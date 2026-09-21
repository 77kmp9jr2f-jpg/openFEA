"""STL parse, quality checks, and a scaled working copy for meshing."""
from __future__ import annotations
import struct, hashlib
from pathlib import Path
import numpy as np
from .storage import identifier, resource, write_json, read_json

MAX_UPLOAD_BYTES = 80_000_000
MAX_WORK_TRIANGLES = 80_000
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


def weld_triangles(triangles: np.ndarray, tol: float) -> np.ndarray:
    tris = _as_triangles(triangles)
    verts = tris.reshape(-1, 3)
    _, inverse = np.unique(np.round(verts / max(tol, 1e-9)), axis=0, return_inverse=True)
    faces = inverse.reshape(-1, 3)
    keep = (faces[:, 0] != faces[:, 1]) & (faces[:, 1] != faces[:, 2]) & (faces[:, 0] != faces[:, 2])
    welded = np.zeros((int(inverse.max()) + 1, 3), dtype=np.float64)
    np.add.at(welded, inverse, verts)
    welded /= np.maximum(np.bincount(inverse), 1)[:, None]
    return welded[faces[keep]]


def _closed_manifold(triangles: np.ndarray) -> bool:
    verts = np.round(_as_triangles(triangles).reshape(-1, 3), 6)
    _, inverse = np.unique(verts, axis=0, return_inverse=True)
    faces = inverse.reshape(-1, 3)
    edges = np.sort(np.concatenate([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]]), axis=1)
    _, counts = np.unique(edges, axis=0, return_counts=True)
    return bool((counts >= 3).sum() == 0 and (counts == 1).sum() == 0)


def simplify_triangles(triangles: np.ndarray) -> tuple[np.ndarray, str | None]:
    tris = _as_triangles(triangles)
    if len(tris) <= MAX_WORK_TRIANGLES:
        return tris, None
    extent = float(np.ptp(tris.reshape(-1, 3), axis=0).max())
    steps = np.unique(np.round(np.concatenate([
        np.array([1.5]),
        extent * np.linspace(0.0038, 0.0055, 14),
        extent * np.geomspace(0.0025, 0.01, 8),
    ]), 4))
    for step in steps:
        candidate = weld_triangles(tris, float(step))
        if not (2_000 <= len(candidate) <= MAX_WORK_TRIANGLES):
            continue
        if _closed_manifold(candidate):
            return candidate, _simplify_note(len(tris), float(step), len(candidate))
    raise ValueError(
        'This STL is too densely tessellated to simplify into a local mesh. '
        'Export a coarser CAD STL.'
    )


def _simplify_note(source: int, used: float, result: int) -> str:
    return (
        f'CAD export had {source:,} triangles. OpenFEA welded vertices at {used:.3g} source units '
        f'to {result:,} triangles. Review the scaled dimensions and preprocessing '
        'before meshing; small fillets, holes and thin walls may be altered.'
    )


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
    tris = _as_triangles(triangles) * float(unit_scale)
    if len(tris) > MAX_WORK_TRIANGLES:
        return _inspect_fast(tris)
    verts = tris.reshape(-1, 3)
    edges: dict[tuple, list[int]] = {}
    areas = []
    volume = 0.0
    degenerate = 0
    for i, tri in enumerate(tris):
        a, b, c = tri
        cross = np.cross(b - a, c - a)
        area = 0.5 * float(np.linalg.norm(cross))
        if area < 1e-16 or np.unique(np.round(tri, 9), axis=0).shape[0] < 3:
            degenerate += 1
            continue
        areas.append(area)
        volume += float(np.dot(a, cross)) / 6.0
        keys = [tuple(sorted((tuple(np.round(tri[j], 7)), tuple(np.round(tri[k], 7))))) for j, k in ((0, 1), (1, 2), (2, 0))]
        for key in keys:
            edges.setdefault(key, []).append(i)
    counts = np.array([len(v) for v in edges.values()], dtype=int) if edges else np.array([0])
    boundary = int((counts == 1).sum())
    manifold = int((counts == 2).sum())
    nonmanifold = int((counts >= 3).sum())
    parent = list(range(len(tris)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for members in edges.values():
        if len(members) < 2:
            continue
        root = find(members[0])
        for other in members[1:]:
            parent[find(other)] = root
    shells = len({find(i) for i in range(len(tris))}) if len(tris) else 0
    lo, hi = verts.min(axis=0), verts.max(axis=0)
    extent = hi - lo
    watertight = boundary == 0 and nonmanifold == 0 and degenerate == 0 and shells == 1
    suggested = 1.0
    warnings = []
    max_extent = float(extent.max()) if len(verts) else 0
    if max_extent < 2:
        suggested = 1000.0 if max_extent < 0.05 else 25.4
        warnings.append('The extents look like metres or inches. Confirm the unit scale before meshing.')
    elif max_extent > 800:
        warnings.append('The imported extents are large. Confirm the model is in millimetres.')
    if not watertight:
        warnings.append('The triangle mesh is not a single watertight shell. Volume meshing requires a closed manifold.')
    if shells > 1:
        warnings.append(f'The STL has {shells} disconnected shells. This version analyses one connected solid.')
    if degenerate:
        warnings.append(f'{degenerate} degenerate triangles were found.')
    if nonmanifold:
        warnings.append(f'{nonmanifold} non-manifold edges were found.')
    if boundary:
        warnings.append(f'{boundary} boundary edges are open (holes).')
    return {
        'triangles': int(len(tris)),
        'bounds': [lo.tolist(), hi.tolist()],
        'extent_mm': extent.tolist(),
        'surface_area_mm2': float(sum(areas)),
        'signed_volume_mm3': volume,
        'watertight': bool(watertight),
        'shells': int(shells),
        'boundary_edges': boundary,
        'manifold_edges': manifold,
        'nonmanifold_edges': nonmanifold,
        'degenerate_triangles': int(degenerate),
        'suggested_scale': suggested,
        'warnings': warnings,
    }


def _inspect_fast(tris: np.ndarray) -> dict:
    verts = tris.reshape(-1, 3)
    lo, hi = verts.min(axis=0), verts.max(axis=0)
    extent = hi - lo
    a, b, c = tris[:, 0], tris[:, 1], tris[:, 2]
    volume = float(np.einsum('ij,ij->i', a, np.cross(b - a, c - a)).sum() / 6.0)
    rounded = np.round(verts, 6)
    _, inverse = np.unique(rounded, axis=0, return_inverse=True)
    faces = inverse.reshape(-1, 3)
    edges = np.sort(np.concatenate([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]]), axis=1)
    _, counts = np.unique(edges, axis=0, return_counts=True)
    boundary = int((counts == 1).sum())
    nonmanifold = int((counts >= 3).sum())
    watertight = boundary == 0 and nonmanifold == 0
    warnings = []
    max_extent = float(extent.max()) if len(verts) else 0
    suggested = 1.0
    if max_extent < 2:
        suggested = 1000.0 if max_extent < 0.05 else 25.4
        warnings.append('The extents look like metres or inches. Confirm the unit scale before meshing.')
    elif max_extent > 800:
        warnings.append('The imported extents are large. Confirm the model is in millimetres.')
    if not watertight:
        warnings.append('The triangle mesh is not a single watertight shell. Volume meshing requires a closed manifold.')
        if nonmanifold:
            warnings.append(f'{nonmanifold} non-manifold edges were found.')
        if boundary:
            warnings.append(f'{boundary} boundary edges are open (holes).')
    else:
        warnings.append(
            f'CAD export has {len(tris):,} triangles. The mesher will coarsen to the requested mesh size; '
            'this is still the same solid.'
        )
    return {
        'triangles': int(len(tris)),
        'bounds': [lo.tolist(), hi.tolist()],
        'extent_mm': extent.tolist(),
        'surface_area_mm2': float(0.5 * np.linalg.norm(np.cross(b - a, c - a), axis=1).sum()),
        'signed_volume_mm3': volume,
        'watertight': bool(watertight),
        'shells': 1 if watertight else 0,
        'boundary_edges': boundary,
        'manifold_edges': int((counts == 2).sum()),
        'nonmanifold_edges': nonmanifold,
        'degenerate_triangles': 0,
        'suggested_scale': suggested,
        'warnings': warnings,
    }


def store_stl(data: bytes, name: str) -> dict:
    if not data or len(data) > MAX_UPLOAD_BYTES:
        raise ValueError('Upload an STL under 80 MB.')
    triangles = parse_stl(data)
    original = triangles
    source_count = int(len(triangles))
    note = None
    if source_count > MAX_WORK_TRIANGLES:
        triangles, note = simplify_triangles(triangles)
    report = inspect_triangles(triangles, 1.0)
    if note:
        report['warnings'] = [note, *report['warnings']]
    report['source_triangles'] = source_count
    sid = identifier()
    folder = resource('stls', sid)
    folder.mkdir(parents=True, exist_ok=True)
    raw = folder / 'source.stl'
    raw.write_bytes(data)
    if note is None:
        (folder / 'unit.stl').write_bytes(data)
    else:
        write_binary_stl(folder / 'unit.stl', triangles)
    from scipy.spatial import cKDTree
    distance = (float(cKDTree(triangles.reshape(-1, 3)).query(original.reshape(-1, 3))[0].max())
                if note else 0.)
    def volume(tris):
        return float(abs(np.einsum('ij,ij->i', tris[:, 0], np.cross(tris[:, 1], tris[:, 2])).sum() / 6))
    source_volume, working_volume = volume(original), volume(triangles)
    preprocessing = {'changed': bool(note), 'note': note,
        'vertex_distance_bound_source_units': distance,
        'vertex_distance_bound_mm': distance,
        'source_volume_units3': source_volume, 'working_volume_units3': working_volume,
        'relative_volume_change': abs(working_volume - source_volume) / max(source_volume, 1e-18),
        'fidelity_scope': 'Maximum original-vertex distance to a working vertex; not a full surface deviation or feature-preservation certificate.'}
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
    meta = read_json(folder / 'inspect.json')
    preprocessing = dict(meta.get('preprocessing', {}))
    if preprocessing:
        preprocessing['vertex_distance_bound_mm'] = preprocessing['vertex_distance_bound_source_units'] * unit_scale
    note = preprocessing.get('note')
    # Older uploads retained their weld warning only in the initial metadata.
    preserved = [note] if note else [w for w in meta.get('warnings', []) if 'welded' in w]
    return {**meta, **report, 'preprocessing': preprocessing,
            'warnings': [*preserved, *report['warnings']], 'scale': unit_scale}


def scaled_stl_path(stl_id: str, unit_scale: float, accept_preprocessing: bool = False) -> Path:
    folder = resource('stls', stl_id)
    meta = read_json(folder / 'inspect.json')
    changed = meta.get('preprocessing', {}).get('changed') or meta.get('source_triangles', 0) > meta.get('triangles', 0)
    if changed and not accept_preprocessing:
        raise ValueError('This STL was simplified. Explicitly review and accept its scaled preprocessing before meshing, or export a coarser STL.')
    triangles = parse_stl((folder / 'unit.stl').read_bytes()) * float(unit_scale)
    report = inspect_triangles(triangles, 1.0)
    if not report['watertight']:
        raise ValueError('Repair the STL so it is a single watertight shell before meshing. ' + ' '.join(report['warnings']))
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
