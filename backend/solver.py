"""Quadratic tetrahedral, homogeneous isotropic, small-strain static elasticity.

Internal units: mm, N, MPa=N/mm². Surface force is integrated as uniform traction
over the discretized CAD face, so its total is independent of mesh density.
"""
import time
import numpy as np
import scipy, skfem
from scipy.sparse.linalg import spsolve, MatrixRankWarning
import warnings
from skfem import MeshTet, Basis, FacetBasis, ElementVector, ElementTetP2, LinearForm, asm, condense
from skfem.helpers import dot, sym_grad
from skfem.models.elasticity import linear_elasticity, lame_parameters
from .schemas import Analysis, GPUSolution
from .storage import DATA, resource, identifier, read_json, write_json

def assemble_system(setup: Analysis):
    folder = resource('models',setup.model_id)
    model = read_json(folder/'model.json')
    arrays = np.load(folder/'mesh.npz')
    mesh = MeshTet(arrays['points'].T,arrays['tets'].T)
    element = ElementVector(ElementTetP2())
    basis = Basis(mesh,element,intorder=4)
    if basis.N>150000:
        raise ValueError('Model exceeds 150,000 quadratic degrees of freedom. Increase mesh size.')
    face_by_id = {f['id']:f for f in model['faces']}
    if not set(setup.fixed_faces + [l.face_id for l in setup.loads]) <= face_by_id.keys():
        raise ValueError('A selected face does not belong to this model revision. Re-select its faces.')
    facet_lookup = {tuple(sorted(f)):i for i,f in enumerate(mesh.facets.T)}
    face_facets = {fid:np.array([facet_lookup[tuple(sorted(t))] for t in f['triangles']],dtype=int) for fid,f in face_by_id.items()}
    fixed_facets = np.unique(np.concatenate([face_facets[f] for f in setup.fixed_faces]))
    fixed = basis.get_dofs(facets=fixed_facets).all()
    lam,mu = lame_parameters(setup.material.young_mpa,setup.material.poisson)
    K = asm(linear_elasticity(lam,mu),basis)
    F = np.zeros(basis.N)
    applied = np.zeros(3)
    load_details = []
    for load in setup.loads:
        fb = FacetBasis(mesh,element,facets=face_facets[load.face_id],intorder=4)
        area = float(fb.dx.sum())
        traction = np.asarray(load.vector)/area
        @LinearForm
        def surface_force(v,w):
            return dot(traction[:,None,None],v)
        F += asm(surface_force,fb)
        applied += load.vector
        load_details.append({'face_id':load.face_id,'vector_n':list(load.vector),'mesh_area_mm2':area,'traction_mpa':traction.tolist()})
    Kc,Fc,x,free = condense(K,F,D=fixed)
    return dict(model=model,mesh=mesh,basis=basis,K=K,F=F,Kc=Kc,Fc=Fc,x=x,free=free,
                fixed=fixed,lam=lam,mu=mu,applied=applied,load_details=load_details)

def prepare_gpu(setup: Analysis):
    state = assemble_system(setup)
    matrix = state['Kc'].tocsr(); matrix.sort_indices()
    if matrix.shape[0] == 0 or not np.any(state['Fc']):
        raise ValueError('No free loaded degrees of freedom remain. Revise the supports.')
    if np.any(matrix.diagonal() <= 0):
        raise ValueError('The stiffness matrix has a non-positive diagonal.')
    sid = identifier(); folder = DATA/'systems'/sid; folder.mkdir()
    write_json(folder/'setup.json',setup.model_dump())
    return {'id':sid,'n':matrix.shape[0],'row_ptr':matrix.indptr.tolist(),
            'col_idx':matrix.indices.tolist(),'values':matrix.data.tolist(),
            'rhs':state['Fc'].tolist(),'diagonal':matrix.diagonal().tolist()}

def finish_gpu(solution: GPUSolution):
    setup = Analysis.model_validate(read_json(resource('systems',solution.system_id)/'setup.json'))
    return solve_model(setup,solution)

def solve_model(setup: Analysis, gpu_solution: GPUSolution | None = None):
    started = time.monotonic()
    state = assemble_system(setup)
    model,mesh,basis,K,F,Kc,Fc,x,free,fixed,lam,mu,applied,load_details = (state[k] for k in
        ('model','mesh','basis','K','F','Kc','Fc','x','free','fixed','lam','mu','applied','load_details'))
    execution = {'backend':'cpu','device':'Local CPU / SciPy sparse direct', 'precision':'float64',
                 'method':'Sparse direct solve','iterations':0,'refinements':0}
    if gpu_solution is not None:
        if len(gpu_solution.displacement) != len(free):
            raise ValueError('GPU solution length does not match the prepared system.')
        x[free] = gpu_solution.displacement
        execution = {'backend':'webgpu','device':gpu_solution.device,
                     'precision':'GPU float32 with browser float64 iterative refinement',
                     'method':'WebGPU conjugate gradient, symmetric Jacobi scaling',
                     'iterations':gpu_solution.iterations,'refinements':gpu_solution.refinements,
                     'gpu_seconds':gpu_solution.seconds,'device_source':'Browser-reported adapter; numerical residual independently verified on server'}
    else:
        with warnings.catch_warnings():
            warnings.simplefilter('error',MatrixRankWarning)
            try:
                x[free] = spsolve(Kc,Fc)
            except MatrixRankWarning as exc:
                raise ValueError('The model is underconstrained. Apply a fixed support to a complete face.') from exc
    if not np.isfinite(x).all():
        raise ValueError('The solve failed to produce finite displacements. Check supports and geometry.')
    residual = K@x-F
    rel_residual = float(np.linalg.norm(residual[free])/max(np.linalg.norm(F[free]),1e-12))
    if rel_residual > 1e-7:
        raise ValueError('The linear solve did not converge to an acceptable residual.')
    reactions = np.zeros(3)
    for c,ids in enumerate(basis.split_indices()):
        reactions[c] = residual[np.intersect1d(ids,fixed)].sum()
    # P2 nodal and edge DOFs both participate in reaction and moment equilibrium.
    applied_moment = np.zeros(3); reaction_moment = np.zeros(3)
    for c,ids in enumerate(basis.split_indices()):
        forces = np.zeros((len(ids),3)); forces[:,c] = F[ids]
        applied_moment += np.cross(basis.doflocs[:,ids].T,forces).sum(axis=0)
        forces[:] = 0; fi = np.intersect1d(ids,fixed)
        forces2 = np.zeros((len(fi),3)); forces2[:,c] = residual[fi]
        reaction_moment += np.cross(basis.doflocs[:,fi].T,forces2).sum(axis=0)
    strain = sym_grad(basis.interpolate(x))
    sigma = 2*mu*strain
    tr = np.einsum('iieq->eq',strain)
    for i in range(3): sigma[i,i] += lam*tr
    vm_q = np.sqrt(0.5*((sigma[0,0]-sigma[1,1])**2+(sigma[1,1]-sigma[2,2])**2+(sigma[2,2]-sigma[0,0])**2)+3*(sigma[0,1]**2+sigma[1,2]**2+sigma[0,2]**2))
    element_vm = np.sum(vm_q*basis.dx,axis=1)/basis.dx.sum(axis=1)
    # Volume-weighted projection for visualization only. Reported peak is unaveraged quadrature.
    nodal_vm = np.zeros(mesh.nvertices); weights = np.zeros(mesh.nvertices)
    tet_volumes = basis.dx.sum(axis=1)
    for j in range(4):
        np.add.at(nodal_vm,mesh.t[j],element_vm*tet_volumes)
        np.add.at(weights,mesh.t[j],tet_volumes)
    nodal_vm /= weights
    displacement = x[basis.nodal_dofs].T
    all_displacements = np.array([x[ids] for ids in basis.split_indices()]).T
    max_u = float(np.linalg.norm(all_displacements,axis=1).max())
    peak = float(vm_q.max())
    span = float(np.linalg.norm(np.ptp(mesh.p,axis=1)))
    notes = [
        'Single homogeneous isotropic solid; quadratic tetrahedral small-strain, linear-elastic static analysis.',
        'Fixtures are ideal fully fixed faces. Forces are distributed uniformly across the selected mesh faces in global XYZ.',
        'No contact, bolt preload, plasticity, buckling, fatigue, thermal effects or manufacturing anisotropy.',
        'Material presets are illustrative inputs. Verify properties for the actual alloy, condition and manufacturing process.',
        'Peak stress is the maximum unaveraged quadrature-point von Mises stress; display colors are volume-weighted nodal averages.',
        'Sharp corners and fixture edges can have stress singularities. A single mesh does not establish stress convergence.',
        'Yield ratio is a linear-elastic indicator, not a safety certification. Physical acceptance requires independent validation.',
    ]
    if peak > setup.material.yield_mpa:
        notes.append('Predicted stress exceeds the supplied yield strength. The elastic model cannot predict post-yield behavior.')
    if max_u/span > 0.01:
        notes.append('Displacement exceeds 1% of model span. A geometrically nonlinear analysis may be needed.')
    if model['spec']['provenance'] == 'image_proposal':
        notes.append('Geometry originated from an image proposal. User confirmation does not constitute metrology.')
    rid = identifier(); out = DATA/'runs'/rid; out.mkdir()
    result = {'id':rid,'model_id':setup.model_id,'setup':setup.model_dump(),'model_sha256':model['sha256'],'mesh_sha256':model['mesh_sha256'],
              'nodes':int(mesh.nvertices),'elements':int(mesh.nelements),'dofs':int(basis.N),'max_displacement_mm':max_u,
              'peak_von_mises_mpa':peak,'max_display_stress_mpa':float(nodal_vm.max()),
              'yield_ratio':setup.material.yield_mpa/peak if peak>0 else None,
              'reaction_n':reactions.tolist(),'applied_n':applied.tolist(),
              'force_balance_error_n':float(np.linalg.norm(reactions+applied)),
              'moment_balance_error_nmm':float(np.linalg.norm(applied_moment+reaction_moment)),
              'relative_residual':rel_residual,'strain_energy_nmm':float(0.5*x@(K@x)),
              'mass_g':model['volume_mm3']*setup.material.density_kg_m3*1e-6,
              'mesh_volume_mm3':float(tet_volumes.sum()),'displacement':displacement.tolist(),
              'nodal_stress_mpa':nodal_vm.tolist(),'loads':load_details,'warnings':notes+model['spec']['assumptions'],
              'execution':execution,'seconds':round(time.monotonic()-started+(gpu_solution.seconds if gpu_solution else 0),3),'created_at':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),
              'versions':{'scikit-fem':skfem.__version__,'numpy':np.__version__,'scipy':scipy.__version__,'gmsh':model['gmsh_version']}}
    np.savez_compressed(out/'solution.npz',dof_displacement=x,dof_coordinates=basis.doflocs,element_stress_mpa=element_vm,quadrature_stress_mpa=vm_q)
    write_json(out/'result.json',result)
    return result
