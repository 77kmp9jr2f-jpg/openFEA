from pathlib import Path
import json, os, uuid

ROOT = Path(__file__).resolve().parents[1]
DATA = Path(os.environ.get('FEAR_DATA_DIR', ROOT / 'data')).resolve()
for name in ('models','runs','images','steps','studies','jobs','systems'):
    (DATA/name).mkdir(parents=True,exist_ok=True)

def identifier():
    return uuid.uuid4().hex

def write_json(path: Path, value):
    temp = path.with_name(path.name + '.' + identifier() + '.tmp')
    temp.write_text(json.dumps(value,allow_nan=False),encoding='utf-8')
    temp.replace(path)

def read_json(path: Path):
    return json.loads(path.read_text(encoding='utf-8'))

def resource(group: str, resource_id: str):
    if len(resource_id) != 32 or any(c not in '0123456789abcdef' for c in resource_id):
        raise ValueError('Invalid resource identifier.')
    return DATA / group / resource_id
