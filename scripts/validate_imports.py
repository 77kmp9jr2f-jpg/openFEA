"""Known-CAD import/refinement checks; run with `python -m scripts.validate_imports`.

Uses isolated temporary data by default. All dimensions/materials are synthetic
specifications, not physical measurements. The JSON retains failures as well as
passing cases; a failed gate returns a nonzero exit code.
"""
from pathlib import Path
import argparse
import hashlib
import json
import math
import os
import shutil
import tempfile
from datetime import datetime, timezone

import numpy as np

GATES = {
    'relative_residual': 1e-7,
    'relative_force_balance': 1e-7,
    'relative_moment_balance': 1e-7,
    'cad_input_volume_relative_error': 1e-8,
    'stl_input_volume_relative_error': .01,
    'refinement_relative_change': .02,
    'import_solution_relative_difference': .05,
    'prismatic_analytic_relative_error': .03,
}


def fixtures():
    from backend.schemas import Geometry, Feature
    return [
        ('tube', Geometry(name='Known tube 60 x OD20 x ID12', kind='shaft',
                          length=60, width=20, hole_diameter=12),
         60 * math.pi * (10**2 - 6**2), True),
        ('thin_channel', Geometry(name='Known open channel with 2 mm walls', kind='custom',
            features=[Feature(size=(60, 24, 16)),
                      Feature(operation='cut', origin=(-1, 2, 2), size=(62, 20, 15))]),
         60 * (24 * 16 - 20 * 14), True),
        ('perforated_plate', Geometry(name='Known asymmetric two-bore plate', kind='custom',
            features=[Feature(size=(60, 40, 6)),
                      Feature(operation='cut', primitive='cylinder', origin=(15, 12, -1),
                              axis=(0, 0, 8), radius=3),
                      Feature(operation='cut', primitive='cylinder', origin=(43, 27, -1),
                              axis=(0, 0, 8), radius=5)]),
         60 * 40 * 6 - math.pi * (3**2 + 5**2) * 6, False),
    ]


def end_faces(model, x):
    """Identify every end patch geometrically; face IDs are revision-specific."""
    points = np.asarray(model['nodes'])
    found = []
    for face in model['faces']:
        triangles = points[np.asarray(face['triangles'])]
        if not np.allclose(triangles[:, :, 0], x, atol=1e-6, rtol=0):
            continue
        area = np.linalg.norm(np.cross(triangles[:, 1] - triangles[:, 0],
                                       triangles[:, 2] - triangles[:, 0]), axis=1).sum() / 2
        found.append((face['id'], float(area)))
    if not found:
        raise ValueError(f'No complete planar end patches at X={x}.')
    return found


def solve_case(model):
    from backend.schemas import Analysis, Material
    from backend.solver import solve_model
    fixed, loaded = end_faces(model, 0), end_faces(model, 60)
    area = sum(a for _, a in loaded)
    # Split the prescribed 100 N over all loaded patches by their actual mesh
    # areas, retaining uniform traction after STL face classification.
    setup = Analysis(model_id=model['id'], confirmed=True,
        material=Material(name='Synthetic validation material', young_mpa=210000,
                          poisson=0, yield_mpa=250, density_kg_m3=7850),
        fixed_faces=[fid for fid, _ in fixed],
        loads=[{'face_id': fid, 'vector': (100 * a / area, 0, 0)} for fid, a in loaded],
        notes='Known-CAD import validation. Synthetic dimensions and inputs; isotropic solid, no print calibration.')
    result = solve_model(setup)
    return {k: result[k] for k in ('id', 'elements', 'dofs', 'element_order', 'versions', 'seconds',
        'max_displacement_mm', 'strain_energy_nmm', 'relative_residual',
        'force_balance_error_n', 'moment_balance_error_nmm', 'mesh_volume_mm3')} | {
        'model_id': model['id'], 'geometry_sha256': model['sha256'],
        'mesh_sha256': model['mesh_sha256'], 'volume_mm3': model['volume_mm3'],
        'bounds': model['bounds'], 'min_quality': model['min_quality'],
        'loaded_area_mm2': area, 'setup': setup.model_dump(mode='json'),
    }


def validate(output, names=None):
    from backend.geometry import build_model
    from backend.schemas import Geometry
    from backend.storage import DATA, resource, identifier
    from backend.stl_io import store_stl
    evidence = {'created_at': datetime.now(timezone.utc).isoformat(),
                'source_hashes': {name: hashlib.sha256(Path(name).read_bytes()).hexdigest()
                    for name in ('backend/geometry.py', 'backend/solver.py', 'backend/stl_io.py',
                                 'backend/schemas.py', 'requirements.txt')},
                'scope': 'Known synthetic CAD; axial loading with Poisson ratio zero; isotropic CPU P2 validation. Two-level refinement comparison, not asymptotic convergence. No bending, stress, dense-STL simplification, GPU, generated-image or physical acceptance claim.',
                'gates': GATES, 'data_directory': str(DATA), 'fixtures': [], 'passed': False}
    for name, spec, exact_volume, prismatic in fixtures():
        if names and name not in names:
            continue
        row = {'name': name, 'specification': spec.model_dump(mode='json'),
               'exact_volume_mm3': exact_volume, 'cases': {}, 'checks': []}
        evidence['fixtures'].append(row)
        def check(label, value, limit):
            row['checks'].append({'gate': label, 'value': float(value),
                                  'limit': limit, 'passed': bool(value <= limit)})
        try:
            # Freeze one source surface for both STL remesh sizes; a changing
            # input surface would conflate import error and mesh convergence.
            source = build_model(spec.model_copy(update={'mesh_size': 2.0}))
            source_folder = resource('models', source['id'])
            upload = store_stl((source_folder/'model.stl').read_bytes(), name+'.stl')
            sid = identifier()
            shutil.copyfile(source_folder/'model.step', resource('steps', sid).with_suffix('.step'))
            row['source'] = {'model_id': source['id'], 'stl_sha256': hashlib.sha256(
                (source_folder/'model.stl').read_bytes()).hexdigest(), 'inspection': upload}
            cases = [('cad_coarse', spec, 4), ('cad_fine', spec, 2.5),
                     ('step', Geometry(kind='step', step_id=sid, provenance='step_import'), 2.5),
                     ('stl_coarse', Geometry(kind='stl', stl_id=upload['id'], provenance='stl_import'), 4),
                     ('stl_fine', Geometry(kind='stl', stl_id=upload['id'], provenance='stl_import'), 2.5)]
            for label, geometry, size in cases:
                print(f'{name}: {label} ({size:g} mm)', flush=True)
                model = build_model(geometry.model_copy(update={'mesh_size': size}))
                case = row['cases'][label] = solve_case(model)
                # Record tetrahedral volume separately from exact CAD or input
                # STL volume. No post-hoc acceptance threshold for mesh volume.
                case['mesh_volume_relative_error'] = abs(case['mesh_volume_mm3']/exact_volume-1)
                check(label+': residual', case['relative_residual'], GATES['relative_residual'])
                check(label+': force balance / 100 N', case['force_balance_error_n']/100, GATES['relative_force_balance'])
                check(label+': moment balance / 6000 N mm', case['moment_balance_error_nmm']/6000, GATES['relative_moment_balance'])
                check(label+': input-solid volume error', abs(case['volume_mm3']/exact_volume-1),
                      GATES['stl_input_volume_relative_error'] if label.startswith('stl') else GATES['cad_input_volume_relative_error'])
                if prismatic:
                    exact_tip = 100 * 60 / (210000 * (exact_volume/60))
                    check(label+': exact prismatic displacement', abs(case['max_displacement_mm']/exact_tip-1), GATES['prismatic_analytic_relative_error'])
            for metric in ('max_displacement_mm', 'strain_energy_nmm'):
                for source_type in ('cad', 'stl'):
                    a, b = (row['cases'][source_type+'_'+level][metric] for level in ('coarse', 'fine'))
                    check(source_type+': refinement '+metric, abs(a/b-1), GATES['refinement_relative_change'])
                for source_type in ('step', 'stl_fine'):
                    check(source_type+': CAD agreement '+metric,
                          abs(row['cases'][source_type][metric]/row['cases']['cad_fine'][metric]-1),
                          GATES['import_solution_relative_difference'])
        except Exception as exc:
            row['error'] = f'{type(exc).__name__}: {exc}'
        row['passed'] = not row.get('error') and bool(row['checks']) and all(c['passed'] for c in row['checks'])
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(evidence, indent=2)+'\n')
    evidence['passed'] = bool(evidence['fixtures']) and all(r['passed'] for r in evidence['fixtures'])
    output.write_text(json.dumps(evidence, indent=2)+'\n')
    for row in evidence['fixtures']:
        print(row['name'], 'PASS' if row['passed'] else 'FAIL', row.get('error', ''), flush=True)
        for check in row['checks']:
            if not check['passed']:
                print(' ', check, flush=True)
    return evidence['passed']


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('evidence/import-validation.json'))
    parser.add_argument('--fixture', choices=['tube', 'thin_channel', 'perforated_plate'], action='append')
    args = parser.parse_args()
    os.environ.setdefault('FEAR_DATA_DIR', tempfile.mkdtemp(prefix='openfea-import-validation-'))
    raise SystemExit(0 if validate(args.output, args.fixture) else 1)
