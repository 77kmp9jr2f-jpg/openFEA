"""Astra must interpret recorded print results independently of current drafts."""
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from backend.schemas import AssistantRequest, Geometry, PrintSettings
from backend.storage import identifier, resource, write_json


@pytest.mark.parametrize('method', ['layer-contours-v1', 'bounding-box-v1', None])
def test_recorded_print_context_survives_changed_draft(monkeypatch, method):
    from backend.assistant import ask_astra
    model_id, run_id = identifier(), identifier()
    resource('models', model_id).mkdir()
    resource('runs', run_id).mkdir()
    geometry = Geometry(kind='plate', length=40, width=10, thickness=8, hole_diameter=0)
    write_json(resource('models', model_id)/'model.json', {
        'id': model_id, 'spec': geometry.model_dump(mode='json'),
        'bounds': [[0, 0, 0], [40, 10, 8]], 'faces': [],
    })
    recorded_print = None if method is None else {
        'enabled': True, 'geometry_method': method,
        'settings': PrintSettings(enabled=True, infill_density=.2).model_dump(mode='json'),
        'filament_mass_g': 2.15, 'assumptions': ['Recorded print assumption.'],
    }
    result = {'model_id': model_id, 'peak_von_mises_mpa': 1,
        'max_displacement_mm': .1, 'yield_ratio': 10, 'relative_residual': 1e-10,
        'force_balance_error_n': 1e-8, 'warnings': ['Recorded warning.'],
        'setup': {'conversation': [{'role': 'user', 'text': 'Full archived interview stays local.'}]}}
    if recorded_print is not None:
        result['print'] = recorded_print
    write_json(resource('runs', run_id)/'result.json', result)
    captured = {}

    def run_cli(command, **kwargs):
        captured['context'] = json.loads(kwargs['input'].split('\nDesign context:\n', 1)[1])
        Path(command[command.index('--output-last-message') + 1]).write_text(json.dumps({
            'message': 'Review the recorded print method.', 'questions': [],
            'proposal': None, 'simulation_proposal': None,
        }))
        return SimpleNamespace(returncode=0, stderr='')

    monkeypatch.setenv('FEAR_CODEX_BIN', '/test-only/codex')
    monkeypatch.setattr('backend.assistant.subprocess.run', run_cli)
    draft = PrintSettings(enabled=True, infill_density=.9, rotation_deg=(90, 0, 0))
    ask_astra(AssistantRequest(message='Explain this saved print result.', stage='results',
        geometry=geometry, model_id=model_id, run_id=run_id, print=draft))
    context = captured['context']
    assert context['result']['print'] == recorded_print
    assert context['print'] == draft.model_dump(mode='json')
    assert context['result']['warnings'] == ['Recorded warning.']
    assert 'Full archived interview stays local.' not in json.dumps(context)
