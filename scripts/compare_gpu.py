"""Compare an actual stored browser GPU run against the float64 CPU reference."""
import sys, json
from pathlib import Path
import numpy as np
from backend.storage import resource, read_json
from backend.schemas import Analysis
from backend.solver import solve_model
rid=sys.argv[1]
gpu=read_json(resource('runs',rid)/'result.json')
assert gpu['execution']['backend']=='webgpu'
cpu=solve_model(Analysis.model_validate(gpu['setup']))
gx=np.load(resource('runs',rid)/'solution.npz')['dof_displacement']
cx=np.load(resource('runs',cpu['id'])/'solution.npz')['dof_displacement']
metrics={'gpu_run':rid,'cpu_run':cpu['id'],'model_id':gpu['model_id'],'mesh_sha256':gpu['mesh_sha256'],
 'device':gpu['execution'],'dofs':gpu['dofs'],'elements':gpu['elements'],
 'displacement_relative_l2_error':float(np.linalg.norm(gx-cx)/np.linalg.norm(cx)),
 'peak_stress_relative_error':abs(gpu['peak_von_mises_mpa']/cpu['peak_von_mises_mpa']-1),
 'gpu_relative_residual':gpu['relative_residual'],'cpu_relative_residual':cpu['relative_residual'],
 'gpu_seconds':gpu['seconds'],'cpu_seconds':cpu['seconds'],
 'gpu_peak_stress_mpa':gpu['peak_von_mises_mpa'],'gpu_max_displacement_mm':gpu['max_displacement_mm'],
 'gates':{'relative_displacement_error_lt_1e-5':False,'relative_stress_error_lt_1e-4':False,'gpu_residual_lt_1e-7':False}}
metrics['gates']={
 'relative_displacement_error_lt_1e-5':metrics['displacement_relative_l2_error']<1e-5,
 'relative_stress_error_lt_1e-4':metrics['peak_stress_relative_error']<1e-4,
 'gpu_residual_lt_1e-7':gpu['relative_residual']<1e-7}
Path('evidence/gpu-cpu-comparison.json').write_text(json.dumps(metrics,indent=2))
print(json.dumps(metrics,indent=2))
assert all(metrics['gates'].values())
