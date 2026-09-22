"""Independent geometric controls for perimeter/core accounting (not bead physics)."""
import numpy as np
import pytest

from backend.schemas import Geometry, Feature, PrintSettings
from backend.stl_io import write_box_stl, parse_stl


def box_triangles(tmp_path):
    path = tmp_path/'box.stl'
    write_box_stl(path, (40, 10, 8))
    return parse_stl(path.read_bytes())


def model_triangles(model):
    return np.asarray(model['nodes'])[np.asarray([t for f in model['faces'] for t in f['triangles']])]


def test_layer_contours_match_independent_box_shell_volume(tmp_path):
    from backend.print_geometry import measure_regions
    regions = measure_regions(box_triangles(tmp_path), PrintSettings(enabled=True))
    core = (40-2*1.2)*(10-2*1.2)*(8-1.6)
    assert regions['sampled_solid_volume_mm3'] == pytest.approx(3200, rel=1e-8)
    assert regions['core_volume_mm3'] == pytest.approx(core, rel=1e-8)
    assert regions['shell_volume_fraction'] == pytest.approx(1-core/3200, rel=1e-8)


def test_channel_uprights_have_no_infill_space():
    from backend.geometry import build_model
    from backend.print_geometry import measure_regions
    model = build_model(Geometry(kind='custom', mesh_size=6,
        features=[Feature(size=(60,24,16)), Feature(operation='cut', origin=(-1,2,2), size=(62,20,15))]))
    regions = measure_regions(model_triangles(model), PrintSettings(enabled=True))
    # 2 mm uprights are filled by overlapping 1.2 mm perimeters. Only the
    # middle 0.4 mm of the floor retains core, plus two 0.8 mm strips below
    # the uprights where there is no exposed upper floor skin.
    core = (60-2*1.2)*((24-2*1.2)*.4 + 2*.8*.8)
    assert regions['sampled_solid_volume_mm3'] == pytest.approx(6240, rel=1e-7)
    assert regions['core_volume_mm3'] == pytest.approx(core, rel=1e-6)
    assert regions['shell_volume_fraction'] > .9


def test_nested_tube_contours_preserve_hole_and_fill_thin_wall():
    from backend.geometry import build_model
    from backend.print_geometry import measure_regions
    model = build_model(Geometry(kind='custom', mesh_size=3,
        features=[Feature(primitive='cylinder', axis=(0,0,20), radius=10),
                  Feature(operation='cut', primitive='cylinder', origin=(0,0,-1), axis=(0,0,22), radius=8)]))
    regions = measure_regions(model_triangles(model), PrintSettings(enabled=True))
    assert regions['sampled_solid_volume_mm3'] == pytest.approx(20*np.pi*(10**2-8**2), rel=.02)
    assert regions['core_volume_mm3'] < 1e-8
    assert regions['shell_volume_fraction'] == pytest.approx(1)


def test_geometry_and_print_frame_rotate_together(tmp_path):
    from backend.print_geometry import measure_regions
    from backend.print_model import rotation_matrix
    triangles = box_triangles(tmp_path)
    angles = (30,45,20)
    moved = triangles @ rotation_matrix(angles).T + [100,-200,75]
    regions = measure_regions(moved, PrintSettings(enabled=True, rotation_deg=angles))
    reference = measure_regions(triangles, PrintSettings(enabled=True))
    assert regions['core_volume_mm3'] == pytest.approx(reference['core_volume_mm3'], rel=1e-6)
    assert regions['sampled_solid_volume_mm3'] == pytest.approx(3200, rel=1e-6)


def test_open_contours_are_rejected_instead_of_falling_back_to_a_box(tmp_path):
    from backend.print_geometry import measure_regions
    triangles = box_triangles(tmp_path)
    # Remove a vertical wall, leaving open contours at every interior layer.
    triangles = triangles[~np.all(np.isclose(triangles[:,:,0], 0), axis=1)]
    with pytest.raises(ValueError, match='closed|contour'):
        measure_regions(triangles, PrintSettings(enabled=True))


@pytest.mark.parametrize('angles, expected', [((0, 0, 0), True), ((90, 0, 0), True), ((30, 45, 20), False)])
def test_first_layer_nominal_line_footprint_follows_print_orientation(tmp_path, angles, expected):
    from backend.print_geometry import measure_regions
    from backend.print_model import homogenize
    from backend.schemas import Material
    triangles = box_triangles(tmp_path)
    settings = PrintSettings(enabled=True, rotation_deg=angles)
    regions = measure_regions(triangles, settings)
    first = regions['first_layer_nominal_footprint']
    assert first['slice_height_mm'] == pytest.approx(.1)
    assert (first['centerline_region_area_mm2'] > 0) == expected
    assert first['has_centerline_area'] is expected
    result = homogenize([[0, 0, 0], [40, 10, 8]], Material(), settings, regions=regions)
    assert any('first model layer' in a for a in result['assumptions']) == (not expected)


@pytest.mark.parametrize('method, angles', [('layer-contours-v1', (0, 0, 0)),
    ('bounding-box-v1', (0, 0, 0)), ('layer-contours-v1', (30, 45, 20))])
def test_print_preview_solve_and_archive_keep_the_recorded_method(tmp_path, method, angles):
    import json, os, subprocess, sys, zipfile
    from fastapi.testclient import TestClient
    from backend.app import app
    from backend.geometry import build_model
    from backend.schemas import Analysis, Material
    from backend.solver import solve_model
    from backend.report import export_report
    from backend.storage import resource, write_json
    model = build_model(Geometry(kind='custom', mesh_size=6,
        features=[Feature(size=(60,24,16)), Feature(operation='cut', origin=(-1,2,2), size=(62,20,15))]))
    setup = Analysis(model_id=model['id'], confirmed=True,
        fixed_faces=[model['recommended']['fixed_face']],
        loads=[{'face_id': model['recommended']['load_face'], 'vector': [0,0,-4]}],
        material=Material(name='Illustrative PLA', young_mpa=3500, poisson=.35, yield_mpa=40, density_kg_m3=1240),
        print=PrintSettings(enabled=True, rotation_deg=angles))
    result = solve_model(setup, reproduction_print_model=method)
    client = TestClient(app)
    response = client.post('/api/print-preview', json={k: setup.model_dump(mode='json')[k]
                                                     for k in ('model_id','material','print')})
    assert response.status_code == 200, response.text
    preview = response.json()
    assert preview['geometry_method'] == 'layer-contours-v1'
    assert preview['filament_mass_g'] == pytest.approx(7.608650244 if any(angles) else 7.170779136, rel=1e-6)
    if any(angles):
        assert not preview['first_layer_nominal_footprint']['has_centerline_area']
        assert any('first model layer' in warning for warning in result['warnings'])
    assert client.post('/api/readiness', json={k: v for k, v in setup.model_dump(mode='json').items()
        if k in ('model_id','material','fixed_faces','loads','confirmed','print')}).json()['ready']
    if method == 'layer-contours-v1':
        for key in ('filament_mass_g','volume_fraction','young_xy_mpa','young_z_mpa'):
            assert preview[key] == pytest.approx(result['print'][key], rel=1e-10)
    else:
        # Historical snapshots predate the method field. Export them unchanged
        # and verify that the bundled script selects the original box method.
        assert result['mass_g'] < 3
        result['print'].pop('geometry_method')
        write_json(resource('runs', result['id'])/'result.json', result)
    with zipfile.ZipFile(export_report(result['id'], 'zip')) as archive:
        assert 'source/backend/print_geometry.py' in archive.namelist()
        if any(angles):
            assert 'first model layer' in archive.read('report.html').decode()
            assert not json.loads(archive.read('result.json'))['print']['first_layer_nominal_footprint']['has_centerline_area']
        archive.extractall(tmp_path)
    process = subprocess.run([sys.executable, str(tmp_path/'reproduce.py')], cwd=tmp_path,
        env={**os.environ, 'PYTHONPATH': ''}, capture_output=True, text=True, timeout=60)
    assert process.returncode == 0, process.stderr
    path = next((tmp_path/'reproduced/runs').glob('*/result.json'))
    actual = json.loads(path.read_text())
    assert actual['print']['geometry_method'] == method
    assert actual['mass_g'] == pytest.approx(result['mass_g'], rel=1e-10)
    if any(angles):
        assert any('first model layer' in warning for warning in actual['warnings'])
    with np.load(resource('runs', result['id'])/'solution.npz') as expected, np.load(path.parent/'solution.npz') as reproduced:
        np.testing.assert_allclose(reproduced['dof_displacement'], expected['dof_displacement'], rtol=1e-9, atol=1e-12)
