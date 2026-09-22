"""Source topology must survive dense preprocessing and historical reloads."""
import numpy as np
import pytest

from backend.stl_io import (inspect_triangles, parse_stl, scaled_stl_path,
                            store_stl, write_binary_stl, write_box_stl)
from backend.storage import read_json, resource, write_json


def subdivide(tris):
    a, b, c = tris[:, 0], tris[:, 1], tris[:, 2]
    ab, bc, ca = (a+b)/2, (b+c)/2, (c+a)/2
    return np.concatenate([np.stack(x, axis=1) for x in
        [(a, ab, ca), (ab, b, bc), (ca, bc, c), (ab, bc, ca)]])


@pytest.fixture
def box(tmp_path):
    path = tmp_path/'box.stl'
    write_box_stl(path, (100, 100, 100))
    return parse_stl(path.read_bytes())


def test_local_winding_defect_is_rejected_before_volume_use(box, tmp_path):
    box[2] = box[2, [0, 2, 1]]
    path = tmp_path/'flipped.stl'
    write_binary_stl(path, box)
    report = store_stl(path.read_bytes(), path.name)
    assert not report['watertight']
    assert report['inconsistent_winding_edges'] == 3
    with pytest.raises(ValueError, match='winding'):
        scaled_stl_path(report['id'], 1)


def test_uniformly_inverted_shell_can_be_reoriented(box, tmp_path):
    path = tmp_path/'inverted.stl'
    write_binary_stl(path, box[:, [0, 2, 1]])
    report = store_stl(path.read_bytes(), path.name)
    assert report['watertight']
    repaired = inspect_triangles(parse_stl(scaled_stl_path(report['id'], 1).read_bytes()))
    assert repaired['signed_volume_mm3'] == pytest.approx(1_000_000)


@pytest.fixture
def dense_box(box):
    for _ in range(7):
        box = subdivide(box)
    return box


def test_dense_inspection_counts_shells_and_degenerates(dense_box, box):
    tiny_shell = box * .00005 + 200
    report = inspect_triangles(np.concatenate([dense_box, tiny_shell]))
    assert report['shells'] == 2
    assert not report['watertight']
    degenerate = np.repeat(dense_box[0, :1], 3, axis=0)[None]
    report = inspect_triangles(np.concatenate([dense_box, degenerate]))
    assert report['degenerate_triangles'] == 1
    assert not report['watertight']


def test_dense_source_is_validated_before_simplifying(dense_box, box, tmp_path, monkeypatch):
    path = tmp_path/'two-shells.stl'
    write_binary_stl(path, np.concatenate([dense_box, box * .00005 + 200]))
    def forbidden(*args):
        pytest.fail('Invalid source reached destructive simplification')
    monkeypatch.setattr('backend.stl_io.simplify_triangles', forbidden)
    with pytest.raises(ValueError, match='boundary shell'):
        store_stl(path.read_bytes(), path.name)


def test_historical_simplification_cannot_hide_source_shell(box, tmp_path):
    # Simulate an upload made by the old weld path: its working file looks valid,
    # but the original contains an erased component and metadata claims validity.
    path = tmp_path/'working.stl'
    write_binary_stl(path, box)
    report = store_stl(path.read_bytes(), path.name)
    folder = resource('stls', report['id'])
    write_binary_stl(folder/'source.stl', np.concatenate([box, box*.00005+200]))
    meta = read_json(folder/'inspect.json')
    meta['source_triangles'] = 24
    meta['preprocessing']['changed'] = True
    write_json(folder/'inspect.json', meta)
    from backend.stl_io import load_inspection
    restored = load_inspection(report['id'])
    assert not restored['source_inspection']['watertight']
    assert 'Source STL requires repair' in restored['warnings'][0]
    with pytest.raises(ValueError, match='boundary shell'):
        scaled_stl_path(report['id'], 1, accept_preprocessing=True)
