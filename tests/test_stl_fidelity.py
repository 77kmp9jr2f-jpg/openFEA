import numpy as np
import pytest

from backend.stl_fidelity import _distance_squared, measure_surface


def test_triangle_distance_includes_interiors_edges_and_vertices():
    t = np.array([[[0, 0, 0], [10, 0, 0], [0, 10, 0]]], float)
    points = np.array([[2, 2, 3], [6, 6, 0], [-1, -1, 0], [3, 0, 0]], float)
    distances = _distance_squared(points, np.broadcast_to(t, (4, 1, 3, 3)))[:, 0]
    assert distances == pytest.approx([9, 2, 2, 0])


def test_same_surface_with_different_tessellation_has_zero_sample_distance():
    from test_stl_topology import subdivide
    coarse = np.array([[[0, 0, 0], [10, 0, 0], [0, 10, 0]]], float)
    measured = measure_surface(subdivide(coarse), coarse)
    assert measured['max_sample_distance_mm'] < 1e-12
    assert measured['source_samples'] == 28
    shifted = measure_surface(coarse, coarse + [0, 0, 2])
    assert shifted['max_sample_distance_mm'] == pytest.approx(2)


def test_volume_alone_cannot_accept_a_surface_change(tmp_path, monkeypatch):
    import fast_simplification
    from test_stl_topology import subdivide
    from backend.stl_io import parse_stl, simplify_triangles, write_box_stl
    path = tmp_path/'box.stl'
    write_box_stl(path, (100, 100, 100))
    coarse = parse_stl(path.read_bytes())
    points, faces = np.unique(coarse.reshape(-1, 3), axis=0, return_inverse=True)
    # Move one corner. Volume changes by only 0.5%, but local surface movement
    # is much greater than the declared 0.01 mm sample-deviation limit.
    points[-1, 0] -= 1.5
    monkeypatch.setattr(fast_simplification, 'simplify', lambda *a, **kw: (points, faces.reshape(-1, 3)))
    monkeypatch.setattr('backend.stl_io.MAX_WORK_TRIANGLES', 100)
    with pytest.raises(ValueError, match='surface'):
        simplify_triangles(subdivide(subdivide(coarse)))


def test_historical_weld_requires_reupload_before_new_meshing(tmp_path):
    from backend.stl_io import store_stl, load_inspection, scaled_stl_path, write_box_stl
    from backend.storage import resource, write_json
    path = tmp_path/'box.stl'
    write_box_stl(path)
    meta = store_stl(path.read_bytes(), path.name)
    meta['preprocessing']['changed'] = True
    write_json(resource('stls', meta['id'])/'inspect.json', meta)
    restored = load_inspection(meta['id'])
    assert restored['preprocessing']['requires_reupload']
    assert 'Re-upload' in restored['warnings'][0]
    with pytest.raises(ValueError, match='Re-upload'):
        scaled_stl_path(meta['id'], 1, accept_preprocessing=True)
