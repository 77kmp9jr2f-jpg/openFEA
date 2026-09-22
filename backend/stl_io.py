"""STL parse, quality checks, and a scaled working copy for meshing."""
from __future__ import annotations
import struct, hashlib
from threading import Lock
from pathlib import Path
import numpy as np
from .storage import identifier, resource, write_json, read_json

MAX_UPLOAD_BYTES = 80_000_000
MAX_WORK_TRIANGLES = 80_000
_SIMPLIFIER_LOCK = Lock()
_RECORD = np.dtype([('n', '<f4', 3), ('v', '<f4', 9), ('attr', '<u2')])


def _as_triangles(vertices: np.ndarray) -> np.ndarray:
    pts = np.asarray(vertices, dtype=np.float64).reshape(-1, 3, 3)
    if not len(pts):
        raise ValueError('The STL contains no triangles.')
    if not np.isfinite(pts).all():
        raise ValueError('The STL contains non-finite coordinates.')
    return pts


def parse_stl(data: bytes) -> np.ndarray:
    if len(data) < 15:
        raise ValueError('Upload a binary or ASCII STL file.')
    head = data[:80].decode('latin-1', 'ignore').lstrip()
    if head.lower().startswith('solid') and b'facet' in data[:4000].lower():
        return _parse_ascii(data.decode('latin-1', 'ignore'))
    return _parse_binary(data)


def _parse_binary(data: bytes) -> np.ndarray:
    if len(data) < 84:
        raise ValueError('The binary STL header is truncated.')
    count = struct.unpack_from('<I', data, 80)[0]
    expected = 84 + count * 50
    if count == 0 or expected > len(data) + 1 or count > 2_000_000:
        raise ValueError('The binary STL triangle count is missing or too large (2,000,000 maximum).')
    recs = np.frombuffer(data, dtype=_RECORD, count=count, offset=84)
    return _as_triangles(np.asarray(recs['v'], dtype=np.float64).reshape(-1, 3, 3))


def simplify_triangles(triangles: np.ndarray) -> tuple[np.ndarray, str | None]:
    candidate, note, _ = _simplify_with_measurement(triangles)
    return candidate, note


def _simplify_with_measurement(triangles):
    """Reduce redundant tessellation, rejecting candidates outside our budget.

    The library's 'lossless' mode is only an algorithm choice. Independent
    topology, volume and sampled-distance checks determine acceptance.
    """
    import fast_simplification
    from .stl_fidelity import SURFACE_RELATIVE_LIMIT

    tris = _as_triangles(triangles)
    if len(tris) <= MAX_WORK_TRIANGLES:
        return tris, None, None
    source = inspect_triangles(tris)
    _require_supported(source, 'source STL')
    # Match inspection's coincidence tolerance without spatial grid averaging.
    _, first, inverse = np.unique(np.round(tris.reshape(-1, 3), 7), axis=0,
                                  return_index=True, return_inverse=True)
    surface_budget = float(np.ptp(tris.reshape(-1, 3), axis=0).max()) * SURFACE_RELATIVE_LIMIT
    failures = []
    for mode, options in (('lossless', {'lossless': True}),
                          ('target-count', {'target_count': min(8000, MAX_WORK_TRIANGLES), 'agg': 3}),
                          ('target-count', {'target_count': min(40000, MAX_WORK_TRIANGLES), 'agg': 3})):
        try:
            # Keep the established numerical cleanup for lossless output.
            # Count-targeted output additionally needs true short-edge handling:
            # grid cells alone leave near-coincident endpoints across boundaries.
            coincidence = surface_budget / (100 if mode == 'lossless' else 10)
            # The native wrapper uses shared mutable buffers; copy under lock.
            with _SIMPLIFIER_LOCK:
                points, faces = fast_simplification.simplify(tris.reshape(-1, 3)[first],
                    inverse.reshape(-1, 3), **options)
                candidate = points[faces].astype(np.float32).astype(np.float64)
            candidate = _clean_reduced(candidate, coincidence, grid_cleanup=mode == 'lossless')
            measurement = _check_reduction(tris, source, candidate)
            measurement['reduction_mode'] = mode
            measurement['coincidence_method'] = ('grid-v1' if mode == 'lossless'
                                                  else 'bounded-short-edge-components-v1')
            measurement['coincidence_tolerance_source_units'] = coincidence
            measurement['coincidence_tolerance_mm'] = coincidence
            if mode == 'target-count':
                measurement['target_triangles'] = options['target_count']
            note = (f'CAD export had {len(tris):,} triangles. OpenFEA reduced it to {len(candidate):,} '
                    'triangles with topology, volume and sampled surface checks. Review the scaled dimensions '
                    'and small features before meshing; unsampled surface regions are not certified.')
            return candidate, note, measurement
        except ValueError as exc:
            failures.append(str(exc))
    raise ValueError('No STL reduction passed the acceptance checks. ' + ' '.join(dict.fromkeys(failures))
                     + ' Export a coarser CAD STL.')


def _clean_reduced(candidate, coincidence=None, *, grid_cleanup=False):
    # Validate actual binary-STL precision. Remove only collapsed/zero-area
    # output faces, then independently check the entire remaining boundary.
    # Count-targeted quadric reduction leaves short edges across grid cells.
    # Its cleanup uses mesh edges and bounded component movement. Lossless
    # output retains the finer established grid; both reject face reversals
    # and pass the original independent topology and surface-fidelity gates.
    original_normals = np.cross(candidate[:, 1]-candidate[:, 0], candidate[:, 2]-candidate[:, 0])
    if coincidence and grid_cleanup:
        # Preserve the existing lossless path, including incidence-weighted
        # centers. Its finer grid passed the retained CAD/STEP/STL corpus.
        _, inverse = np.unique(np.round(candidate.reshape(-1, 3) / coincidence),
                               axis=0, return_inverse=True)
        vertices = np.zeros((int(inverse.max())+1, 3))
        np.add.at(vertices, inverse, candidate.reshape(-1, 3))
        vertices /= np.bincount(inverse)[:, None]
        candidate = vertices[inverse.reshape(-1, 3)].astype(np.float32).astype(np.float64)
    elif coincidence:
        from scipy.sparse import coo_matrix
        from scipy.sparse.csgraph import connected_components
        vertices, inverse = np.unique(candidate.reshape(-1, 3), axis=0, return_inverse=True)
        faces = inverse.reshape(-1, 3)
        edges = np.concatenate([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]])
        short = np.linalg.norm(vertices[edges[:, 1]] - vertices[edges[:, 0]], axis=1) <= coincidence
        edges = edges[short]
        count, groups = connected_components(coo_matrix(
            (np.ones(len(edges)), (edges[:, 0], edges[:, 1])),
            shape=(len(vertices), len(vertices))), directed=False)
        centers = np.zeros((count, 3))
        np.add.at(centers, groups, vertices)
        centers /= np.bincount(groups)[:, None]
        merged = centers[groups].astype(np.float32).astype(np.float64)
        # A chain of short edges can span an arbitrarily large distance. Leave
        # the entire component unchanged if any vertex would move too far.
        too_far = np.unique(groups[np.linalg.norm(merged - vertices, axis=1) > coincidence])
        preserve = np.isin(groups, too_far)
        merged[preserve] = vertices[preserve]
        candidate = merged[faces]
    _, ids = np.unique(np.round(candidate.reshape(-1, 3), 7), axis=0, return_inverse=True)
    f = ids.reshape(-1, 3)
    normals = np.cross(candidate[:, 1]-candidate[:, 0], candidate[:, 2]-candidate[:, 0])
    keep = ((f[:, 0] != f[:, 1]) & (f[:, 1] != f[:, 2]) & (f[:, 2] != f[:, 0]) &
            (np.linalg.norm(normals, axis=1) >= 2e-16))
    if np.any(np.einsum('ij,ij->i', normals[keep], original_normals[keep]) <= 0):
        raise ValueError('Short-edge cleanup reversed a retained surface triangle.')
    return candidate[keep]


def _check_reduction(tris, source, candidate):
    from .stl_fidelity import measure_surface, VOLUME_RELATIVE_LIMIT
    if not (4 <= len(candidate) <= MAX_WORK_TRIANGLES):
        raise ValueError('The reduced STL exceeds the local triangle limit or has no usable surface.')
    working = inspect_triangles(candidate)
    _require_supported(working, 'reduced STL')
    if working['euler_characteristic'] != source['euler_characteristic']:
        raise ValueError('STL reduction changed boundary topology.')
    source_volume, working_volume = source['signed_volume_mm3'], working['signed_volume_mm3']
    if source_volume * working_volume <= 0 or abs(working_volume/source_volume-1) > VOLUME_RELATIVE_LIMIT:
        raise ValueError('STL reduction exceeded the 1% volume-change limit.')
    measurement = measure_surface(tris, candidate)
    if measurement['max_sample_distance_source_units'] > measurement['limit_source_units']:
        raise ValueError('STL reduction exceeded the sampled surface-deviation limit (0.01% of the longest dimension).')
    return measurement


def _parse_ascii(text: str) -> np.ndarray:
    verts: list[float] = []
    for line in text.splitlines():
        parts = line.strip().split()
        if len(parts) >= 4 and parts[0].lower() == 'vertex':
            try:
                verts.extend(float(p) for p in parts[1:4])
            except ValueError as exc:
                raise ValueError('The ASCII STL has an invalid vertex.') from exc
    if len(verts) % 9:
        raise ValueError('The ASCII STL is missing vertices.')
    return _as_triangles(np.array(verts, dtype=np.float64))


def write_binary_stl(path: Path, triangles: np.ndarray) -> None:
    tris = _as_triangles(triangles)
    header = bytearray(b'OpenFEA scaled STL'.ljust(80, b' '))
    normals = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
    length = np.linalg.norm(normals, axis=1, keepdims=True)
    normals = np.divide(normals, length, out=np.zeros_like(normals), where=length > 0)
    records = np.zeros(len(tris), dtype=_RECORD)
    records['n'] = normals
    records['v'] = tris.reshape(-1, 9)
    path.write_bytes(bytes(header) + struct.pack('<I', len(tris)) + records.tobytes())


def inspect_triangles(triangles: np.ndarray, unit_scale: float = 1.0) -> dict:
    """Use identical topology checks for small and dense inputs.

    Coincidence uses seven decimal places in the scaled coordinates. This checks
    edge incidence, connected boundary shells, degeneracy and winding, not
    geometric self-intersections or shell containment.
    """
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components

    tris = _as_triangles(triangles) * float(unit_scale)
    verts = tris.reshape(-1, 3)
    points, inverse = np.unique(np.round(verts, 7), axis=0, return_inverse=True)
    faces = inverse.reshape(-1, 3)
    crosses = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
    areas = np.linalg.norm(crosses, axis=1) / 2
    valid = ((areas >= 1e-16) & (faces[:, 0] != faces[:, 1]) &
             (faces[:, 1] != faces[:, 2]) & (faces[:, 2] != faces[:, 0]))
    degenerate = int((~valid).sum())
    good = faces[valid]
    directed = np.concatenate([good[:, [0, 1]], good[:, [1, 2]], good[:, [2, 0]]])
    edges, groups, counts = np.unique(np.sort(directed, axis=1), axis=0,
                                     return_inverse=True, return_counts=True)
    boundary = int((counts == 1).sum())
    manifold = int((counts == 2).sum())
    nonmanifold = int((counts >= 3).sum())
    directions = np.where(directed[:, 0] < directed[:, 1], 1, -1)
    winding = int(((counts == 2) & (np.bincount(groups, weights=directions,
                                              minlength=len(edges)) != 0)).sum())
    # Connect incident faces, including all faces around a non-manifold edge.
    # Sparse connected-components avoids a Python loop over millions of edges.
    order = np.argsort(groups, kind='stable')
    same = groups[order[1:]] == groups[order[:-1]]
    owners = np.tile(np.flatnonzero(valid), 3)[order]
    adjacency = coo_matrix((np.ones(int(same.sum()), dtype=np.int8),
        (owners[:-1][same], owners[1:][same])), shape=(len(tris), len(tris)))
    shells = int(connected_components(adjacency, directed=False, return_labels=False))
    lo, hi = verts.min(axis=0), verts.max(axis=0)
    extent = hi - lo
    watertight = boundary == 0 and nonmanifold == 0 and degenerate == 0 and shells == 1 and winding == 0
    # Translation before the volume sum reduces cancellation for offset parts.
    shifted = tris - lo
    volume = float(np.einsum('ij,ij->i', shifted[:, 0], crosses).sum() / 6)
    suggested = 1.0
    warnings = []
    max_extent = float(extent.max())
    if max_extent < 2:
        suggested = 1000.0 if max_extent < 0.05 else 25.4
        warnings.append('The extents look like metres or inches. Confirm the unit scale before meshing.')
    elif max_extent > 800:
        warnings.append('The imported extents are large. Confirm the model is in millimetres.')
    if not watertight:
        warnings.append('The STL must have one closed boundary shell with consistent triangle winding before meshing.')
    if shells > 1:
        warnings.append(f'The STL has {shells} boundary shells. Separate components and enclosed cavities are not supported.')
    if degenerate:
        warnings.append(f'{degenerate} degenerate triangles were found.')
    if nonmanifold:
        warnings.append(f'{nonmanifold} non-manifold edges were found.')
    if boundary:
        warnings.append(f'{boundary} boundary edges are open (holes).')
    if winding:
        warnings.append(f'{winding} shared edges have inconsistent triangle winding; repair the STL orientation.')
    return {
        'triangles': int(len(tris)),
        'bounds': [lo.tolist(), hi.tolist()],
        'extent_mm': extent.tolist(),
        'surface_area_mm2': float(areas[valid].sum()),
        'signed_volume_mm3': volume,
        'watertight': bool(watertight),
        'shells': shells,
        'boundary_edges': boundary,
        'manifold_edges': manifold,
        'nonmanifold_edges': nonmanifold,
        'inconsistent_winding_edges': winding,
        'degenerate_triangles': degenerate,
        'euler_characteristic': int(len(points) - len(edges) + len(tris)),
        'suggested_scale': suggested,
        'warnings': warnings,
    }


def _require_supported(report: dict, label: str = 'STL') -> None:
    if not report['watertight']:
        raise ValueError(f'Repair the {label} so it is a single watertight boundary shell before meshing. '
                         + ' '.join(report['warnings']))


def _preprocessing(original, triangles, note, surface_measurement=None):
    from scipy.spatial import cKDTree
    distance = (float(cKDTree(triangles.reshape(-1, 3)).query(original.reshape(-1, 3))[0].max())
                if note else 0.)
    def volume(tris):
        shifted = tris - tris.reshape(-1, 3).min(axis=0)
        return float(abs(np.einsum('ij,ij->i', shifted[:, 0], np.cross(shifted[:, 1], shifted[:, 2])).sum() / 6))
    source_volume, working_volume = volume(original), volume(triangles)
    meta = {'changed': bool(note), 'note': note,
        'vertex_distance_bound_source_units': distance,
        'vertex_distance_bound_mm': distance,
        'source_volume_units3': source_volume, 'working_volume_units3': working_volume,
        'relative_volume_change': abs(working_volume - source_volume) / max(source_volume, 1e-18),
        'fidelity_scope': 'Maximum original-vertex distance to a working vertex; not a full surface deviation or feature-preservation certificate.'}
    if surface_measurement is not None:
        from .stl_fidelity import VOLUME_RELATIVE_LIMIT
        meta.update(method='quadric-v1', surface_samples=surface_measurement,
                    relative_volume_limit=VOLUME_RELATIVE_LIMIT,
                    fidelity_scope=surface_measurement['scope'])
    return meta


def store_stl(data: bytes, name: str) -> dict:
    if not data or len(data) > MAX_UPLOAD_BYTES:
        raise ValueError('Upload an STL under 80 MB.')
    triangles = parse_stl(data)
    original = triangles
    source_count = int(len(triangles))
    note, surface_measurement = None, None
    source_report = inspect_triangles(original)
    if source_count > MAX_WORK_TRIANGLES:
        _require_supported(source_report, 'source STL')
        triangles, note, surface_measurement = _simplify_with_measurement(triangles)
    report = inspect_triangles(triangles, 1.0)
    if note:
        report['warnings'] = [note, *report['warnings']]
    report['source_triangles'] = source_count
    report['source_inspection'] = source_report
    sid = identifier()
    folder = resource('stls', sid)
    folder.mkdir(parents=True, exist_ok=True)
    raw = folder / 'source.stl'
    raw.write_bytes(data)
    if note is None:
        (folder / 'unit.stl').write_bytes(data)
    else:
        write_binary_stl(folder / 'unit.stl', triangles)
    preprocessing = _preprocessing(original, triangles, note, surface_measurement)
    meta = {'id': sid, 'name': name, 'bytes': len(data), **report,
            'source_sha256': hashlib.sha256(data).hexdigest(),
            'working_sha256': hashlib.sha256((folder / 'unit.stl').read_bytes()).hexdigest(),
            'preprocessing': preprocessing}
    write_json(folder / 'inspect.json', meta)
    return meta


def load_inspection(stl_id: str, unit_scale: float = 1.0) -> dict:
    folder = resource('stls', stl_id)
    triangles = parse_stl((folder / 'unit.stl').read_bytes())
    report = inspect_triangles(triangles, unit_scale)
    source_report = inspect_triangles(parse_stl((folder / 'source.stl').read_bytes()), unit_scale)
    meta = read_json(folder / 'inspect.json')
    preprocessing = dict(meta.get('preprocessing', {}))
    if not preprocessing and meta.get('source_triangles', 0) > meta.get('triangles', 0):
        note = next((w for w in meta.get('warnings', []) if 'welded' in w), 'The original STL was simplified; inspect its small features before use.')
        preprocessing = _preprocessing(parse_stl((folder/'source.stl').read_bytes()), triangles, note)
    if preprocessing:
        preprocessing['vertex_distance_bound_mm'] = preprocessing['vertex_distance_bound_source_units'] * unit_scale
        if preprocessing.get('surface_samples'):
            samples = dict(preprocessing['surface_samples'])
            samples['max_sample_distance_mm'] = samples['max_sample_distance_source_units'] * unit_scale
            samples['limit_mm'] = samples['limit_source_units'] * unit_scale
            if 'coincidence_tolerance_source_units' in samples:
                samples['coincidence_tolerance_mm'] = samples['coincidence_tolerance_source_units'] * unit_scale
            preprocessing['surface_samples'] = samples
    historical = preprocessing.get('changed') and not preprocessing.get('surface_samples')
    preprocessing['requires_reupload'] = bool(historical)
    note = preprocessing.get('note')
    # Older uploads retained their weld warning only in the initial metadata.
    preserved = [note] if note else [w for w in meta.get('warnings', []) if 'welded' in w]
    source_warnings = ([] if source_report['watertight'] else
                       ['Source STL requires repair: ' + ' '.join(source_report['warnings'])])
    if historical:
        source_warnings.append('This historical STL used earlier simplification. Re-upload the original STL for current fidelity checks before building a new mesh. Existing models and results remain available.')
    return {**meta, **report, 'source_inspection': source_report, 'preprocessing': preprocessing,
            'warnings': [*source_warnings, *preserved, *report['warnings']], 'scale': unit_scale}


def scaled_stl_path(stl_id: str, unit_scale: float, accept_preprocessing: bool = False) -> Path:
    folder = resource('stls', stl_id)
    meta = read_json(folder / 'inspect.json')
    # Recheck original bytes, including uploads made before source validation.
    _require_supported(inspect_triangles(parse_stl((folder / 'source.stl').read_bytes()) * float(unit_scale)), 'source STL')
    changed = meta.get('preprocessing', {}).get('changed') or meta.get('source_triangles', 0) > meta.get('triangles', 0)
    if changed and not meta.get('preprocessing', {}).get('surface_samples'):
        raise ValueError('Re-upload the original STL for current surface-fidelity checks before building a new mesh. This historical upload used earlier simplification; existing models and results remain available.')
    if changed and not accept_preprocessing:
        raise ValueError('This STL was simplified. Explicitly review and accept its scaled preprocessing before meshing, or export a coarser STL.')
    triangles = parse_stl((folder / 'unit.stl').read_bytes()) * float(unit_scale)
    report = inspect_triangles(triangles, 1.0)
    _require_supported(report)
    if abs(report['signed_volume_mm3']) < 1e-6:
        raise ValueError('The STL has zero enclosed volume after scaling.')
    dest = folder / f'scaled-{unit_scale:g}.stl'
    if unit_scale == 1 and report['signed_volume_mm3'] > 0:
        dest.write_bytes((folder / 'unit.stl').read_bytes())
        return dest
    if report['signed_volume_mm3'] < 0:
        triangles = triangles[:, [0, 2, 1], :]
    write_binary_stl(dest, triangles)
    return dest


def _name(folder: Path) -> str:
    inspect = folder / 'inspect.json'
    if inspect.exists():
        from .storage import read_json
        return read_json(inspect).get('name', 'Imported STL')
    return 'Imported STL'


def write_box_stl(path: Path, size=(40.0, 10.0, 8.0)) -> None:
    lx, ly, lz = size
    corners = np.array([[0, 0, 0], [lx, 0, 0], [lx, ly, 0], [0, ly, 0],
                        [0, 0, lz], [lx, 0, lz], [lx, ly, lz], [0, ly, lz]], dtype=np.float64)
    faces = ((0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7))
    tris = []
    for a, b, c, d in faces:
        tris.append(corners[[a, b, c]])
        tris.append(corners[[a, c, d]])
    write_binary_stl(path, np.stack(tris))
