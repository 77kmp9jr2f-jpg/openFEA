import base64, io
from fastapi.testclient import TestClient
from PIL import Image
from backend.app import app

client=TestClient(app)

def test_health_and_local_boundary():
    assert client.get('/api/health').json()['ok']
    assert client.post('/api/models',json={},headers={'Origin':'https://foreign.example'}).status_code==403
    assert client.get('/api/health',headers={'Host':'foreign.example'}).status_code==403

def test_image_roundtrip_and_validation():
    buf=io.BytesIO();Image.new('RGB',(80,50),'white').save(buf,format='PNG')
    response=client.post('/api/images',json={'name':'test.png','data_url':'data:image/png;base64,'+base64.b64encode(buf.getvalue()).decode()})
    assert response.status_code==200
    meta=response.json();assert meta['width']==80
    assert client.get(meta['url']).content.startswith(b'\x89PNG')
    assert client.post('/api/images',json={'data_url':'data:text/html;base64,AAAA'}).status_code==400

def test_study_persistence():
    state={'notes':'A note','annotations':[{'text':'12 mm'}]}
    saved=client.post('/api/studies',json={'name':'API persistence test','state':state}).json()
    restored=client.get('/api/studies/'+saved['id']).json()
    assert restored['state']==state

def test_setup_requires_review_and_step_rejects_bad_input():
    assert client.post('/api/solve',json={'model_id':'a'*32,'fixed_faces':[1],'loads':[{'face_id':2,'vector':[0,0,-1]}],'confirmed':False}).status_code==422
    assert client.post('/api/steps',content=b'<html>fake</html>').status_code==400
    assert client.post('/api/stls',content=b'<html>fake</html>').status_code==400
    from backend.stl_io import write_box_stl
    from pathlib import Path
    coupon=Path('/tmp/openfea-api-coupon.stl'); write_box_stl(coupon)
    uploaded=client.post('/api/stls',content=coupon.read_bytes(),headers={'X-Filename':'coupon.stl'})
    assert uploaded.status_code==200 and uploaded.json()['watertight'] is True

def _wait_job(jid, timeout=90):
    import time
    for _ in range(timeout * 2):
        status = client.get('/api/jobs/' + jid).json()
        if status['status'] == 'complete':
            return status['result']
        if status['status'] in ('failed', 'cancelled'):
            raise AssertionError(status)
        time.sleep(0.5)
    raise AssertionError('job timed out: ' + jid)


def test_agent_contract_and_readiness_do_not_bypass_confirm():
    contract = client.get('/api/agent').json()
    assert contract['gates']['confirm_required'] is True
    assert contract['gates']['max_relative_residual'] == 1e-7
    assert contract['gates']['no_generated_code'] is True
    assert client.get('/api/health').json()['agent'] == '/api/agent'
    assert client.post('/api/solve', json={
        'model_id': 'a' * 32, 'fixed_faces': [1],
        'loads': [{'face_id': 2, 'vector': [0, 0, -1]}], 'confirmed': False,
    }).status_code == 422
    missing = client.get('/api/models/' + 'f' * 32 + '/readiness')
    assert missing.status_code == 404


def test_agent_can_import_check_confirm_and_solve_on_cpu():
    from backend.stl_io import write_box_stl
    from pathlib import Path
    coupon = Path('/tmp/openfea-agent-coupon.stl')
    write_box_stl(coupon, (40, 10, 8))
    uploaded = client.post('/api/stls', content=coupon.read_bytes(),
                           headers={'X-Filename': 'agent-coupon.stl'}).json()
    assert uploaded['watertight'] is True
    job = client.post('/api/models', json={
        'name': 'agent-coupon', 'kind': 'stl', 'stl_id': uploaded['id'],
        'mesh_size': 7, 'hole_diameter': 0, 'provenance': 'stl_import',
    }).json()
    model = _wait_job(job['id'])
    empty = client.get('/api/models/' + model['id'] + '/readiness').json()
    assert empty['status'] == 'incomplete'
    assert 'confirm' in empty['missing']
    draft = {
        'model_id': model['id'],
        'material': {
            'name': 'PLA · illustrative filament', 'young_mpa': 3500,
            'poisson': 0.35, 'yield_mpa': 40, 'density_kg_m3': 1240,
        },
        'fixed_faces': empty['recommended']['fixed_faces'],
        'loads': empty['recommended']['loads'],
        'confirmed': False,
    }
    pending = client.post('/api/readiness', json=draft).json()
    assert pending['missing'] == ['confirm']
    assert pending['ready'] is False
    solved = client.post('/api/solve', json={**draft, 'confirmed': True}).json()
    result = _wait_job(solved['id'])
    assert result['relative_residual'] < 1e-7
    assert result['guidance']['trust']
    assert result['model_sha256'] == model['sha256']
    assert result['mesh_sha256'] == model['mesh_sha256']
    html = client.get('/api/runs/' + result['id'] + '/report/html')
    assert html.status_code == 200
    assert b'What to trust' in html.content


def test_agent_can_import_step_check_and_solve():
    from backend.geometry import build_model
    from backend.schemas import Geometry
    from backend.storage import resource
    source = build_model(Geometry(
        name='agent-plate', kind='plate', length=40, width=20, thickness=8,
        hole_diameter=0, mesh_size=8, provenance='user_dimensions'))
    uploaded = client.post('/api/steps', content=(resource('models', source['id']) / 'model.step').read_bytes()).json()
    job = client.post('/api/models', json={
        'name': 'agent-step', 'kind': 'step', 'step_id': uploaded['id'],
        'mesh_size': 8, 'hole_diameter': 0, 'provenance': 'step_import',
    }).json()
    model = _wait_job(job['id'])
    empty = client.get('/api/models/' + model['id'] + '/readiness').json()
    assert empty['recommended']['fixed_faces']
    draft = {
        'model_id': model['id'],
        'material': {
            'name': 'Aluminum · illustrative', 'young_mpa': 69000,
            'poisson': 0.33, 'yield_mpa': 240, 'density_kg_m3': 2700,
        },
        'fixed_faces': empty['recommended']['fixed_faces'],
        'loads': empty['recommended']['loads'],
        'confirmed': True,
    }
    assert client.post('/api/readiness', json=draft).json()['ready'] is True
    result = _wait_job(client.post('/api/solve', json=draft).json()['id'])
    assert result['relative_residual'] < 1e-7
    assert result['guidance']['trust']
    assert result['model_sha256'] == model['sha256']


def test_unknown_job_cancel_is_not_found():
    assert client.post('/api/jobs/'+'a'*32+'/cancel').status_code==404

def test_running_job_can_be_cancelled():
    from backend.jobs import start_job
    from backend.schemas import Geometry
    from backend.storage import read_json, resource
    started=start_job('model',Geometry(kind='plate',length=80,width=20,thickness=12,hole_diameter=0,mesh_size=3).model_dump())
    cancelled=client.post('/api/jobs/'+started['id']+'/cancel')
    status=read_json(resource('jobs',started['id'])/'status.json')
    assert cancelled.status_code==200
    assert cancelled.json()['status'] in ('cancelled','complete')
    assert status['status'] in ('cancelled','complete')
    if status['status']=='cancelled':
        assert 'cancelled' in status['error']

def test_artifact_path_and_missing_ids():
    assert client.get('/api/models/not-an-id').status_code==400
    assert client.get('/api/models/'+'f'*32).status_code==404
    assert client.get('/api/models/'+'f'*32+'/files/secret').status_code==404
