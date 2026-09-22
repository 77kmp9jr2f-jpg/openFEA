"""Short-edge cleanup must not depend on spatial-grid placement."""
import numpy as np
import pytest

from backend.stl_io import _clean_reduced, inspect_triangles, parse_stl, write_box_stl


def test_short_edge_across_grid_boundary_is_removed_without_opening_shell(tmp_path):
    path = tmp_path/'box.stl'
    write_box_stl(path, (10, 10, 10))
    triangles = parse_stl(path.read_bytes()) + .0004
    a = np.full(3, .0004)
    b, near = a + [10, 0, 0], a + [.0002, 0, 0]
    split = []
    for face in triangles:
        edge = [i for i in range(3) if np.array_equal(face[i], a) or np.array_equal(face[i], b)]
        if len(edge) != 2:
            split.append(face)
            continue
        for i in range(3):
            j, k = (i+1) % 3, (i+2) % 3
            if i in edge and j in edge:
                split.extend([[face[i], near, face[k]], [near, face[j], face[k]]])
                break
    split = np.asarray(split)
    assert len(split) == 14 and inspect_triangles(split)['watertight']
    clean = _clean_reduced(split, .001)
    assert len(clean) == 12
    report = inspect_triangles(clean)
    assert report['watertight'] and report['euler_characteristic'] == 2
    assert report['signed_volume_mm3'] == pytest.approx(1000, rel=1e-4)


def test_short_edge_chain_cannot_move_vertices_beyond_cleanup_distance():
    # Each base edge is short, but collapsing the entire chain would move its
    # endpoints more than the permitted distance. Keep this component intact.
    vertices = np.array([[x*.8, 0, 0] for x in range(6)] + [[2, 10, 0]], float)
    triangles = vertices[np.array([[i, i+1, 6] for i in range(5)])]
    clean = _clean_reduced(triangles, 1.)
    np.testing.assert_allclose(clean, triangles, atol=2e-7, rtol=0)


def test_close_vertices_on_unconnected_edges_are_not_welded():
    triangles = np.array([[[0, 0, 0], [10, 0, 0], [0, 10, 0]],
                          [[0, 0, .1], [10, 0, .1], [0, 10, .1]]], float)
    np.testing.assert_allclose(_clean_reduced(triangles, 1.), triangles, atol=1e-8, rtol=0)


@pytest.mark.parametrize('grid_cleanup', [False, True])
def test_cleanup_cannot_reverse_a_retained_cap_triangle(grid_cleanup):
    p = np.array([0., 0., 5.])
    extent = 100 if grid_cleanup else 10
    ring = np.array([[2, .00002, 5], [1, .00002, 5],
                     [0, .00008 if grid_cleanup else .00016, 5],
                     [-extent, extent, 5], [-extent, -extent, 5], [extent, -extent, 5]], float)
    faces = []
    for i, a in enumerate(ring):
        b = ring[(i+1) % len(ring)]
        faces.extend([[p, a, b], [p-[0, 0, 5], b-[0, 0, 5], a-[0, 0, 5]],
                      [a, a-[0, 0, 5], b-[0, 0, 5]], [a, b-[0, 0, 5], b]])
    source = np.asarray(faces).astype(np.float32).astype(float)
    assert inspect_triangles(source)['watertight']
    # Euler/edge incidence, volume and surface-distance gates alone accepted
    # this fold. Movement is within radius but crosses a retained triangle.
    with pytest.raises(ValueError, match='reversed'):
        _clean_reduced(source, .0002, grid_cleanup=grid_cleanup)
