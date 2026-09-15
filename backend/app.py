from pathlib import Path
import base64, io, json, time
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from PIL import Image, ImageOps, UnidentifiedImageError
from .storage import ROOT, DATA, identifier, resource, write_json, read_json
from .schemas import Geometry, Analysis, AssistantRequest, ImageInput, Study, GPUSolution, SimulationContext, PrintPreviewRequest
from .jobs import start_job
from .assistant import assistant_status

app = FastAPI(title='openFEA',version='0.1.0')
Image.MAX_IMAGE_PIXELS = 25_000_000

@app.middleware('http')
async def local_boundary(request: Request, call_next):
    # Loopback-only local application. Reject foreign browser origins and DNS rebinding.
    if request.url.hostname not in ('localhost','127.0.0.1','testserver'):
        return JSONResponse({'detail':'Use the localhost address.'},status_code=403)
    origin = request.headers.get('origin')
    if origin and origin not in ('http://localhost:8000','http://127.0.0.1:8000','http://localhost:5173','http://127.0.0.1:5173'):
        return JSONResponse({'detail':'Foreign origin rejected.'},status_code=403)
    if request.method in ('POST','PUT'):
        body = await request.body()
        if len(body)>20_000_000:
            return JSONResponse({'detail':'Request is too large (20 MB maximum).'},status_code=413)
    return await call_next(request)

@app.exception_handler(ValueError)
async def value_error(request,exc):
    return JSONResponse({'detail':str(exc)},status_code=400)

@app.exception_handler(FileNotFoundError)
async def missing(request,exc):
    return JSONResponse({'detail':'The requested local artifact was not found.'},status_code=404)

@app.get('/api/health')
def health():
    return {'ok':True,'version':'0.1.0','assistant':assistant_status(),'solver':'scikit-fem · quadratic tetrahedra'}

@app.post('/api/models')
def model(spec: Geometry):
    return start_job('model',spec.model_dump())

@app.get('/api/models/{mid}')
def get_model(mid: str):
    return read_json(resource('models',mid)/'model.json')

@app.post('/api/solve')
def solve(setup: Analysis):
    return start_job('solve',setup.model_dump())

@app.post('/api/gpu/prepare')
def gpu_prepare(setup: Analysis):
    return start_job('gpu_prepare',setup.model_dump())

@app.post('/api/gpu/finish')
def gpu_finish(solution: GPUSolution):
    return start_job('gpu_finish',solution.model_dump())

@app.get('/api/runs/{rid}')
def run(rid: str):
    return read_json(resource('runs',rid)/'result.json')

@app.post('/api/assistant')
def assistant(req: AssistantRequest):
    return start_job('assistant',req.model_dump())

@app.post('/api/setup-proposals/{pid}/apply')
def apply_simulation_proposal(pid: str, context: SimulationContext):
    from .simulation_proposals import apply_setup
    return apply_setup(pid,context.model_dump())

@app.get('/api/jobs/{jid}')
def job(jid: str):
    return read_json(resource('jobs',jid)/'status.json')

@app.post('/api/jobs/{jid}/cancel')
def cancel(jid: str):
    from .jobs import cancel_job
    return cancel_job(jid)

@app.post('/api/images')
def upload_image(image: ImageInput):
    try:
        header,encoded = image.data_url.split(',',1)
        if header not in ('data:image/png;base64','data:image/jpeg;base64','data:image/webp;base64'):
            raise ValueError('Use a PNG, JPEG or WebP image.')
        raw = base64.b64decode(encoded,validate=True)
        with Image.open(io.BytesIO(raw)) as opened:
            im = ImageOps.exif_transpose(opened).convert('RGB')
            im.thumbnail((2048,2048))
    except (UnidentifiedImageError,Image.DecompressionBombError,Image.DecompressionBombWarning) as exc:
        raise ValueError('Use a valid image under 25 megapixels.') from exc
    iid = identifier(); path = resource('images',iid).with_suffix('.png'); im.save(path)
    meta = {'id':iid,'name':image.name,'width':im.width,'height':im.height,'url':f'/api/images/{iid}'}
    write_json(path.with_suffix('.json'),meta)
    return meta

@app.get('/api/images/{iid}')
def image(iid: str):
    return FileResponse(resource('images',iid).with_suffix('.png'),media_type='image/png')

@app.post('/api/stls')
async def upload_stl(request: Request):
    from .stl_io import store_stl
    content = await request.body()
    if not content or len(content) > 15_000_000:
        raise ValueError('Upload an STL under 15 MB.')
    name = request.headers.get('x-filename', 'import.stl')[:160]
    return store_stl(content, name)

@app.get('/api/stls/{sid}')
def get_stl(sid: str, scale: float = 1.0):
    from .stl_io import load_inspection
    return load_inspection(sid, scale)

@app.post('/api/print-preview')
def print_preview(body: PrintPreviewRequest):
    from .print_model import homogenize, apply_usage
    model = read_json(resource('models', body.model_id) / 'model.json')
    settings = body.print if body.print.enabled else body.print.model_copy(update={'enabled': True})
    homogenized = homogenize(model['bounds'], body.material, settings)
    return {**homogenized, **apply_usage(homogenized, model['volume_mm3'], body.material.density_kg_m3)}

@app.get('/api/runs/{aid}/compare/{bid}')
def compare_runs(aid: str, bid: str):
    from .print_model import compare_results
    return compare_results(read_json(resource('runs', aid) / 'result.json'),
                           read_json(resource('runs', bid) / 'result.json'))

@app.post('/api/steps')
async def upload_step(request: Request):
    content = await request.body()
    if not content or len(content)>15_000_000 or b'ISO-10303-21' not in content[:1000]:
        raise ValueError('Upload a STEP (.step/.stp) file under 15 MB.')
    sid = identifier(); resource('steps',sid).with_suffix('.step').write_bytes(content)
    return {'id':sid,'units':'Imported and converted to millimetres by OpenCASCADE; verify displayed bounds.'}

@app.get('/api/models/{mid}/files/{name}')
def model_file(mid: str,name: str):
    if name not in ('model.step','model.stl','mesh.msh','model.json','mesh.npz'):
        raise HTTPException(404)
    return FileResponse(resource('models',mid)/name,filename=name)

@app.get('/api/studies')
def studies():
    return sorted([{'id':p.stem,**{k:v for k,v in read_json(p).items() if k!='state'}} for p in (DATA/'studies').glob('*.json')],key=lambda x:x['updated_at'],reverse=True)

@app.post('/api/studies')
def save_study(study: Study):
    sid = identifier()
    write_json(resource('studies',sid).with_suffix('.json'),{**study.model_dump(),'updated_at':time.time()})
    return {'id':sid}

@app.get('/api/studies/{sid}')
def study(sid: str):
    return read_json(resource('studies',sid).with_suffix('.json'))

@app.get('/api/runs/{rid}/report/{format}')
def report(rid: str,format: str):
    from .report import export_report
    if format not in ('html','pdf','zip','json'):
        raise HTTPException(404)
    path = export_report(rid,format)
    return FileResponse(path,filename=f'openFEA-{rid[:8]}.{format}')

if (ROOT/'dist').exists():
    app.mount('/',StaticFiles(directory=ROOT/'dist',html=True),name='frontend')
