"""Measure orientation/wall/infill/profile effects using frozen STL surfaces.

Run: python -m scripts.compare_slicer_matrix
Requires the installed OrcaSlicer and BBL profiles. Toolpaths are measurement
artifacts with no startup or support operations; never send them to a printer.
No physical-mass, stiffness or universal accuracy claim is made.
"""
import argparse
from datetime import datetime, timezone
import gzip
import json
import math
import os
from pathlib import Path
import re
import subprocess
import tempfile
import xml.etree.ElementTree as ET
import zipfile

import numpy as np

from .compare_slicer_usage import extrusion, prepare_profiles, sha


SCENARIOS = [
    ('baseline', {}),
    ('one-wall', {'wall_count': 1}),
    ('five-walls', {'wall_count': 5}),
    ('infill-60', {'infill_density': .6}),
    ('x90', {'rotation_deg': (90, 0, 0)}),
    ('y90', {'rotation_deg': (0, 90, 0)}),
    ('oblique', {'rotation_deg': (30, 45, 20)}),
    ('x90-one-wall', {'rotation_deg': (90, 0, 0), 'wall_count': 1}),
    ('x90-five-walls', {'rotation_deg': (90, 0, 0), 'wall_count': 5}),
    ('nozzle-06', {'line_width_mm': .6, 'layer_height_mm': .3}),
]


def verify_settings(effective, settings):
    """Check the slicer actually used the requested comparable inputs."""
    scalars = {'wall_loops': settings.wall_count, 'layer_height': settings.layer_height_mm,
        'initial_layer_print_height': settings.layer_height_mm, 'top_shell_layers': settings.top_layers,
        'bottom_shell_layers': settings.bottom_layers, 'top_shell_thickness': 0,
        'bottom_shell_thickness': 0, 'enable_support': 0, 'skirt_loops': 0,
        'brim_width': 0, 'enable_prime_tower': 0}
    widths = ('line_width', 'initial_layer_line_width', 'inner_wall_line_width',
        'outer_wall_line_width', 'internal_solid_infill_line_width', 'sparse_infill_line_width',
        'top_surface_line_width')
    scalars.update({key: settings.line_width_mm for key in widths})
    for key, value in scalars.items():
        if not math.isclose(float(effective[key]), value, rel_tol=1e-10, abs_tol=1e-10):
            raise ValueError(f'Slicer setting {key} differs: {effective[key]} != {value}')
    for key, value in {'filament_flow_ratio': 1, 'filament_density': 1.24,
                       'filament_diameter': 1.75, 'nozzle_diameter': settings.line_width_mm}.items():
        if len(effective[key]) != 1 or float(effective[key][0]) != value:
            raise ValueError(f'Slicer setting {key} differs: {effective[key]} != [{value}]')
    if float(effective['sparse_infill_density'].removesuffix('%')) != 100*settings.infill_density:
        raise ValueError('Slicer infill density differs.')
    if effective['sparse_infill_pattern'] != settings.infill_pattern or effective['wall_generator'] != 'classic':
        raise ValueError('Slicer infill pattern or wall generator differs.')
    return {key: effective[key] for key in effective if key in scalars or key in (
        'sparse_infill_density', 'sparse_infill_pattern', 'wall_generator', 'nozzle_diameter',
        'filament_flow_ratio', 'filament_density', 'filament_diameter', 'bridge_line_width', 'printer_model')}


def placement_transforms(project, xml_path):
    """Ensure arrange only translates the already oriented STL, never rotates/scales it."""
    with zipfile.ZipFile(project) as archive:
        raw = archive.read('3D/3dmodel.model')
    xml_path.write_bytes(raw)
    root = ET.fromstring(raw)
    transforms = [element.attrib['transform'] for element in root.iter() if 'transform' in element.attrib]
    if not transforms:
        raise ValueError('No placement transforms found in sliced project.')
    for transform in transforms:
        values = np.fromstring(transform, sep=' ')
        if len(values) != 12 or not np.allclose(values[:9], np.eye(3).ravel(), rtol=0, atol=1e-10):
            raise ValueError(f'Slicer changed orientation or scale: {transform}')
    return transforms


def compare(executable, profiles, output, *, only=None):
    from backend.schemas import Material, PrintSettings
    from backend.stl_io import parse_stl, inspect_triangles, write_binary_stl
    from backend.print_geometry import measure_regions
    from backend.print_model import apply_usage, homogenize, rotation_matrix
    temporary = Path(tempfile.mkdtemp(prefix='openfea-slicer-matrix-'))
    artifacts = output.parent/f'{output.stem}-artifacts'
    artifacts.mkdir(parents=True, exist_ok=True)
    prior_path = Path('evidence/slicer-usage-comparison.json')
    prior = json.loads(prior_path.read_text())
    material = Material(name='Illustrative PLA', young_mpa=3500, poisson=.35, yield_mpa=40, density_kg_m3=1240)
    evidence = {'created_at': datetime.now(timezone.utc).isoformat(), 'temporary_directory': str(temporary),
        'scope': 'Exploratory model-only deposition comparison. No post-hoc accuracy gate, physical calibration, stiffness validation or printability acceptance. Oblique/overhung cases intentionally omit supports.',
        'protocol': {'geometries': ['box', 'channel', 'tube'], 'scenarios': SCENARIOS,
            'selected_case_ids': only, 'expected_case_count': len(only) if only else 30,
            'measurement_checks': ['frozen input hash', 'matched effective settings', 'translation-only slicer placement',
                                   'positive role deposition agrees with slicer total within 0.03 mm'],
            'transform': 'STL vertices @ print-to-global rotation matrix; subtract XYZ minima and center XY at (128,128) mm. Matches OpenFEA global-to-print row-vector convention. Slicer arrangement and orientation are disabled.'},
        'slicer': subprocess.run([str(executable), '--help'], capture_output=True, text=True, check=True).stdout.splitlines()[0],
        'frozen_source_record': str(prior_path), 'frozen_source_record_sha256': sha(prior_path),
        'source_hashes': {p: sha(Path(p)) for p in ('backend/print_geometry.py', 'backend/print_model.py',
            'scripts/compare_slicer_usage.py', 'scripts/compare_slicer_matrix.py')}, 'cases': []}
    output.write_text(json.dumps(evidence, indent=2)+'\n')
    for previous in prior['cases']:
        name = previous['name']
        frozen_path = Path(f'evidence/slicer-usage-artifacts/{name}.stl.gz')
        assert sha(frozen_path) == previous['artifacts'][str(frozen_path)]['sha256']
        raw = gzip.decompress(frozen_path.read_bytes())
        triangles = parse_stl(raw)
        inspection = inspect_triangles(triangles)
        for label, changes in SCENARIOS:
            case_id = f'{name}-{label}'
            if only and case_id not in only:
                continue
            settings = PrintSettings(enabled=True, **changes)
            case = {'id': case_id, 'geometry': name, 'scenario': label, 'settings': settings.model_dump(mode='json'),
                    'frozen_stl': str(frozen_path), 'frozen_stl_sha256': sha(frozen_path), 'checks_passed': False}
            folder = temporary/case_id
            folder.mkdir()
            try:
                large = label == 'nozzle-06'
                machine = 'Bambu Lab X1 Carbon 0.6 nozzle' if large else 'Bambu Lab X1 Carbon 0.4 nozzle'
                process = '0.30mm Standard @BBL X1C 0.6 nozzle' if large else '0.20mm Standard @BBL X1C'
                case['profile_source_hashes'] = prepare_profiles(profiles, folder, settings=settings,
                    machine_profile=machine, process_profile=process)
                regions = measure_regions(triangles, settings)
                current = apply_usage(homogenize(inspection['bounds'], material, settings, regions=regions),
                    abs(inspection['signed_volume_mm3']), material.density_kg_m3)
                case.update(regions=regions, openfea_mass_g=current['filament_mass_g'],
                    volume_discretization_relative_error=abs(regions['sampled_solid_volume_mm3']/abs(inspection['signed_volume_mm3'])-1))
                oriented = triangles @ rotation_matrix(settings.rotation_deg)
                oriented -= oriented.min(axis=(0, 1))
                oriented[:, :, :2] += 128-oriented[:, :, :2].max(axis=(0, 1))/2
                source = folder/'input.stl'
                write_binary_stl(source, oriented)
                case['slicer_input_extent_mm'] = np.ptp(parse_stl(source.read_bytes()).reshape(-1, 3), axis=0).tolist()
                command = [str(executable), '--debug', '3', '--logfile', str(folder/'diagnostic.log'),
                    '--datadir', str(temporary/'config'), '--load-settings',
                    str(folder/'machine.json')+';'+str(folder/'process.json'), '--load-filaments', str(folder/'filament.json'),
                    '--slice', '0', '--arrange', '0', '--orient', '0', '--ensure-on-bed', '--outputdir', str(folder/'sliced'),
                    '--export-3mf', 'project.3mf', '--export-settings', str(folder/'effective.json'), str(source)]
                with (folder/'slicer.log').open('w') as log:
                    subprocess.run(command, cwd=folder, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=120)
                case['effective_settings'] = verify_settings(json.loads((folder/'effective.json').read_text()), settings)
                case['placement_transforms'] = placement_transforms(folder/'sliced/project.3mf', folder/'placement.model.xml')
                gcode_path = folder/'sliced/plate_1.gcode'
                gcode = gcode_path.read_text()
                roles = extrusion(gcode)
                length = sum(roles.values())
                stats_length = float(re.search(r'; filament used \[mm\] = ([\d.]+)', gcode)[1])
                if length <= 0 or abs(length-stats_length) > .03:
                    raise ValueError(f'Role deposition {length} differs from slicer total {stats_length}.')
                mass = length*math.pi*1.75**2/4*1.24/1000
                case.update(slicer_mass_g=mass, slicer_deposited_length_mm=length, slicer_total_length_mm=stats_length,
                    deposition_by_role_mm=roles, relative_mass_difference=current['filament_mass_g']/mass-1, checks_passed=True)
            except Exception as exc:
                case['error'] = f'{type(exc).__name__}: {exc}'
            case['artifacts'] = {}
            for filename, suffix in [('input.stl', 'stl'), ('sliced/plate_1.gcode', 'gcode'),
                                     ('effective.json', 'settings.json'), ('slicer.log', 'log'),
                                     ('diagnostic.log', 'diagnostic.log'), ('00000.log', 'native.log'),
                                     ('placement.model.xml', 'placement.model.xml')]:
                source_file = folder/filename
                if source_file.exists():
                    artifact = artifacts/f'{case_id}.{suffix}.gz'
                    artifact.write_bytes(gzip.compress(source_file.read_bytes(), mtime=0))
                    case['artifacts'][str(artifact)] = {'sha256': sha(artifact), 'uncompressed_sha256': sha(source_file)}
            evidence['cases'].append(case)
            output.write_text(json.dumps(evidence, indent=2)+'\n')
            print(case_id, f"difference {100*case['relative_mass_difference']:+.2f}%" if case['checks_passed'] else case['error'], flush=True)
    evidence['completed_case_count'] = len(evidence['cases'])
    evidence['measured_case_count'] = sum(c['checks_passed'] for c in evidence['cases'])
    evidence['all_measurement_checks_passed'] = (len(evidence['cases']) == evidence['protocol']['expected_case_count']
                                              and all(c['checks_passed'] for c in evidence['cases']))
    output.write_text(json.dumps(evidence, indent=2)+'\n')
    return evidence['all_measurement_checks_passed']


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--executable', type=Path, default=Path('/Applications/OrcaSlicer.app/Contents/MacOS/OrcaSlicer'))
    parser.add_argument('--profiles', type=Path, default=Path('/Applications/OrcaSlicer.app/Contents/Resources/profiles/BBL'))
    parser.add_argument('--output', type=Path, default=Path('evidence/slicer-matrix.json'))
    parser.add_argument('--only', nargs='+', help='Explicit geometry-scenario IDs for diagnosis; omit for all 30 cases.')
    args = parser.parse_args()
    os.environ.setdefault('FEAR_DATA_DIR', tempfile.mkdtemp(prefix='openfea-slicer-models-'))
    raise SystemExit(0 if compare(args.executable, args.profiles, args.output, only=args.only) else 1)
