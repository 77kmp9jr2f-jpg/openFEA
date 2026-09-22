"""Compare an actual stored browser GPU run against the float64 CPU reference."""
import argparse, json
from pathlib import Path
import numpy as np
from backend.storage import resource, read_json
from backend.schemas import Analysis
from backend.solver import solve_model
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('run_id')
parser.add_argument('--output', type=Path, default=Path('evidence/gpu-cpu-comparison.json'))
args=parser.parse_args()
rid=args.run_id
gpu=read_json(resource('runs',rid)/'result.json')
assert gpu['execution']['backend']=='webgpu'
cpu=solve_model(Analysis.model_validate(gpu['setup']),
    reproduction_element_order=gpu.get('element_order', 2),
    reproduction_print_model=(gpu.get('print') or {}).get('geometry_method', 'bounding-box-v1'))
gx=np.load(resource('runs',rid)/'solution.npz')['dof_displacement']
cx=np.load(resource('runs',cpu['id'])/'solution.npz')['dof_displacement']
metrics={'gpu_run':rid,'cpu_run':cpu['id'],'model_id':gpu['model_id'],'mesh_sha256':gpu['mesh_sha256'],
 'device':gpu['execution'],'dofs':gpu['dofs'],'elements':gpu['elements'],
 'print_geometry_method':(gpu.get('print') or {}).get('geometry_method', 'bounding-box-v1'),
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
args.output.parent.mkdir(parents=True,exist_ok=True)
args.output.write_text(json.dumps(metrics,indent=2)+'\n')
print(json.dumps(metrics,indent=2))
assert all(metrics['gates'].values())
