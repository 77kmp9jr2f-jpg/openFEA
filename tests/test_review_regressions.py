"""Independent regression checks for the print branch integration review."""
import copy
import numpy as np
import pytest


@pytest.mark.parametrize('angles', [(30, 45, 20), (-17, 63, 8), (0, 0, 41)])
def test_stiffness_rotation_matches_tensor_transform(angles):
    from backend.print_model import _rotate_voigt, _transverse, rotation_matrix
    local = _transverse(2300, 900, .32, 800, 500)
    rotation = rotation_matrix(angles)
    pairs = [(0, 0), (1, 1), (2, 2), (1, 2), (0, 2), (0, 1)]
    expected = np.zeros((6, 6))
    for column, (i, j) in enumerate(pairs):
        strain = np.zeros((3, 3))
        strain[i, j] = strain[j, i] = 1 if i == j else .5
        local_strain = rotation.T @ strain @ rotation
        engineering = np.array([local_strain[a, b] * (1 if a == b else 2) for a, b in pairs])
        stress_voigt = local @ engineering
        local_stress = np.zeros((3, 3))
        for value, (a, b) in zip(stress_voigt, pairs):
            local_stress[a, b] = local_stress[b, a] = value
        global_stress = rotation @ local_stress @ rotation.T
        expected[:, column] = [global_stress[a, b] for a, b in pairs]
    np.testing.assert_allclose(_rotate_voigt(local, rotation), expected, atol=1e-10)


def test_cancelled_queued_job_never_launches(monkeypatch):
    from backend import jobs
    from backend.storage import resource, read_json
    pending = []
    monkeypatch.setattr(jobs.POOL, 'submit', lambda work: pending.append(work))
    def forbidden(*args, **kwargs):
        pytest.fail('Cancelled queued work must not launch a child process')
    monkeypatch.setattr(jobs.subprocess, 'Popen', forbidden)
    queued = jobs.start_job('unused', {})
    jobs.cancel_job(queued['id'])
    pending.pop()()
    assert read_json(resource('jobs', queued['id']) / 'status.json')['status'] == 'cancelled'
    assert jobs.cancel_job(queued['id'])['status'] == 'cancelled'


def test_gpu_finish_accepts_every_supported_solver_dof():
    from backend.schemas import GPUSolution
    kwargs = dict(system_id='a' * 32, device='test adapter', iterations=1, refinements=1, seconds=0)
    assert len(GPUSolution(**kwargs, displacement=[0.] * 500000).displacement) == 500000
    with pytest.raises(ValueError):
        GPUSolution(**kwargs, displacement=[0.] * 500001)


def test_running_child_cancellation_stops_process_and_preserves_terminal_status(monkeypatch):
    import time, sys
    from backend import jobs
    from backend.storage import resource, read_json
    original_submit, original_popen = jobs.POOL.submit, jobs.subprocess.Popen
    futures, children = [], []
    def submit(work):
        future = original_submit(work); futures.append(future); return future
    def popen(_command, **kwargs):
        process = original_popen([sys.executable, '-c', 'import time; time.sleep(30)'], **kwargs)
        children.append(process); return process
    monkeypatch.setattr(jobs.POOL, 'submit', submit)
    monkeypatch.setattr(jobs.subprocess, 'Popen', popen)
    job = jobs.start_job('test', {})
    status_path = resource('jobs', job['id']) / 'status.json'
    try:
        deadline = time.monotonic() + 5
        while read_json(status_path)['status'] == 'queued' and time.monotonic() < deadline:
            time.sleep(.01)
        assert read_json(status_path)['status'] == 'running'
        assert jobs.cancel_job(job['id'])['status'] == 'cancelled'
        futures[0].result(timeout=5)
        assert children[0].poll() is not None
        assert read_json(status_path)['status'] == 'cancelled'
    finally:
        for process in children:
            if process.poll() is None: process.kill(); process.wait()


def test_dense_mesh_does_not_silently_downgrade_interpolation():
    from backend.solver import choose_element
    from types import SimpleNamespace
    mesh = SimpleNamespace(nvertices=10000, edges=np.empty((2, 160000)))
    with pytest.raises(ValueError, match='quadratic'):
        choose_element(mesh)


def test_comparison_discloses_changed_boundary_conditions_and_material():
    from backend.print_model import compare_results
    from backend.schemas import Material
    a = dict(id='a', model_id='m', mesh_sha256='same', element_order=2,
             max_displacement_mm=1., peak_von_mises_mpa=2., mass_g=3.,
             relative_residual=1e-12, force_balance_error_n=1e-10,
             setup=dict(material=Material().model_dump(), fixed_faces=[1],
                        loads=[dict(face_id=2, vector=[0, 0, -40])]))
    b = copy.deepcopy(a); b['id'] = 'b'
    assert compare_results(a, b)['same_analysis_context']
    b['setup']['loads'][0]['vector'][2] = -80
    compared = compare_results(a, b)
    assert not compared['same_analysis_context']
    assert 'loads' in compared['context_differences']
    assert compared['b']['setup']['loads'][0]['vector'][2] == -80
    b['setup']['material']['young_mpa'] *= .5
    assert 'material' in compare_results(a, b)['context_differences']
