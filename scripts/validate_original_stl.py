"""Measure a supplied original STL without changing any stored study.

Run: python -m scripts.validate_original_stl SOURCE [--probe-alternatives]
Exit 0 means the production importer accepted the file; exit 1 means it rejected
it. Experimental probes are diagnostic only and never affect that verdict.
The source file is not copied into the evidence report or repository.
"""
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import tempfile
import time
from datetime import datetime, timezone

import numpy as np


def write_record(output, record):
    def native(value):
        if isinstance(value, np.generic):
            return value.item()
        raise TypeError(f'Unsupported evidence value: {type(value).__name__}')
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(record, indent=2, default=native) + '\n')


def validate(source_path, output, probe_alternatives=False):
    if (source_path.resolve() == output.resolve()
            or (output.exists() and source_path.samefile(output))):
        raise ValueError('The evidence output must not overwrite the source STL.')
    from backend.stl_io import (MAX_WORK_TRIANGLES, _check_reduction, _clean_reduced,
                               inspect_triangles, parse_stl, store_stl)
    from backend.stl_fidelity import SURFACE_RELATIVE_LIMIT, measure_surface

    raw = source_path.read_bytes()
    source_hash = hashlib.sha256(raw).hexdigest()
    record = {
        'created_at': datetime.now(timezone.utc).isoformat(),
        'scope': 'Original supplied tessellation, without artificial subdivision. '
                 'Checks compare reduced surfaces to the input facets, not to CAD or physical ground truth. '
                 'No meshing, stress convergence, self-intersection certification or FEA acceptance is claimed.',
        'source_name': source_path.name,
        'source_bytes': len(raw),
        'source_sha256': source_hash,
        'source_inspection': None,
        'working_triangle_limit': MAX_WORK_TRIANGLES,
        'surface_relative_limit': SURFACE_RELATIVE_LIMIT,
        'fast_simplification_version': importlib.metadata.version('fast-simplification'),
        'source_hashes': {name: hashlib.sha256(Path(name).read_bytes()).hexdigest()
                          for name in ('backend/stl_io.py', 'backend/stl_fidelity.py',
                                       'scripts/validate_original_stl.py', 'requirements.txt')},
        'experimental_probes': [],
    }
    start = time.monotonic()
    try:
        inspection = store_stl(raw, source_path.name)
        record['production_import'] = {'accepted': True, 'inspection': inspection}
    except ValueError as exc:
        record['production_import'] = {'accepted': False, 'error': str(exc)}
    record['production_import']['seconds'] = time.monotonic() - start
    write_record(output, record)
    print('Production import:', 'accepted' if record['production_import']['accepted'] else 'rejected', flush=True)

    try:
        triangles = parse_stl(raw)
        source = inspect_triangles(triangles)
        record['source_inspection'] = source
    except ValueError as exc:
        source = None
        record['source_inspection_error'] = str(exc)
    write_record(output, record)

    if probe_alternatives and source and source['watertight'] and len(triangles) > MAX_WORK_TRIANGLES:
        import fast_simplification
        _, first, inverse = np.unique(np.round(triangles.reshape(-1, 3), 7), axis=0,
                                      return_index=True, return_inverse=True)
        points = triangles.reshape(-1, 3)[first]
        faces = inverse.reshape(-1, 3)
        origin = (points.min(axis=0) + points.max(axis=0)) / 2
        extent = float(np.ptp(points, axis=0).max())
        # Fixed diagnostic hypotheses, not a search until something passes.
        # Higher aggression can reach the requested count; normalization tests
        # the native algorithm's absolute quadric-error thresholds. Acceptance
        # remains in the original units, with the production cleanup and gates.
        for name, agg, normalized in [('native-80k-agg5', 5, False),
                                      ('native-80k-agg7', 7, False),
                                      ('normalized-80k-agg3', 3, True)]:
            start = time.monotonic()
            row = {'name': name, 'adopted': False,
                   'options': {'target_count': MAX_WORK_TRIANGLES, 'agg': agg},
                   'normalization': {'origin': origin.tolist(), 'scale': extent} if normalized else None}
            record['experimental_probes'].append(row)
            try:
                p, f = fast_simplification.simplify((points-origin)/extent if normalized else points,
                                                   faces, **row['options'])
                candidate = ((p[f]*extent + origin) if normalized else p[f]).astype(np.float32).astype(np.float64)
                row['raw_triangles'] = len(candidate)
                candidate = _clean_reduced(candidate, extent*SURFACE_RELATIVE_LIMIT/10)
                row['clean_triangles'] = len(candidate)
                row['inspection'] = inspect_triangles(candidate)
                if 4 <= len(candidate) <= MAX_WORK_TRIANGLES:
                    row['surface_measurement'] = measure_surface(triangles, candidate)
                _check_reduction(triangles, source, candidate)
                row['accepted_by_geometry_gates'] = True
            except ValueError as exc:
                row.update(accepted_by_geometry_gates=False, error=str(exc))
            row['seconds'] = time.monotonic() - start
            write_record(output, record)
            print(name, 'accepted' if row['accepted_by_geometry_gates'] else 'rejected', flush=True)

    record['source_unchanged'] = hashlib.sha256(source_path.read_bytes()).hexdigest() == source_hash
    write_record(output, record)
    return record['production_import']['accepted'] and record['source_unchanged']


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('--output', type=Path, default=Path('evidence/original-stl-validation.json'))
    parser.add_argument('--probe-alternatives', action='store_true')
    args = parser.parse_args()
    # Always isolate validation artifacts, even when a user's FEAR_DATA_DIR is set.
    with tempfile.TemporaryDirectory(prefix='openfea-original-validation-') as folder:
        os.environ['FEAR_DATA_DIR'] = folder
        try:
            accepted = validate(args.source, args.output, args.probe_alternatives)
        except ValueError as exc:
            parser.error(str(exc))
    raise SystemExit(0 if accepted else 1)
