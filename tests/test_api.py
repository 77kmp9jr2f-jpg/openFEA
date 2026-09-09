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

def test_artifact_path_and_missing_ids():
    assert client.get('/api/models/not-an-id').status_code==400
    assert client.get('/api/models/'+'f'*32).status_code==404
    assert client.get('/api/models/'+'f'*32+'/files/secret').status_code==404
