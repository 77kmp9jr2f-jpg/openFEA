"""Readiness verdict and agent contract — same checks for UI and API."""
from backend.readiness import analysis_readiness, agent_contract


def box_model(**overrides):
    model = {
        'id': 'a' * 32,
        'spec': {'name': 'Box', 'kind': 'stl', 'provenance': 'stl_import', 'assumptions': []},
        'tetrahedra': 200,
        'quadratic_dofs': 3000,
        'volume_mm3': 3200,
        'min_quality': 0.4,
        'bounds': [[0, 0, 0], [40, 10, 8]],
        'sha256': 'b' * 64,
        'mesh_sha256': 'c' * 64,
        'faces': [
            {'id': 1, 'label': 'X = 0.0 mm', 'kind': 'Plane', 'center': [0, 5, 4], 'area_mm2': 80},
            {'id': 2, 'label': 'X = 40.0 mm', 'kind': 'Plane', 'center': [40, 5, 4], 'area_mm2': 80},
        ],
        'recommended': {'fixed_face': 1, 'load_face': 2},
    }
    model.update(overrides)
    return model


PLA = {'name': 'PLA · illustrative filament', 'young_mpa': 3500, 'poisson': 0.35,
       'yield_mpa': 40, 'density_kg_m3': 1240}


def test_empty_draft_is_incomplete_with_catalog():
    verdict = analysis_readiness(box_model())
    assert verdict['status'] == 'incomplete'
    assert verdict['ready'] is False
    assert verdict['can_solve'] is False
    assert verdict['missing'] == ['fixture', 'load', 'material', 'confirm']
    assert [face['role_hint'] for face in verdict['faces']] == [
        'recommended_fixture', 'recommended_load']
    assert verdict['recommended']['fixed_faces'] == [1]
    assert verdict['recommended']['loads'][0]['face_id'] == 2
    assert '1e-7' in verdict['scope']['physics'] or verdict['scope']['residual_limit'] == 1e-7


def test_recommended_setup_still_requires_confirm():
    verdict = analysis_readiness(box_model(), {
        'material': PLA,
        'fixed_faces': [1],
        'loads': [{'face_id': 2, 'vector': [0, 0, -40]}],
        'confirmed': False,
    })
    assert verdict['status'] == 'incomplete'
    assert verdict['missing'] == ['confirm']
    assert any(item['id'] == 'confirm' and 'cannot skip' in item['detail'] for item in verdict['checks'])
    assert 'confirmed=true' in verdict['agent_next']


def test_confirmed_complete_setup_is_ready():
    verdict = analysis_readiness(box_model(), {
        'material': PLA,
        'fixed_faces': [1],
        'loads': [{'face_id': 2, 'vector': [0, 0, -40]}],
        'confirmed': True,
    })
    assert verdict['status'] == 'ready'
    assert verdict['ready'] is True
    assert verdict['can_solve'] is True
    assert verdict['missing'] == []
    assert 'Run the simulation' in verdict['next']
    assert 'POST /api/solve' in verdict['agent_next']


def test_unknown_or_overlapping_faces_block_setup():
    unknown = analysis_readiness(box_model(), {
        'material': PLA, 'fixed_faces': [9],
        'loads': [{'face_id': 2, 'vector': [0, 0, -1]}], 'confirmed': True})
    assert 'fixture' in unknown['missing']
    overlap = analysis_readiness(box_model(), {
        'material': PLA, 'fixed_faces': [1],
        'loads': [{'face_id': 1, 'vector': [0, 0, -1]}], 'confirmed': True})
    assert 'fixture' in overlap['missing'] and 'load' in overlap['missing']


def test_unusable_mesh_is_blocked():
    verdict = analysis_readiness(box_model(tetrahedra=0, volume_mm3=0, min_quality=0, faces=[]))
    assert verdict['status'] == 'blocked'
    assert 'mesh_usable' in verdict['missing']
    assert 'faces_selectable' in verdict['missing']


def test_quadratic_capacity_is_checked_before_inviting_a_solve():
    draft = {'material': PLA, 'fixed_faces': [1],
             'loads': [{'face_id': 2, 'vector': [0, 0, -40]}], 'confirmed': True}
    verdict = analysis_readiness(box_model(quadratic_dofs=500001), draft)
    assert verdict['status'] == 'blocked'
    assert verdict['can_solve'] is False
    assert 'mesh_usable' in verdict['missing']
    assert 'coarser' in verdict['next'].lower()
    assert '500,001' in next(c['detail'] for c in verdict['checks'] if c['id'] == 'mesh_usable')
    assert analysis_readiness(box_model(quadratic_dofs=500000), draft)['ready'] is True


def test_legacy_model_capacity_uses_its_mesh_without_rewriting_it():
    import numpy as np
    from backend.readiness import load_readiness_model
    from backend.storage import resource, write_json
    model = box_model()
    del model['quadratic_dofs']
    folder = resource('models', model['id'])
    folder.mkdir(exist_ok=True)
    write_json(folder/'model.json', model)
    before = (folder/'model.json').read_bytes()
    np.savez(folder/'mesh.npz', points=np.array([[0,0,0],[1,0,0],[0,1,0],[0,0,1]]),
             tets=np.array([[0,1,2,3]]))
    assert load_readiness_model(model['id'])['quadratic_dofs'] == 30
    assert (folder/'model.json').read_bytes() == before


def test_agent_contract_names_gates_and_forbids_ui_scraping():
    contract = agent_contract()
    assert contract['gates']['confirm_required'] is True
    assert contract['gates']['max_relative_residual'] == 1e-7
    assert contract['gates']['no_generated_code'] is True
    steps = {item['id']: item for item in contract['workflow']}
    assert steps['readiness']['path'] == '/api/readiness'
    assert 'Do not scrape' in steps['readiness']['note']
    assert 'confirmed=false' in steps['solve']['rejects']
    assert 'guidance' in steps['result']['read']
