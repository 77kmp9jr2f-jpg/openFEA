"""Verify a final run's archive and independently reproduced solution."""
from pathlib import Path
import json,hashlib,zipfile
import numpy as np
original=json.loads(Path('evidence/demo/result.json').read_text())
folder=Path('/tmp/fear-reproduce-final/reproduced/runs')
rpath=next(folder.glob('*/result.json'))
reproduced=json.loads(rpath.read_text())
with zipfile.ZipFile('evidence/demo/FEA-R-demo-package.zip') as z:
    manifest=json.loads(z.read('manifest.json'))
    for name,digest in manifest.items():assert hashlib.sha256(z.read(name)).hexdigest()==digest
    from io import BytesIO
    gpu=np.load(BytesIO(z.read('solution.npz')))['dof_displacement']
cpu=np.load(rpath.parent/'solution.npz')['dof_displacement']
evidence={'run_id':original['id'],'reference_id':original['setup']['reference_id'],'annotations':len(original['setup']['annotations']),
 'execution':original['execution'],'relative_displacement_error':float(np.linalg.norm(gpu-cpu)/np.linalg.norm(cpu)),
 'peak_stress_relative_error':abs(original['peak_von_mises_mpa']/reproduced['peak_von_mises_mpa']-1),
 'server_verified_relative_residual':original['relative_residual'],'verified_manifest_entries':len(manifest),
 'pdf_sha256':hashlib.sha256(Path('evidence/demo/FEA-R-demo-report.pdf').read_bytes()).hexdigest(),
 'zip_sha256':hashlib.sha256(Path('evidence/demo/FEA-R-demo-package.zip').read_bytes()).hexdigest()}
assert evidence['relative_displacement_error']<1e-5
assert evidence['peak_stress_relative_error']<1e-4
assert evidence['server_verified_relative_residual']<1e-7
Path('evidence/demo/verification.json').write_text(json.dumps(evidence,indent=2))
print(json.dumps(evidence,indent=2))
