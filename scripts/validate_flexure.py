"""Three-level bending/torsion validation: python -m scripts.validate_flexure.

Synthetic isotropic CPU/P2 cases, using only supported CSG, fixed faces and
uniform face forces. Runs in isolated temporary storage by default. No stress,
print calibration, asymptotic convergence or GPU-performance claim.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import tempfile

import numpy as np

GATES = {'analytic_relative_error': .05, 'successive_refinement_change': .02,
         'stl_relative_difference': .03, 'relative_residual': 1e-7,
         'relative_force_balance': 1e-7, 'relative_moment_balance': 1e-7}
SOURCES = {
    'cantilever': 'https://ocw.mit.edu/courses/1-050-solid-mechanics-fall-2004/fd4eff39aec922b8c07660006f40686e_pset04_11.pdf',
    'circular_torsion': 'https://ocw.mit.edu/courses/3-11-mechanics-of-materials-fall-1999/0e0845a9e3abe430080eaffb0c5015ba_MIT3_11F99_torsion.pdf',
}


def planar_faces(model, axis, coordinate):
    points = np.asarray(model['nodes'])
    found = []
    for face in model['faces']:
        triangles = points[np.asarray(face['triangles'])]
        if np.allclose(triangles[:, :, axis], coordinate, rtol=0, atol=1e-6):
            area = np.linalg.norm(np.cross(triangles[:, 1]-triangles[:, 0],
                                           triangles[:, 2]-triangles[:, 0]), axis=1).sum()/2
            found.append((face['id'], float(area)))
    if not found:
        raise ValueError(f'No complete planar patches at axis {axis} = {coordinate}.')
    return found


def distributed_loads(patches, vector):
    area = sum(a for _, a in patches)
    return [{'face_id': fid, 'vector': (np.asarray(vector)*a/area).tolist()}
            for fid, a in patches]


def channel():
    from backend.schemas import Geometry, Feature
    return Geometry(name='Synthetic 160 mm channel, 2 mm walls', kind='custom',
        features=[Feature(size=(160, 24, 16)),
                  Feature(operation='cut', origin=(-1, 2, 2), size=(162, 20, 15))])


def torque_tube():
    from backend.schemas import Geometry, Feature
    # The end bar gives two actual flat loading patches. A force couple applies
    # torque with zero net force; there is no unsupported moment boundary type.
    return Geometry(name='Synthetic tube with torque loading bar', kind='custom',
        features=[Feature(primitive='cylinder', axis=(120, 0, 0), radius=6),
                  Feature(operation='cut', primitive='cylinder', origin=(-1, 0, 0),
                          axis=(122, 0, 0), radius=4),
                  Feature(origin=(110, -10, -2), size=(10, 20, 4))])


def bending_reference():
    # Exact centroid and second moment of the section (base plus two uprights).
    rectangles = [(24, 2, 1), (2, 14, 9), (2, 14, 9)]
    area = sum(b*h for b, h, z in rectangles)
    centroid = sum(b*h*z for b, h, z in rectangles)/area
    inertia = sum(b*h**3/12+b*h*(z-centroid)**2 for b, h, z in rectangles)
    return {'area_mm2': area, 'centroid_z_mm': centroid, 'I_y_mm4': inertia,
            'expected': 10*160**3/(3*210000*inertia), 'metric': 'mean_tip_z_mm',
            'formula': 'F L^3 / (3 E I_y); slender Euler-Bernoulli reference, not exact 3D clamping/shear.'}


def torsion_reference():
    shear = 210000/(2*(1+.3))
    polar = math.pi*(6**4-4**4)/2
    return {'torque_nmm': 200, 'G_mpa': shear, 'J_mm4': polar,
            'expected': 200/(shear*polar), 'metric': 'twist_rate_rad_per_mm',
            'formula': 'd(theta)/dx = T/(G J); fit only X=24..84 mm, away from clamp and loading bar.'}


def mean_tip(model, result):
    from backend.storage import resource
    from skfem import MeshTet, FacetBasis, ElementVector, ElementTetP2
    with np.load(resource('models', model['id'])/'mesh.npz') as mesh_data:
        mesh = MeshTet(mesh_data['points'].T, mesh_data['tets'].T)
    with np.load(resource('runs', result['id'])/'solution.npz') as solution:
        x = solution['dof_displacement']
    facet_points = mesh.p[:, mesh.facets]
    selected = np.flatnonzero(np.all(np.isclose(facet_points[0], 160, atol=1e-6, rtol=0), axis=0))
    fb = FacetBasis(mesh, ElementVector(ElementTetP2()), facets=selected, intorder=4)
    return float(-np.sum(fb.interpolate(x)[2]*fb.dx)/fb.dx.sum())


def twist_rate(model, result):
    points = np.asarray(model['nodes'])
    mask = (points[:, 0] >= 24) & (points[:, 0] <= 84)
    x, y, z = points[mask].T
    uy, uz = np.asarray(result['displacement'])[mask, 1:].T
    # theta(x)=theta0+rate*x, allowing linear transverse translations as nuisance
    # terms. Fitted only in the uniform circular shaft; no lug-tip inference.
    ones, zero = np.ones_like(x), np.zeros_like(x)
    matrix = np.vstack([np.column_stack([-z, -x*z, ones, x, zero, zero]),
                        np.column_stack([y, x*y, zero, zero, ones, x])])
    values = np.concatenate([uy, uz])
    fit, _, rank, _ = np.linalg.lstsq(matrix, values, rcond=None)
    if rank != 6:
        raise ValueError('Insufficient shaft samples for independent twist fit.')
    return float(fit[1]), float(np.linalg.norm(matrix@fit-values)/np.linalg.norm(values)), int(mask.sum())


def run_case(name, model):
    from backend.schemas import Analysis, Material
    from backend.solver import solve_model
    fixed = [fid for fid, _ in planar_faces(model, 0, 0)]
    if name == 'channel_bending':
        loads = distributed_loads(planar_faces(model, 0, 160), [0, 0, -10])
    else:
        loads = (distributed_loads(planar_faces(model, 1, 10), [0, 0, 10]) +
                 distributed_loads(planar_faces(model, 1, -10), [0, 0, -10]))
    setup = Analysis(model_id=model['id'], confirmed=True, fixed_faces=fixed, loads=loads,
        material=Material(name='Synthetic isotropic validation material', young_mpa=210000,
                          poisson=.3, yield_mpa=250, density_kg_m3=7850),
        notes='Software validation only: supported uniform face forces, no print homogenization.')
    result = solve_model(setup)
    case = {k: result[k] for k in ('id', 'model_id', 'elements', 'dofs', 'element_order', 'versions',
        'seconds', 'relative_residual', 'strain_energy_nmm', 'mesh_volume_mm3',
        'force_balance_error_n', 'moment_balance_error_nmm', 'model_sha256', 'mesh_sha256')}
    case['setup'] = setup.model_dump(mode='json')
    if name == 'channel_bending':
        case['metric'] = mean_tip(model, result)
    else:
        case['metric'], case['twist_fit_relative_residual'], case['twist_fit_nodes'] = twist_rate(model, result)
    return case


def evaluate_fixture(row):
    """Evaluate retained raw solve metrics without re-running or changing them."""
    row['checks'] = []
    def check(label, value, gate):
        row['checks'].append({'gate': label, 'value': float(value),
                              'limit': GATES[gate], 'passed': bool(value <= GATES[gate])})
    for label, case in row['cases'].items():
        force_scale = sum(np.linalg.norm(load['vector']) for load in case['setup']['loads'])
        check(label+': analytic response', abs(case['metric']/row['reference']['expected']-1), 'analytic_relative_error')
        check(label+': residual', case['relative_residual'], 'relative_residual')
        check(label+f': force equilibrium / {force_scale:g} N', case['force_balance_error_n']/force_scale, 'relative_force_balance')
        moment = 1600 if row['name'] == 'channel_bending' else 200
        check(label+': moment equilibrium', case['moment_balance_error_nmm']/moment, 'relative_moment_balance')
    if all(label in row['cases'] for label in ('coarse', 'medium', 'fine', 'stl')):
        for a, b in [('coarse', 'medium'), ('medium', 'fine')]:
            check(a+' to '+b+': response change', abs(row['cases'][a]['metric']/row['cases'][b]['metric']-1), 'successive_refinement_change')
        check('STL to fine CAD: response', abs(row['cases']['stl']['metric']/row['cases']['fine']['metric']-1), 'stl_relative_difference')
    row['passed'] = not row.get('error') and len(row['cases']) == 4 and all(c['passed'] for c in row['checks'])


def validate(output, names=None):
    from backend.geometry import build_model
    from backend.schemas import Geometry
    from backend.storage import DATA, resource
    from backend.stl_io import store_stl
    evidence = {'created_at': datetime.now(timezone.utc).isoformat(), 'gates': GATES,
        'sources': SOURCES, 'data_directory': str(DATA), 'fixtures': [], 'passed': False,
        'scope': 'Synthetic isotropic CPU P2; three CAD mesh levels and fixed-source STL import. No stress, asymptotic convergence, print calibration or GPU claim.',
        'source_hashes': {p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
            for p in ('backend/geometry.py', 'backend/solver.py', 'backend/stl_io.py',
                      'backend/schemas.py', 'requirements.txt')}}
    for name, factory, reference in [('channel_bending', channel, bending_reference),
                                      ('tube_torsion', torque_tube, torsion_reference)]:
        if names and name not in names:
            continue
        spec, oracle = factory(), reference()
        row = {'name': name, 'specification': spec.model_dump(mode='json'),
               'reference': oracle, 'cases': {}, 'checks': []}
        evidence['fixtures'].append(row)
        try:
            sizes = (6, 4, 2.5, 2.5) if name == 'channel_bending' else (2, 1.5, 1.1, 1.1)
            for label, size in zip(('coarse', 'medium', 'fine', 'stl'), sizes):
                geometry = spec
                if label == 'stl':
                    # Freeze the medium CAD tessellation as the independent source.
                    source_path = resource('models', row['cases']['medium']['model_id'])/'model.stl'
                    source = store_stl(source_path.read_bytes(), name+'.stl')
                    row['stl_source'] = {'inspection': source,
                        'sha256': hashlib.sha256(source_path.read_bytes()).hexdigest()}
                    geometry = Geometry(kind='stl', stl_id=source['id'], provenance='stl_import')
                print(f'{name}: {label}, mesh {size} mm', flush=True)
                model = build_model(geometry.model_copy(update={'mesh_size': size}))
                case = row['cases'][label] = run_case(name, model)
                case['requested_mesh_size_mm'] = size
        except Exception as exc:
            row['error'] = f'{type(exc).__name__}: {exc}'
        evaluate_fixture(row)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(evidence, indent=2)+'\n')
        print(name, 'PASS' if row['passed'] else 'FAIL', row.get('error', ''), flush=True)
    evidence['passed'] = bool(evidence['fixtures']) and all(r['passed'] for r in evidence['fixtures'])
    output.write_text(json.dumps(evidence, indent=2)+'\n')
    return evidence['passed']


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('evidence/flexure-validation.json'))
    parser.add_argument('--fixture', choices=['channel_bending', 'tube_torsion'], action='append')
    parser.add_argument('--recheck', type=Path, help='Re-evaluate saved raw metrics only; retains original solve provenance and records a new gate-evaluator hash.')
    args = parser.parse_args()
    if args.recheck:
        evidence = json.loads(args.recheck.read_text())
        for row in evidence['fixtures']:
            evaluate_fixture(row)
        evidence['gates'] = GATES
        evidence['passed'] = bool(evidence['fixtures']) and all(row['passed'] for row in evidence['fixtures'])
        evidence['gate_recheck'] = {'created_at': datetime.now(timezone.utc).isoformat(),
            'evaluator_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'scope': 'Raw solve records unchanged; force imbalance normalized by sum of applied load magnitudes (10 N bending, 20 N couple).'}
        args.output.write_text(json.dumps(evidence, indent=2)+'\n')
        raise SystemExit(0 if evidence['passed'] else 1)
    os.environ.setdefault('FEAR_DATA_DIR', tempfile.mkdtemp(prefix='openfea-flexure-validation-'))
    raise SystemExit(0 if validate(args.output, args.fixture) else 1)
