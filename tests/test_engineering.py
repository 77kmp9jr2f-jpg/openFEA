"""Independent analytical checks and invalid-input gates, not canned demo results."""
import json, os, zipfile, hashlib
from pathlib import Path
import numpy as np
import pytest
from pydantic import ValidationError
from backend.geometry import build_model
from backend.schemas import Geometry, Analysis, Material, Feature
from backend.solver import solve_model
from backend.storage import resource

@pytest.fixture(scope='module')
def bar():
    return build_model(Geometry(name='Analytic test beam',kind='plate',length=100,width=10,thickness=10,hole_diameter=0,mesh_size=8))

def run_case(model,vector,young=210000,poisson=0):
    return solve_model(Analysis(model_id=model['id'],fixed_faces=[model['recommended']['fixed_face']],
        loads=[{'face_id':model['recommended']['load_face'],'vector':vector}],
        material=Material(name='Analytic isotropic material',young_mpa=young,poisson=poisson,yield_mpa=250,density_kg_m3=7850),confirmed=True))

def test_uniform_tension_matches_exact_solution(bar):
    result=run_case(bar,[1000,0,0])
    # nu=0 suppresses clamped Poisson effects, so u_x=F*x/(E*A) is an exact 3D solution.
    expected=1000*np.array(bar['nodes'])[:,0]/(210000*10*10)
    np.testing.assert_allclose(np.array(result['displacement'])[:,0],expected,rtol=1e-7,atol=1e-10)
    assert result['peak_von_mises_mpa']==pytest.approx(10,rel=1e-7)
    assert result['reaction_n'][0]==pytest.approx(-1000,rel=1e-8)
    assert result['force_balance_error_n']<1e-5
    assert result['moment_balance_error_nmm']<1e-3
    assert result['strain_energy_nmm']==pytest.approx(.5*1000*expected.max(),rel=1e-7)

def test_bending_and_refinement_against_timoshenko(bar):
    force=100;E=210000;nu=.3;L=100;A=100;I=10*10**3/12;G=E/(2*(1+nu));kappa=5/6
    analytic=force*L**3/(3*E*I)+force*L/(kappa*A*G)
    coarse=run_case(bar,[0,0,-force],poisson=nu)
    fine_model=build_model(Geometry(name='Refined analytic beam',kind='plate',length=100,width=10,thickness=10,hole_diameter=0,mesh_size=4))
    fine=run_case(fine_model,[0,0,-force],poisson=nu)
    def tip(r,m):
        ids=np.flatnonzero(np.isclose(np.array(m['nodes'])[:,0],100))
        return float(-np.array(r['displacement'])[ids,2].mean())
    coarse_u,fine_u=tip(coarse,bar),tip(fine,fine_model)
    # 3D clamping effects differ slightly from the 1D model; require <5% for both,
    # and <2% mesh-to-mesh change, fixed in advance of evaluating these cases.
    assert abs(coarse_u/analytic-1)<.05
    assert abs(fine_u/analytic-1)<.05
    assert abs(coarse_u/fine_u-1)<.02
    metrics={'analytical_tip_mm':analytic,'coarse_tip_mm':coarse_u,'fine_tip_mm':fine_u,
             'coarse_error_percent':100*abs(coarse_u/analytic-1),'fine_error_percent':100*abs(fine_u/analytic-1),
             'mesh_change_percent':100*abs(coarse_u/fine_u-1),'coarse_elements':coarse['elements'],'fine_elements':fine['elements']}
    Path('evidence/numerical-benchmark.json').write_text(json.dumps(metrics,indent=2))

def test_load_and_stiffness_scaling(bar):
    base=run_case(bar,[1000,0,0]);double=run_case(bar,[2000,0,0]);soft=run_case(bar,[1000,0,0],young=105000)
    assert double['max_displacement_mm']==pytest.approx(2*base['max_displacement_mm'],rel=1e-8)
    assert double['peak_von_mises_mpa']==pytest.approx(2*base['peak_von_mises_mpa'],rel=1e-8)
    assert soft['max_displacement_mm']==pytest.approx(2*base['max_displacement_mm'],rel=1e-8)
    assert soft['peak_von_mises_mpa']==pytest.approx(base['peak_von_mises_mpa'],rel=1e-8)

def test_step_round_trip_preserves_solid(bar):
    import shutil, uuid
    sid=uuid.uuid4().hex
    shutil.copyfile(resource('models',bar['id'])/'model.step',resource('steps',sid).with_suffix('.step'))
    imported=build_model(Geometry(kind='step',step_id=sid,mesh_size=8,provenance='step_import'))
    assert imported['volume_mm3']==pytest.approx(bar['volume_mm3'],rel=1e-8)
    np.testing.assert_allclose(imported['bounds'],bar['bounds'],atol=1e-6)
    assert len(imported['faces'])==6

def test_custom_csg_and_disconnected_rejection():
    spec=Geometry(kind='custom',features=[Feature(size=(20,20,10)),Feature(operation='cut',primitive='cylinder',origin=(10,10,-1),axis=(0,0,12),radius=3)],mesh_size=4)
    model=build_model(spec)
    assert model['volume_mm3']==pytest.approx(4000-np.pi*3**2*10,rel=1e-8)
    with pytest.raises(ValueError,match='one connected solid'):
        build_model(Geometry(kind='custom',features=[Feature(),Feature(origin=(30,0,0))]))

@pytest.mark.parametrize('patch',[{'confirmed':False},{'fixed_faces':[]},{'loads':[]},{'loads':[{'face_id':1,'vector':[0,0,0]}]},{'material':{'young_mpa':-1}},{'material':{'poisson':.5}},{'loads':[{'face_id':1,'vector':[1,0,0]}]}])
def test_invalid_analysis_gates(patch):
    args={'model_id':'a'*32,'fixed_faces':[1],'loads':[{'face_id':2,'vector':[0,0,-100]}],'confirmed':True}
    args.update(patch)
    with pytest.raises(ValidationError):Analysis(**args)

def test_unknown_face_rejected(bar):
    with pytest.raises(ValueError,match='does not belong'):
        solve_model(Analysis(model_id=bar['id'],fixed_faces=[999],loads=[{'face_id':1,'vector':[1,0,0]}],confirmed=True))

@pytest.mark.parametrize('patch',[{'length':float('nan')},{'thickness':50},{'mesh_size':0},{'hole_diameter':100},{'kind':'step'},{'kind':'custom'}])
def test_invalid_geometry(patch):
    with pytest.raises(ValidationError):Geometry(**patch)

def test_report_archive_is_complete_and_hashes_match(bar):
    from backend.report import export_report
    result=run_case(bar,[1000,0,0])
    archive=export_report(result['id'],'zip')
    with zipfile.ZipFile(archive) as z:
        assert {'report.pdf','report.html','result.json','model/model.step','model/mesh.msh','solution.npz','nodes.csv','manifest.json','reproduce.py'}<=set(z.namelist())
        for name,digest in json.loads(z.read('manifest.json')).items():assert hashlib.sha256(z.read(name)).hexdigest()==digest
        assert z.read('report.pdf').startswith(b'%PDF')
        assert 'quadratic DOFs' in z.read('report.html').decode()

def test_gpu_submission_is_independently_verified(bar):
    from backend.solver import prepare_gpu, finish_gpu
    from backend.schemas import GPUSolution
    from scipy.sparse import csr_matrix
    from scipy.sparse.linalg import spsolve
    setup=Analysis(model_id=bar['id'],fixed_faces=[bar['recommended']['fixed_face']],
        loads=[{'face_id':bar['recommended']['load_face'],'vector':[1000,0,0]}],
        material=Material(young_mpa=210000,poisson=0),confirmed=True)
    prepared=prepare_gpu(setup)
    matrix=csr_matrix((prepared['values'],prepared['col_idx'],prepared['row_ptr']),shape=(prepared['n'],prepared['n']))
    values=spsolve(matrix,prepared['rhs'])
    args=dict(system_id=prepared['id'],device='Test submission; not GPU execution evidence',iterations=1,refinements=1,seconds=0)
    result=finish_gpu(GPUSolution(displacement=values.tolist(),**args))
    assert result['peak_von_mises_mpa']==pytest.approx(10,rel=1e-7)
    assert result['relative_residual']<1e-7
    with pytest.raises(ValueError,match='did not converge'):
        finish_gpu(GPUSolution(displacement=(values*1.01).tolist(),**args))
    with pytest.raises(ValueError,match='length'):
        finish_gpu(GPUSolution(displacement=[0],**args))
