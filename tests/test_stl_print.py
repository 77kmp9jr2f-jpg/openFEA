"""STL quality gates and print homogenization — not printed-coupon calibration."""
from pathlib import Path
import numpy as np
import pytest
from backend.schemas import Geometry, Analysis, Material, PrintSettings
from backend.stl_io import parse_stl, inspect_triangles, store_stl, write_box_stl, write_binary_stl
from backend.print_model import homogenize, stiffness
from backend.storage import DATA

PLA = Material(name='PLA · illustrative filament', young_mpa=3500, poisson=0.35, yield_mpa=40, density_kg_m3=1240)


def _open_square():
    corners = np.array([[0, 0, 0], [10, 0, 0], [10, 10, 0], [0, 10, 0]], float)
    return np.stack([corners[[0, 1, 2]], corners[[0, 2, 3]]])


def test_stl_inspect_flags_open_and_closed_meshes(tmp_path):
    closed = tmp_path / 'box.stl'
    write_box_stl(closed, (40, 10, 8))
    ok = inspect_triangles(parse_stl(closed.read_bytes()))
    assert ok['watertight'] and ok['shells'] == 1
    assert ok['extent_mm'] == pytest.approx([40, 10, 8])
    assert ok['signed_volume_mm3'] == pytest.approx(3200, rel=1e-8)
    bad = inspect_triangles(_open_square())
    assert not bad['watertight']
    assert bad['boundary_edges'] == 4


def test_stl_store_rejects_non_stl_and_accepts_box():
    path = DATA / 'stls'
    path.mkdir(parents=True, exist_ok=True)
    dest = Path('/tmp/fea-r-box.stl')
    write_box_stl(dest)
    meta = store_stl(dest.read_bytes(), 'coupon.stl')
    assert meta['watertight']
    assert meta['triangles'] == 12
    with pytest.raises(ValueError, match='STL'):
        store_stl(b'<html>nope</html>', 'fake.stl')


def test_open_stl_cannot_be_meshed():
    from backend.stl_io import scaled_stl_path
    dest = Path('/tmp/fea-r-open.stl')
    write_binary_stl(dest, _open_square())
    meta = store_stl(dest.read_bytes(), 'open.stl')
    with pytest.raises(ValueError, match='watertight'):
        scaled_stl_path(meta['id'], 1.0)


def test_print_homogenization_changes_stiffness_and_mass():
    bounds = [[0, 0, 0], [40, 10, 8]]
    solid = homogenize(bounds, PLA, PrintSettings(enabled=True, infill_density=1, infill_pattern='gyroid'))
    sparse = homogenize(bounds, PLA, PrintSettings(enabled=True, infill_density=0.2, infill_pattern='gyroid',
                                                   wall_count=2, line_width_mm=0.4, top_layers=3, bottom_layers=3,
                                                   layer_height_mm=0.2))
    assert solid['eta_xy'] == pytest.approx(1)
    assert solid['volume_fraction'] == pytest.approx(1)
    assert sparse['volume_fraction'] < 0.6
    assert sparse['young_z_mpa'] < sparse['young_xy_mpa'] < PLA.young_mpa
    assert 'not coupon-calibrated' in ' '.join(sparse['assumptions'])


def test_print_settings_rotate_the_soft_axis():
    bounds = [[0, 0, 0], [20, 20, 20]]
    settings = PrintSettings(enabled=True, infill_density=0.2, infill_pattern='rectilinear')
    C0, _ = stiffness(PLA, settings, bounds)
    C90, _ = stiffness(PLA, settings.model_copy(update={'rotation_deg': (0, 90, 0)}), bounds)
    # Without rotation, layer (3,3) is softer than in-plane (1,1).
    assert C0[2, 2] < C0[0, 0]
    # 90 deg about Y sends print-Z toward global X.
    assert C90[0, 0] < C90[2, 2]


def test_stl_import_builds_selectable_faces_and_print_solve(tmp_path):
    from backend.geometry import build_model
    from backend.solver import solve_model
    dest = tmp_path / 'bar.stl'
    write_box_stl(dest, (40, 10, 8))
    meta = store_stl(dest.read_bytes(), 'print-bar.stl')
    model = build_model(Geometry(name='Print bar', kind='stl', stl_id=meta['id'], mesh_size=5,
                                 provenance='stl_import', unit_scale=1, hole_diameter=0))
    assert model['volume_mm3'] == pytest.approx(3200, rel=0.08)
    assert len(model['faces']) >= 2
    solid = solve_model(Analysis(
        model_id=model['id'], confirmed=True,
        fixed_faces=[model['recommended']['fixed_face']],
        loads=[{'face_id': model['recommended']['load_face'], 'vector': [0, 0, -40]}],
        material=PLA, print=PrintSettings(enabled=True, infill_density=1)))
    sparse = solve_model(Analysis(
        model_id=model['id'], confirmed=True,
        fixed_faces=[model['recommended']['fixed_face']],
        loads=[{'face_id': model['recommended']['load_face'], 'vector': [0, 0, -40]}],
        material=PLA, print=PrintSettings(enabled=True, infill_density=0.2, infill_pattern='gyroid')))
    assert sparse['max_displacement_mm'] > solid['max_displacement_mm'] * 1.15
    assert sparse['mass_g'] < solid['mass_g'] * 0.7
    assert sparse['print']['enabled']
    assert sparse['relative_residual'] < 1e-7


def test_compare_endpoint_reports_print_deltas(tmp_path):
    from backend.geometry import build_model
    from backend.solver import solve_model
    from backend.print_model import compare_results
    dest = tmp_path / 'bar.stl'
    write_box_stl(dest, (40, 10, 8))
    meta = store_stl(dest.read_bytes(), 'compare-bar.stl')
    model = build_model(Geometry(name='Compare bar', kind='stl', stl_id=meta['id'], mesh_size=6,
                                 provenance='stl_import', hole_diameter=0))
    common = dict(model_id=model['id'], confirmed=True,
                  fixed_faces=[model['recommended']['fixed_face']],
                  loads=[{'face_id': model['recommended']['load_face'], 'vector': [0, 0, -40]}],
                  material=PLA)
    a = solve_model(Analysis(**common, print=PrintSettings(enabled=True, infill_density=0.4, wall_count=3)))
    b = solve_model(Analysis(**common, print=PrintSettings(enabled=True, infill_density=0.15, wall_count=2)))
    compared = compare_results(a, b)
    assert compared['same_model']
    assert compared['delta']['max_displacement_mm'] > 0
    assert compared['delta']['mass_g'] < 0
