"""OpenCASCADE single-solid construction and conforming tetrahedral meshes (mm)."""
from pathlib import Path
from threading import Lock
import fcntl, hashlib, math, time
import gmsh
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from .schemas import Geometry
from .storage import DATA, identifier, write_json, read_json, resource

GMSH_LOCK = Lock()

def _process_lock():
    path = DATA / '.gmsh.lock'
    handle = path.open('w')
    fcntl.flock(handle, fcntl.LOCK_EX)
    return handle

def _make_solid(spec: Geometry):
    occ = gmsh.model.occ
    l,w,h,t,d = spec.length,spec.width,spec.height,spec.thickness,spec.hole_diameter
    if spec.kind == 'stl':
        _make_stl_solid(spec)
        return
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

def _make_stl_solid(spec: Geometry):
    from .stl_io import scaled_stl_path
    path = scaled_stl_path(spec.stl_id, spec.unit_scale, spec.accept_stl_preprocessing)
    angle = spec.feature_angle_deg * math.pi / 180
    gmsh.option.setNumber('Mesh.AngleToleranceFacetOverlap', 0.2)
    inspect = read_json(resource('stls', spec.stl_id) / 'inspect.json')
    reduced = inspect.get('preprocessing', {}).get('surface_samples', {})
    retain_facets = inspect.get('triangles', 0) > 50000 or reduced.get('reduction_mode') == 'target-count'
    def classify_source(for_parametrization):
        gmsh.merge(str(path))
        gmsh.model.mesh.classifySurfaces(angle, True, for_parametrization, math.pi)
    classify_source(not retain_facets)
    if retain_facets:
        # The extra cuts for parametrization can stall on reduced skinny facets.
        # Retain their independently checked boundary and mesh the volume inside.
        gmsh.model.mesh.createTopology()
    else:
        try:
            gmsh.model.mesh.createGeometry()
        except Exception:
            # createGeometry can leave some surfaces parametrized and others
            # untouched. Reusing that state can silently produce no volume
            # elements. Reload the immutable surface before topology fallback.
            gmsh.clear()
            gmsh.model.add('OpenFEA')
            classify_source(False)
            gmsh.model.mesh.createTopology()
    surfaces = gmsh.model.getEntities(2)
    if len(surfaces) < 1:
        raise ValueError('No surfaces could be classified from the STL. Repair the mesh or change the feature angle.')
    loop = gmsh.model.geo.addSurfaceLoop([tag for _dim, tag in surfaces])
    gmsh.model.geo.addVolume([loop])
    gmsh.model.geo.synchronize()

def _face_record(tag, index, points):
    _, tri_nodes = gmsh.model.mesh.getElementsByType(2, tag)
    tris = []
    for row in np.asarray(tri_nodes).reshape(-1, 3):
        try:
            tris.append([index[int(n)] for n in row])
        except KeyError:
            continue
    if not tris:
        return None
    try:
        center = list(gmsh.model.occ.getCenterOfMass(2, tag))
        area = float(gmsh.model.occ.getMass(2, tag))
        bb = gmsh.model.getBoundingBox(2, tag)
        kind = gmsh.model.getType(2, tag)
    except Exception:
        coords = np.array([points[i] for tri in tris for i in tri]).reshape(-1, 3)
        areas = []
        cents = []
        for tri in tris:
            a, b, c = points[tri]
            cross = np.cross(b - a, c - a)
            areas.append(0.5 * np.linalg.norm(cross))
            cents.append((a + b + c) / 3)
        area = float(sum(areas))
        center = (np.average(cents, axis=0, weights=np.maximum(areas, 1e-18)) if area else coords.mean(axis=0)).tolist()
        bb = (*coords.min(axis=0), *coords.max(axis=0))
        kind = 'STL patch'
    spans = np.array(bb[3:]) - bb[:3]
    axis = int(np.argmin(spans))
    planar = spans[axis] < 1e-4
    label = f'{"XYZ"[axis]} = {center[axis]:.1f} mm' if planar else f'{kind} surface'
    return {'id': tag, 'label': label, 'kind': kind, 'center': center, 'area_mm2': area, 'triangles': tris}

def build_model(spec: Geometry, destination: Path | None = None):
    started = time.monotonic()
    mid = identifier()
    out = destination or DATA/'models'/mid
    out.mkdir(parents=True,exist_ok=True)
    lock = _process_lock()
    try:
      with GMSH_LOCK:
        gmsh.initialize(interruptible=False)
        try:
            gmsh.option.setNumber('General.Terminal',0)
            gmsh.option.setNumber('General.NumThreads',2)
            gmsh.option.setString('Geometry.OCCTargetUnit','MM')
            gmsh.model.add('OpenFEA')
            _make_solid(spec)
            volumes = gmsh.model.getEntities(3)
            if len(volumes) != 1:
                raise ValueError('This version requires one connected solid. Fuse bodies or import a single-solid STEP; contact is not modelled.')
            try:
                volume = gmsh.model.occ.getMass(*volumes[0])
            except Exception:
                if spec.kind != 'stl':
                    raise
                from .stl_io import load_inspection
                volume = abs(load_inspection(spec.stl_id, spec.unit_scale)['signed_volume_mm3'])
            bounds = gmsh.model.getBoundingBox(*volumes[0])
            extents = np.array(bounds[3:])-bounds[:3]
            if min(extents) < 0.05 or max(extents) > 2000 or volume <= 0:
                raise ValueError('The model must be a nonzero solid spanning 0.05 to 2,000 mm on each axis. Check STEP units.')
            if volume/spec.mesh_size**3 > 15000:
                raise ValueError('Requested mesh is too dense for the local prototype. Increase the mesh size.')
            gmsh.option.setNumber('Mesh.MeshSizeMin',spec.mesh_size*0.35)
            gmsh.option.setNumber('Mesh.MeshSizeMax',spec.mesh_size)
            dense_stl = False
            if spec.kind == 'stl' and spec.stl_id:
                from .storage import read_json
                inspect = read_json(resource('stls', spec.stl_id) / 'inspect.json')
                dense_stl = inspect.get('triangles', 0) > 50000
            gmsh.option.setNumber('Mesh.MeshSizeFromCurvature', 0 if dense_stl else 12)
            gmsh.option.setNumber('Mesh.ElementOrder',1)
            gmsh.option.setNumber('Mesh.Algorithm3D',1)
            gmsh.model.mesh.generate(3)
            gmsh.model.mesh.optimize('Netgen')
            tags,coords,_ = gmsh.model.mesh.getNodes()
            all_points = np.asarray(coords).reshape(-1,3)
            _,raw_tets = gmsh.model.mesh.getElementsByType(4)
            raw_tets = np.asarray(raw_tets).reshape(-1,4)
            if not len(raw_tets):
                raise ValueError('No tetrahedra were produced from the surface. Repair the geometry or change the STL feature angle.')
            if len(raw_tets)>200000:
                raise ValueError('Mesh exceeds 200,000 tetrahedra. Increase mesh size.')
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
                record = _face_record(tag, index, points)
                if record:
                    faces.append(record)
            if not faces:
                raise ValueError('No selectable surfaces were produced. Repair the STL or change the feature angle.')
            qualities = gmsh.model.mesh.getElementQualities(gmsh.model.mesh.getElementsByType(4)[0],'minSICN')
            if min(qualities)<=0:
                raise ValueError('Mesher produced an inverted element. Adjust the geometry or mesh size.')
            if spec.kind != 'stl':
                gmsh.write(str(out/'model.step'))
            gmsh.write(str(out/'model.stl'))
            gmsh.write(str(out/'mesh.msh'))
            provenance = {}
            if spec.kind == 'stl':
                from .stl_io import load_inspection, scaled_stl_path
                import shutil
                source = resource('stls', spec.stl_id)
                shutil.copyfile(source/'source.stl', out/'source.stl')
                shutil.copyfile(scaled_stl_path(spec.stl_id, spec.unit_scale, spec.accept_stl_preprocessing), out/'working.stl')
                provenance = {'source_sha256': hashlib.sha256((out/'source.stl').read_bytes()).hexdigest(),
                    'working_sha256': hashlib.sha256((out/'working.stl').read_bytes()).hexdigest(),
                    'unit_scale': spec.unit_scale, 'feature_angle_deg': spec.feature_angle_deg,
                    'preprocessing_accepted': spec.accept_stl_preprocessing,
                    'inspection': load_inspection(spec.stl_id, spec.unit_scale)}
                write_json(out/'stl-provenance.json', provenance)
            np.savez_compressed(out/'mesh.npz',points=points,tets=tets)
            lo,hi = points.min(axis=0),points.max(axis=0)
            left = min(faces,key=lambda f:f['center'][0])
            right = max(faces,key=lambda f:f['center'][0])
            result = {'id':mid,'spec':spec.model_dump(),'nodes':points.tolist(),'tetrahedra':len(tets),'faces':faces,
                      'volume_mm3':volume,'bounds':[lo.tolist(),hi.tolist()],'min_quality':float(min(qualities)),
                      'recommended':{'fixed_face':left['id'],'load_face':right['id']},
                      'sha256':hashlib.sha256((out/('stl-provenance.json' if spec.kind == 'stl' else 'model.step')).read_bytes()).hexdigest(),
                      'available_formats':['stl','msh'] + ([] if spec.kind == 'stl' else ['step']),
                      **provenance,
                      'mesh_sha256':hashlib.sha256((out/'mesh.msh').read_bytes()).hexdigest(),
                      'seconds':round(time.monotonic()-started,3),'gmsh_version':gmsh.__version__}
            write_json(out/'model.json',result)
            return result
        finally:
            gmsh.finalize()
    finally:
        lock.close()
