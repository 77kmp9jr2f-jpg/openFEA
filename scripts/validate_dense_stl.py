"""Validate dense imports against frozen CAD surfaces and prior axial references.

Run: python -m scripts.validate_dense_stl [--skip-solve] [--output PATH]
Uses isolated temporary storage. Triangle subdivision adds redundant surface
tessellation, not new CAD curvature. Gates are scoped to these synthetic inputs.
"""
import argparse
import gzip
import hashlib
import json
import os
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

GATES = {'relative_volume_change': .01, 'relative_sample_distance': 1e-4,
         'section_boundary_deviation_mm': .1, 'section_area_change': .02,
         'axial_response_relative_difference': .05, 'relative_residual': 1e-7,
         'relative_force_balance': 1e-7, 'relative_moment_balance': 1e-7}


def subdivide(t):
    a, b, c = t[:, 0], t[:, 1], t[:, 2]
    ab, bc, ca = (a+b)/2, (b+c)/2, (c+a)/2
    return np.concatenate([np.stack(x, axis=1) for x in
        [(a, ab, ca), (ab, b, bc), (ca, bc, c), (ab, bc, ca)]])


def validate(output, skip_solve=False):
    from shapely import hausdorff_distance
    from backend.stl_io import parse_stl, store_stl, write_binary_stl, scaled_stl_path
    from backend.storage import DATA, resource
    from backend.print_geometry import section
    from backend.geometry import build_model
    from backend.schemas import Geometry
    from scripts.validate_imports import solve_case

    fixture_dir = Path(__file__).resolve().parents[1]/'tests/fixtures/dense-stl'
    manifest = json.loads((fixture_dir/'manifest.json').read_text())
    result = {'created_at': datetime.now(timezone.utc).isoformat(), 'gates': GATES,
        'scope': manifest['scope'] + ' Surface samples and selected sections do not certify global Hausdorff error, self-intersections or arbitrary small-feature preservation. Axial CPU/P2 comparison only; no printed-material calibration.',
        'data_directory': str(DATA), 'source_hashes': {name: hashlib.sha256(Path(name).read_bytes()).hexdigest()
            for name in ('backend/stl_io.py', 'backend/stl_fidelity.py', 'backend/geometry.py',
                         'requirements.txt', 'scripts/validate_dense_stl.py')},
        'solve_exercised': not skip_solve, 'cases': [], 'passed': False}
    for fixture in manifest['fixtures']:
        start = time.monotonic()
        row = {'name': fixture['name'], 'checks': []}
        result['cases'].append(row)
        def check(name, value, limit=0):
            row['checks'].append({'gate': name, 'value': float(value), 'limit': limit,
                                  'passed': bool(value <= limit)})
        try:
            raw = gzip.decompress((fixture_dir/fixture['file']).read_bytes())
            assert hashlib.sha256(raw).hexdigest() == fixture['sha256']
            coarse = parse_stl(raw)
            dense = coarse
            while len(dense) <= 80000:
                dense = subdivide(dense)
            path = DATA/(row['name']+'-dense.stl')
            write_binary_stl(path, dense)
            # Exercise exactly the uploaded binary precision and production path.
            upload = store_stl(path.read_bytes(), path.name)
            row.update(source_triangles=len(dense), frozen_source_sha256=fixture['sha256'],
                       inspection=upload, preprocessing_seconds=time.monotonic()-start)
            try:
                scaled_stl_path(upload['id'], 1)
                check('explicit preprocessing review required', 1)
            except ValueError as exc:
                check('explicit preprocessing review required', 0 if 'review' in str(exc) else 1)
            working_path = scaled_stl_path(upload['id'], 1, accept_preprocessing=True)
            working = parse_stl(working_path.read_bytes())
            check('closed single consistently wound boundary', not upload['watertight'])
            check('boundary topology retained', abs(upload['euler_characteristic'] - upload['source_inspection']['euler_characteristic']))
            pre = upload['preprocessing']
            check('volume change', pre['relative_volume_change'], GATES['relative_volume_change'])
            check('sampled surface deviation / longest extent', pre['surface_samples']['relative_to_longest_extent'], GATES['relative_sample_distance'])
            axis = 2 if row['name'] == 'perforated_plate' else 0
            order = [i for i in range(3) if i != axis]+[axis]
            row['sections'] = []
            stations = [1., 3., 5.] if axis == 2 else [1., 10., 30., 50., 59.]
            for z in stations:
                a, b = section(coarse[:, :, order], z), section(working[:, :, order], z)
                holes = lambda p: sum(len(g.interiors) for g in ([p] if p.geom_type == 'Polygon' else p.geoms))
                distance = float(hausdorff_distance(a.boundary, b.boundary, densify=.1))
                area_change = abs(b.area/a.area-1)
                row['sections'].append({'station_mm': z, 'source_holes': holes(a), 'working_holes': holes(b),
                    'boundary_deviation_mm': distance, 'relative_area_change': area_change})
                check(f'section {z:g}: hole count', abs(holes(a)-holes(b)))
                check(f'section {z:g}: area', area_change, GATES['section_area_change'])
                check(f'section {z:g}: sampled boundary distance', distance, GATES['section_boundary_deviation_mm'])
            if not skip_solve:
                print(row['name'], 'build and axial P2 solve', flush=True)
                model = build_model(Geometry(kind='stl', stl_id=upload['id'], mesh_size=2.5,
                    provenance='stl_import', accept_stl_preprocessing=True))
                solved = row['solve'] = solve_case(model)
                reference = row['cad_reference'] = fixture['cad_fine_response']
                for metric in ('max_displacement_mm', 'strain_energy_nmm'):
                    check('CAD agreement: '+metric, abs(solved[metric]/reference[metric]-1), GATES['axial_response_relative_difference'])
                check('residual', solved['relative_residual'], GATES['relative_residual'])
                check('force balance / 100 N', solved['force_balance_error_n']/100, GATES['relative_force_balance'])
                check('moment balance / 6000 N mm', solved['moment_balance_error_nmm']/6000, GATES['relative_moment_balance'])
        except Exception as exc:
            row['error'] = f'{type(exc).__name__}: {exc}'
        row['seconds'] = time.monotonic()-start
        row['passed'] = not row.get('error') and bool(row['checks']) and all(c['passed'] for c in row['checks'])
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, indent=2)+'\n')
        print(row['name'], 'PASS' if row['passed'] else 'FAIL', row.get('error', ''), flush=True)
    result['passed'] = all(r['passed'] for r in result['cases'])
    output.write_text(json.dumps(result, indent=2)+'\n')
    return result['passed']


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('evidence/dense-stl-validation.json'))
    parser.add_argument('--skip-solve', action='store_true')
    args = parser.parse_args()
    os.environ.setdefault('FEAR_DATA_DIR', tempfile.mkdtemp(prefix='openfea-dense-validation-'))
    raise SystemExit(0 if validate(args.output, args.skip_solve) else 1)
