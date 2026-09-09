"""OpenCASCADE single-solid construction and conforming tetrahedral meshes (mm)."""
from pathlib import Path
from threading import Lock
import hashlib, time
import gmsh
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from .schemas import Geometry
from .storage import DATA, identifier, write_json, resource

GMSH_LOCK = Lock()

def _make_solid(spec: Geometry):
    occ = gmsh.model.occ
    l,w,h,t,d = spec.length,spec.width,spec.height,spec.thickness,spec.hole_diameter
    if spec.kind == 'step':
        occ.importShapes(str(resource('steps',spec.step_id).with_suffix('.step')))
        occ.synchronize()
        return
    if spec.kind == 'custom':
        solid = []
        for f in spec.features:
            tag = occ.addBox(*f.origin,*f.size) if f.primitive == 'box' else occ.addCylinder(*f.origin,*f.axis,f.radius)
            if not solid:
                solid = [(3,tag)]
            elif f.operation == 'add':
                solid,_ = occ.fuse(solid,[(3,tag)])
            else:
                solid,_ = occ.cut(solid,[(3,tag)])
                if not solid:
                    raise ValueError('A subtractive feature removed the entire solid.')
    elif spec.kind == 'shaft':
        solid = [(3,occ.addCylinder(0,0,0,l,0,0,w/2))]
        if d:
            solid,_ = occ.cut(solid,[(3,occ.addCylinder(-1,0,0,l+2,0,0,d/2))])
    else:
        solid = [(3,occ.addBox(0,0,0,l,w,t))]
        if spec.kind == 'bracket':
            solid,_ = occ.fuse(solid,[(3,occ.addBox(0,0,0,t,w,h))])
        if d:
            cuts = [(3,occ.addCylinder(l*0.72,w*0.5,-1,0,0,t+2,d/2))]
            if spec.kind == 'bracket':
                cuts += [(3,occ.addCylinder(-1,w*0.5,h*0.72,t+2,0,0,d/2))]
            solid,_ = occ.cut(solid,cuts)
    occ.removeAllDuplicates()
    occ.synchronize()

def build_model(spec: Geometry, destination: Path | None = None):
    started = time.monotonic()
    mid = identifier()
    out = destination or DATA/'models'/mid
    out.mkdir(parents=True,exist_ok=True)
    with GMSH_LOCK:
        gmsh.initialize(interruptible=False)
        try:
            gmsh.option.setNumber('General.Terminal',0)
            gmsh.option.setNumber('General.NumThreads',2)
            gmsh.option.setString('Geometry.OCCTargetUnit','MM')
            gmsh.model.add('FEA-R')
            _make_solid(spec)
            volumes = gmsh.model.getEntities(3)
            if len(volumes) != 1:
                raise ValueError('This version requires one connected solid. Fuse bodies or import a single-solid STEP; contact is not modelled.')
            volume = gmsh.model.occ.getMass(*volumes[0])
            bounds = gmsh.model.getBoundingBox(*volumes[0])
            extents = np.array(bounds[3:])-bounds[:3]
            if min(extents) < 0.05 or max(extents) > 2000 or volume <= 0:
                raise ValueError('The model must be a nonzero solid spanning 0.05 to 2,000 mm on each axis. Check STEP units.')
            if volume/spec.mesh_size**3 > 15000:
                raise ValueError('Requested mesh is too dense for the local prototype. Increase the mesh size.')
            gmsh.option.setNumber('Mesh.MeshSizeMin',spec.mesh_size*0.35)
            gmsh.option.setNumber('Mesh.MeshSizeMax',spec.mesh_size)
            gmsh.option.setNumber('Mesh.MeshSizeFromCurvature',12)
            gmsh.option.setNumber('Mesh.ElementOrder',1)
            gmsh.option.setNumber('Mesh.Algorithm3D',1)
            gmsh.model.mesh.generate(3)
            gmsh.model.mesh.optimize('Netgen')
            tags,coords,_ = gmsh.model.mesh.getNodes()
            all_points = np.asarray(coords).reshape(-1,3)
            _,raw_tets = gmsh.model.mesh.getElementsByType(4)
            raw_tets = np.asarray(raw_tets).reshape(-1,4)
            if not len(raw_tets) or len(raw_tets)>35000:
                raise ValueError('Mesh must contain 1–35,000 tetrahedra. Increase mesh size if too dense.')
            used = np.unique(raw_tets)
            index = {int(tag):i for i,tag in enumerate(used)}
            raw_index = {int(tag):i for i,tag in enumerate(tags)}
            points = all_points[[raw_index[int(tag)] for tag in used]]
            tets = np.array([[index[int(n)] for n in tet] for tet in raw_tets],dtype=np.int32)
            rows = np.repeat(tets[:,0],3); cols = tets[:,1:].ravel()
            graph = coo_matrix((np.ones(len(rows)),(rows,cols)),shape=(len(points),len(points)))
            if connected_components(graph,directed=False,return_labels=False) != 1:
                raise ValueError('The mesh contains disconnected bodies; contact is not supported.')
            faces = []
            for _,tag in gmsh.model.getEntities(2):
                _,tri_nodes = gmsh.model.mesh.getElementsByType(2,tag)
                tris = [[index[int(n)] for n in row] for row in np.asarray(tri_nodes).reshape(-1,3)]
                if not tris: continue
                center = list(gmsh.model.occ.getCenterOfMass(2,tag))
                bb = gmsh.model.getBoundingBox(2,tag)
                spans = np.array(bb[3:])-bb[:3]
                axis = int(np.argmin(spans))
                planar = spans[axis] < 1e-4
                kind = gmsh.model.getType(2,tag)
                label = f'{"XYZ"[axis]} = {center[axis]:.1f} mm' if planar else f'{kind} surface'
                faces.append({'id':tag,'label':label,'kind':kind,'center':center,'area_mm2':gmsh.model.occ.getMass(2,tag),'triangles':tris})
            qualities = gmsh.model.mesh.getElementQualities(gmsh.model.mesh.getElementsByType(4)[0],'minSICN')
            if min(qualities)<=0:
                raise ValueError('Mesher produced an inverted element. Adjust the geometry or mesh size.')
            gmsh.write(str(out/'model.step'))
            gmsh.write(str(out/'model.stl'))
            gmsh.write(str(out/'mesh.msh'))
            np.savez_compressed(out/'mesh.npz',points=points,tets=tets)
            lo,hi = points.min(axis=0),points.max(axis=0)
            left = min(faces,key=lambda f:f['center'][0])
            right = max(faces,key=lambda f:f['center'][0])
            result = {'id':mid,'spec':spec.model_dump(),'nodes':points.tolist(),'tetrahedra':len(tets),'faces':faces,
                      'volume_mm3':volume,'bounds':[lo.tolist(),hi.tolist()],'min_quality':float(min(qualities)),
                      'recommended':{'fixed_face':left['id'],'load_face':right['id']},
                      'sha256':hashlib.sha256((out/'model.step').read_bytes()).hexdigest(),
                      'mesh_sha256':hashlib.sha256((out/'mesh.msh').read_bytes()).hexdigest(),
                      'seconds':round(time.monotonic()-started,3),'gmsh_version':gmsh.__version__}
            write_json(out/'model.json',result)
            return result
        finally:
            gmsh.finalize()
