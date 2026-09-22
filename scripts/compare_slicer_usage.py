"""Compare contour estimates to isolated OrcaSlicer toolpaths, not physical mass.

Run from the repository root: python -m scripts.compare_slicer_usage
Installed OrcaSlicer and its BBL profiles are required. Never sends to a printer.
"""
import argparse
from datetime import datetime, timezone
import gzip
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
import tempfile

PROCESS_OVERRIDES = dict(wall_loops='3', layer_height='0.2', initial_layer_print_height='0.2',
    top_shell_layers='4', bottom_shell_layers='4', top_shell_thickness='0', bottom_shell_thickness='0',
    sparse_infill_density='20%', sparse_infill_pattern='gyroid', wall_generator='classic',
    enable_support='0', skirt_loops='0', brim_type='no_brim', brim_width='0', enable_prime_tower='0')
FILAMENT_OVERRIDES = dict(filament_flow_ratio=['1'], filament_density=['1.24'], filament_diameter=['1.75'])
# Measurement-only toolpaths. No heating, homing, purge, timelapse or hardware macros.
MACHINE_OVERRIDES = dict(machine_start_gcode='G90\nM83\nG92 E0\n', machine_end_gcode='M400\n',
    change_filament_gcode='', before_layer_change_gcode='', layer_change_gcode='',
    time_lapse_gcode='', scan_first_layer='0', use_relative_e_distances='1')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare_profiles(source, target):
    paths = {p.stem: p for p in source.rglob('*.json')}
    hashes = {}
    def flatten(name):
        path = paths[name]
        hashes[str(path.relative_to(source))] = sha(path)
        data = json.loads(path.read_text())
        return {**(flatten(data['inherits']) if data.get('inherits') else {}), **data}
    for kind, name, overrides in [
        ('machine', 'Bambu Lab X1 Carbon 0.4 nozzle', MACHINE_OVERRIDES),
        ('process', '0.20mm Standard @BBL X1C', PROCESS_OVERRIDES),
        ('filament', 'Generic PLA', FILAMENT_OVERRIDES),
    ]:
        data = flatten(name)
        data.pop('inherits', None)
        data.update(overrides)
        if kind == 'process':
            for key in data:
                if 'line_width' in key:
                    data[key] = '0.4'
        (target/f'{kind}.json').write_text(json.dumps(data, indent=2)+'\n')
    return hashes


def extrusion(gcode):
    """Sum deposited E on XY moves by model role; exclude retract/prime/custom."""
    role = None
    relative = False
    amount = {}
    for line in gcode.splitlines():
        if line.startswith('; FEATURE: '):
            role = line.removeprefix('; FEATURE: ')
        command = line.split(';')[0].strip()
        if command.startswith('M83'):
            relative = True
        if command.startswith('M82'):
            relative = False
        if not re.match(r'^G[123]\s', command):
            continue
        match = re.search(r'\bE(-?[\d.]+)', command)
        if match and float(match[1]) > 0 and re.search(r'\b[XY]-?[\d.]', command):
            if not relative:
                raise ValueError('This measurement requires relative extrusion.')
            if role in (None, 'Custom', 'Skirt', 'Brim', 'Support', 'Support interface', 'Prime tower'):
                raise ValueError(f'Unexpected non-model deposition: {role}.')
            amount[role] = amount.get(role, 0)+float(match[1])
    return amount


def compare(executable, profiles, output):
    from backend.geometry import build_model
    from backend.schemas import Geometry, Feature, PrintSettings, Material
    from backend.print_geometry import measure_regions
    from backend.print_model import homogenize, apply_usage
    from backend.stl_io import write_binary_stl
    import numpy as np
    temporary = Path(tempfile.mkdtemp(prefix='openfea-slicer-usage-'))
    source_hashes = prepare_profiles(profiles, temporary)
    settings = PrintSettings(enabled=True)
    material = Material(name='Illustrative PLA', young_mpa=3500, poisson=.35, yield_mpa=40, density_kg_m3=1240)
    artifact_dir = output.parent/'slicer-usage-artifacts'
    artifact_dir.mkdir(parents=True, exist_ok=True)
    evidence = {'created_at': datetime.now(timezone.utc).isoformat(), 'temporary_directory': str(temporary),
        'scope': 'Exploratory material-usage comparison only. Not stiffness calibration, physical mass or printer-ready G-code.',
        'slicer': subprocess.run([str(executable), '--help'], capture_output=True, text=True, check=True).stdout.splitlines()[0],
        'profile_source_hashes': source_hashes, 'process_overrides': PROCESS_OVERRIDES,
        'all_process_line_widths_mm': .4, 'filament_overrides': FILAMENT_OVERRIDES,
        'machine_overrides': MACHINE_OVERRIDES, 'print_settings': settings.model_dump(mode='json'),
        'source_hashes': {p: sha(Path(p)) for p in ('backend/print_geometry.py', 'backend/print_model.py', 'scripts/compare_slicer_usage.py')},
        'cases': []}
    factories = [
        ('box', [Feature(size=(40,10,8))]),
        ('channel', [Feature(size=(60,24,16)), Feature(operation='cut', origin=(-1,2,2), size=(62,20,15))]),
        ('tube', [Feature(primitive='cylinder', axis=(0,0,20), radius=10),
                  Feature(operation='cut', primitive='cylinder', origin=(0,0,-1), axis=(0,0,22), radius=8)]),
    ]
    for name, features in factories:
        model = build_model(Geometry(kind='custom', mesh_size=3, features=features))
        triangles = np.asarray(model['nodes'])[np.asarray([t for f in model['faces'] for t in f['triangles']])]
        source = temporary/f'{name}.stl'
        write_binary_stl(source, triangles)
        regions = measure_regions(triangles, settings)
        current = apply_usage(homogenize(model['bounds'], material, settings, regions=regions), model['volume_mm3'], material.density_kg_m3)
        legacy = apply_usage(homogenize(model['bounds'], material, settings), model['volume_mm3'], material.density_kg_m3)
        folder = temporary/name
        command = [str(executable), '--datadir', str(temporary/'config'), '--load-settings',
            str(temporary/'machine.json')+';'+str(temporary/'process.json'), '--load-filaments', str(temporary/'filament.json'),
            '--slice', '0', '--arrange', '1', '--orient', '0', '--ensure-on-bed', '--outputdir', str(folder),
            '--export-3mf', name+'.3mf', '--export-settings', str(temporary/f'{name}-effective.json'), str(source)]
        with (temporary/f'{name}.log').open('w') as log:
            subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=120)
        gcode_path = folder/'plate_1.gcode'
        gcode = gcode_path.read_text()
        roles = extrusion(gcode)
        length = sum(roles.values())
        volume = length*math.pi*1.75**2/4
        mass = volume*1.24/1000
        stats_length = float(re.search(r'; filament used \[mm\] = ([\d.]+)', gcode)[1])
        # No prime/retract extrusion is counted. Agreement independently checks
        # the role sum against the slicer's total (rounded to 0.01 mm).
        if abs(length-stats_length) > .03:
            raise ValueError(f'Role deposition {length} differs from slicer total {stats_length}.')
        files = {}
        for source_file, suffix in [(source, 'stl'), (gcode_path, 'gcode'), (temporary/f'{name}-effective.json', 'settings.json')]:
            artifact = artifact_dir/f'{name}.{suffix}.gz'
            artifact.write_bytes(gzip.compress(source_file.read_bytes(), mtime=0))
            files[str(artifact)] = {'sha256': sha(artifact), 'uncompressed_sha256': sha(source_file)}
        evidence['cases'].append({'name': name, 'geometry': model['spec'], 'input_triangles': len(triangles),
            'regions': regions, 'openfea_mass_g': current['filament_mass_g'], 'legacy_mass_g': legacy['filament_mass_g'],
            'slicer_mass_g': mass, 'slicer_volume_mm3': volume, 'slicer_deposited_length_mm': length,
            'slicer_total_length_mm': stats_length, 'deposition_by_role_mm': roles,
            'relative_mass_difference': current['filament_mass_g']/mass-1,
            'legacy_relative_mass_difference': legacy['filament_mass_g']/mass-1, 'artifacts': files})
        print(name, json.dumps(evidence['cases'][-1], default=str), flush=True)
    output.write_text(json.dumps(evidence, indent=2)+'\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--executable', type=Path, default=Path('/Applications/OrcaSlicer.app/Contents/MacOS/OrcaSlicer'))
    parser.add_argument('--profiles', type=Path, default=Path('/Applications/OrcaSlicer.app/Contents/Resources/profiles/BBL'))
    parser.add_argument('--output', type=Path, default=Path('evidence/slicer-usage-comparison.json'))
    args = parser.parse_args()
    os.environ.setdefault('FEAR_DATA_DIR', tempfile.mkdtemp(prefix='openfea-slicer-models-'))
    compare(args.executable, args.profiles, args.output)
