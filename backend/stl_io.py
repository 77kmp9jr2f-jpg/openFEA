"""STL parse, quality checks, and a scaled working copy for meshing."""
from __future__ import annotations
import struct
from pathlib import Path
import numpy as np
from .storage import identifier, resource, write_json


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
    tris = []
    for i in range(count):
        off = 84 + i * 50
        vals = struct.unpack_from('<' + 'f' * 12, data, off)
        tris.append(vals[3:12])
    return _as_triangles(np.array(tris, dtype=np.float64))


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
    path.write_bytes(b'OpenFEA scaled STL'.ljust(80, b' ') + struct.pack('<I', len(tris)))
    with path.open('ab') as handle:
        for tri in tris:
            n = np.cross(tri[1] - tri[0], tri[2] - tri[0])
            norm = np.linalg.norm(n)
            n = n / norm if norm > 0 else np.zeros(3)
            handle.write(struct.pack('<' + 'f' * 12, *n, *tri.ravel()))
            handle.write(b'\x00\x00')


def inspect_triangles(triangles: np.ndarray, unit_scale: float = 1.0) -> dict:
    tris = _as_triangles(triangles) * float(unit_scale)
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


def store_stl(data: bytes, name: str) -> dict:
    triangles = parse_stl(data)
    report = inspect_triangles(triangles, 1.0)
    sid = identifier()
    folder = resource('stls', sid)
    folder.mkdir(parents=True, exist_ok=True)
    raw = folder / 'source.stl'
    raw.write_bytes(data)
    write_binary_stl(folder / 'unit.stl', triangles)
    meta = {'id': sid, 'name': name, 'bytes': len(data), **report}
    write_json(folder / 'inspect.json', meta)
    return meta


def load_inspection(stl_id: str, unit_scale: float = 1.0) -> dict:
    folder = resource('stls', stl_id)
    triangles = parse_stl((folder / 'unit.stl').read_bytes())
    report = inspect_triangles(triangles, unit_scale)
    return {**report, 'id': stl_id, 'name': _name(folder), 'scale': unit_scale}


def scaled_stl_path(stl_id: str, unit_scale: float) -> Path:
    folder = resource('stls', stl_id)
    triangles = parse_stl((folder / 'unit.stl').read_bytes()) * float(unit_scale)
    report = inspect_triangles(triangles, 1.0)
    if not report['watertight']:
        raise ValueError('Repair the STL so it is a single watertight shell before meshing. ' + ' '.join(report['warnings']))
    if abs(report['signed_volume_mm3']) < 1e-6:
        raise ValueError('The STL has zero enclosed volume after scaling.')
    if report['signed_volume_mm3'] < 0:
        triangles = triangles[:, [0, 2, 1], :]
    dest = folder / f'scaled-{unit_scale:g}.stl'
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
