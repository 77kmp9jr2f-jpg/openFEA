"""An AI suggestion becomes a setup only after revision and input checks."""
import copy
import pytest
from backend.geometry import build_model
from backend.schemas import Geometry

@pytest.fixture(scope='module')
def model():
    return build_model(Geometry(name='Interview test solid',kind='plate',length=40,width=20,thickness=10,hole_diameter=0,mesh_size=8))

@pytest.fixture
def context(model):
    return {'model_id':model['id'],'geometry':model['spec'],
        'material':{'name':'Illustrative aluminum','young_mpa':69000,'poisson':.33,'yield_mpa':240,'density_kg_m3':2700},
        'fixed_faces':[],'loads':[],'notes':'Bench example','reference_id':None,'annotations':[]}

@pytest.fixture
def draft(model,context):
    return {'material':context['material'],'fixed_faces':[model['recommended']['fixed_face']],
        'loads':[{'face_id':model['recommended']['load_face'],'vector':[0,0,-100]}],
        'notes':'Rear fixed; total downward force on end face.',
        'assumptions':['Static illustrative material; no bolts or contact.']}

def test_proposal_applies_complete_setup_but_never_confirms_or_solves(context,draft):
    from backend.simulation_proposals import propose_setup, apply_setup
    proposal=propose_setup(draft,context)
    applied=apply_setup(proposal['id'],context)
    assert applied['model_id']==context['model_id']
    assert applied['loads']==draft['loads']
    assert applied['fixed_faces']==draft['fixed_faces']
    assert applied['material']==draft['material']
    assert applied['confirmed'] is False
    assert applied['setup_proposal_id']==proposal['id']
    assert 'no bolts or contact' in applied['notes']
    assert 'result' not in applied

@pytest.mark.parametrize('field,value',[
    ('notes','Changed force intent'),('fixed_faces',[999]),
    ('material',{'name':'Steel','young_mpa':200000,'poisson':.3,'yield_mpa':250,'density_kg_m3':7850}),
    ('reference_id','a'*32),
])
def test_changed_interview_inputs_require_a_fresh_proposal(context,draft,field,value):
    from backend.simulation_proposals import propose_setup, apply_setup
    p=propose_setup(draft,context)
    changed=copy.deepcopy(context);changed[field]=value
    with pytest.raises(ValueError,match='changed'):
        apply_setup(p['id'],changed)

def test_rebuilt_model_cannot_reuse_a_proposal(context,draft):
    from backend.simulation_proposals import propose_setup, apply_setup
    p=propose_setup(draft,context)
    changed=copy.deepcopy(context);changed['model_id']='a'*32
    with pytest.raises(ValueError,match='model revision'):
        apply_setup(p['id'],changed)

def test_unmeshed_geometry_cannot_receive_a_proposal(context,draft):
    from backend.simulation_proposals import propose_setup
    changed=copy.deepcopy(context);changed['geometry']['length']+=5
    with pytest.raises(ValueError,match='Rebuild'):
        propose_setup(draft,changed)

@pytest.mark.parametrize('patch',[
    {'fixed_faces':[999]}, {'loads':[{'face_id':999,'vector':[0,0,-100]}]},
    {'loads':[{'face_id':2,'vector':[0,0,0]}]}, {'fixed_faces':[]},
])
def test_unresolvable_or_incomplete_conditions_are_rejected(context,draft,patch):
    from backend.simulation_proposals import propose_setup
    changed=copy.deepcopy(draft);changed.update(patch)
    with pytest.raises(ValueError):propose_setup(changed,context)

def test_a_face_cannot_be_both_fixed_and_loaded(context,draft):
    from backend.simulation_proposals import propose_setup
    changed=copy.deepcopy(draft);changed['loads'][0]['face_id']=draft['fixed_faces'][0]
    with pytest.raises(ValueError,match='both'):
        propose_setup(changed,context)

@pytest.mark.parametrize('missing',['material_property','force_vector'])
def test_proposal_never_supplies_defaults_for_missing_inputs(context,draft,missing):
    from backend.simulation_proposals import propose_setup
    changed=copy.deepcopy(draft)
    if missing=='material_property':del changed['material']['young_mpa']
    else:del changed['loads'][0]['vector']
    with pytest.raises(ValueError,match='explicit'):propose_setup(changed,context)

def request_for(context):
    from backend.schemas import AssistantRequest
    return AssistantRequest(message='Set up this static test',stage='loading',model_id=context['model_id'],
        geometry=context['geometry'],material=context['material'],fixed_faces=context['fixed_faces'],
        loads=context['loads'],application_notes=context['notes'],image_id=context['reference_id'],annotations=context['annotations'])

def test_missing_inputs_remain_questions_without_a_setup(context):
    from backend.assistant import normalize_answer
    answer=normalize_answer({'message':'What is the load magnitude?', 'questions':['Which direction?'],
        'proposal':None,'simulation_proposal':None},request_for(context))
    assert answer['simulation_proposal'] is None
    assert answer['live'] is True
    assert answer['questions']==['Which direction?']

def test_print_proposal_is_complete_revision_bound_and_verified(context, draft):
    from backend.schemas import PrintSettings, Analysis
    from backend.simulation_proposals import propose_setup, apply_setup, verify_applied_setup
    context['print'] = PrintSettings(enabled=True, rotation_deg=(30, 45, 20)).model_dump(mode='json')
    with pytest.raises(ValueError, match='print'):
        propose_setup(draft, context)
    draft['print'] = {**context['print'], 'infill_density': .35}
    proposal = propose_setup(draft, context)
    changed = copy.deepcopy(context); changed['print']['wall_count'] += 1
    with pytest.raises(ValueError, match='changed'):
        apply_setup(proposal['id'], changed)
    applied = apply_setup(proposal['id'], context)
    assert applied['print'] == draft['print']
    setup = Analysis.model_validate({**applied, 'confirmed': True})
    verify_applied_setup(setup)
    setup.print.infill_density = .9
    with pytest.raises(ValueError, match='differs'):
        verify_applied_setup(setup)

def test_print_proposal_cannot_default_missing_manufacturing_inputs(context, draft):
    from backend.schemas import PrintSettings
    from backend.simulation_proposals import propose_setup
    context['print'] = PrintSettings(enabled=True).model_dump(mode='json')
    draft['print'] = {'enabled': True}
    with pytest.raises(ValueError, match='explicit'):
        propose_setup(draft, context)

def test_live_answer_becomes_revision_bound_complete_proposal(context,draft):
    from backend.assistant import normalize_answer
    answer=normalize_answer({'message':'Review these conditions.', 'questions':[],
        'proposal':None,'simulation_proposal':draft},request_for(context))
    assert answer['simulation_proposal']['source_context']['model_id']==context['model_id']
    assert answer['simulation_proposal']['loads']==draft['loads']
    assert len(answer['simulation_proposal']['source_hash'])==64

def test_geometry_and_face_assignments_cannot_share_a_response(context,draft):
    from backend.assistant import normalize_answer
    with pytest.raises(ValueError,match='separate steps'):
        normalize_answer({'message':'Both','questions':[],'proposal':context['geometry'],'simulation_proposal':draft},request_for(context))

def test_apply_endpoint_and_provenance_reject_tampering(context,draft):
    from fastapi.testclient import TestClient
    from backend.app import app
    from backend.schemas import Analysis
    from backend.simulation_proposals import propose_setup,verify_applied_setup
    proposal=propose_setup(draft,context)
    client=TestClient(app)
    response=client.post(f"/api/setup-proposals/{proposal['id']}/apply",json=context)
    assert response.status_code==200
    applied=response.json()
    setup=Analysis.model_validate({**applied,'confirmed':True})
    verify_applied_setup(setup)
    for field,value in [('notes','tampered'),('reference_id','a'*32)]:
        changed=setup.model_copy(update={field:value})
        with pytest.raises(ValueError,match='differs'):verify_applied_setup(changed)
    changed=copy.deepcopy(context);changed['notes']='Different intent'
    assert client.post(f"/api/setup-proposals/{proposal['id']}/apply",json=changed).status_code==400

@pytest.mark.parametrize('order', [1, 2])
def test_archive_preserves_interview_proposal_and_reproduces(context,draft,tmp_path,order):
    import json,subprocess,sys,zipfile,os
    from backend.simulation_proposals import propose_setup,apply_setup
    from backend.schemas import Analysis
    from backend.solver import solve_model
    from backend.report import export_report
    proposal=propose_setup(draft,context)
    transcript=[{'role':'user','text':'Use 100 N downward.','live':False},
        {'role':'assistant','text':'Review rear restraint and end force.','live':True}]
    setup=Analysis.model_validate({**apply_setup(proposal['id'],context),'confirmed':True,'conversation':transcript})
    result=solve_model(setup, reproduction_element_order=order)
    with zipfile.ZipFile(export_report(result['id'],'zip')) as archive:
        assert json.loads(archive.read('interview.json'))==transcript
        assert json.loads(archive.read('setup-proposal.json'))['id']==proposal['id']
        archive.extractall(tmp_path)
    env={**os.environ};env.pop('FEAR_DATA_DIR',None)
    reproduced=subprocess.run([sys.executable,str(tmp_path/'reproduce.py')],capture_output=True,text=True,env=env,timeout=60)
    assert reproduced.returncode==0,reproduced.stderr
    original=result['max_displacement_mm']
    actual=json.loads(next((tmp_path/'reproduced'/'runs').glob('*/result.json')).read_text())
    assert actual['max_displacement_mm']==pytest.approx(original,rel=1e-10)
    assert actual['element_order'] == order
    assert actual['setup']['setup_proposal_id']==proposal['id']

def test_live_print_answer_cannot_default_entire_print_setup(context, draft):
    from backend.schemas import PrintSettings
    from backend.assistant import normalize_answer
    request = request_for(context).model_copy(update={'print': PrintSettings(enabled=True)})
    with pytest.raises(ValueError, match='explicit print'):
        normalize_answer({'message': 'Review', 'questions': [], 'proposal': None, 'simulation_proposal': draft}, request)
