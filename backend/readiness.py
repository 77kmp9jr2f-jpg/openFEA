"""Machine-readable analysis readiness for people and agents.

One verdict answers: can this model be solved inside the stated scope, and
what is still missing. The workspace and /api/agent use the same checks.
"""

SCOPE = {
    'physics': (
        'One connected solid; small-strain static linear elasticity; '
        'optional homogenized print equivalent.'
    ),
    'units': 'mm, N, MPa',
    'residual_limit': 1e-7,
    'confirm_required': True,
    'generated_code': False,
    'deferred': [
        'contact / assemblies',
        'plasticity, buckling, fatigue, transients',
        'printed-part strength / coupon calibration',
        'hosted Sites',
        'sketch-to-mesh',
    ],
}


def face_catalog(model: dict) -> list[dict]:
    rec = model.get('recommended') or {}
    catalog = []
    for face in model.get('faces') or []:
        role = None
        if face['id'] == rec.get('fixed_face'):
            role = 'recommended_fixture'
        elif face['id'] == rec.get('load_face'):
            role = 'recommended_load'
        catalog.append({
            'id': face['id'],
            'label': face.get('label') or f"Face {face['id']}",
            'kind': face.get('kind'),
            'area_mm2': face.get('area_mm2'),
            'center': face.get('center'),
            'role_hint': role,
        })
    return catalog


def analysis_readiness(model: dict, draft: dict | None = None) -> dict:
    draft = draft or {}
    faces = {face['id']: face for face in model.get('faces') or []}
    fixed = list(draft.get('fixed_faces') or [])
    loads = list(draft.get('loads') or [])
    load_ids = [load['face_id'] if isinstance(load, dict) else load.face_id for load in loads]
    material = draft.get('material')
    confirmed = bool(draft.get('confirmed'))
    rec = model.get('recommended') or {}

    def check(ident, ok, detail, fix=None):
        item = {'id': ident, 'ok': bool(ok), 'detail': detail}
        if fix and not ok:
            item['fix'] = fix
        return item

    mesh_ok = (
        1 <= int(model.get('tetrahedra') or 0) <= 35000
        and float(model.get('volume_mm3') or 0) > 0
        and float(model.get('min_quality') or 0) > 0
    )
    faces_ok = len(faces) >= 2
    known = set(faces)
    fixture_ok = bool(fixed) and set(fixed) <= known
    load_ok = bool(load_ids) and set(load_ids) <= known
    overlap = set(fixed) & set(load_ids)
    material_ok = material is not None
    confirm_ok = confirmed

    checks = [
        check(
            'mesh_usable',
            mesh_ok,
            (
                f"{model.get('tetrahedra', 0)} tetrahedra, volume "
                f"{model.get('volume_mm3', 0):.4g} mm³, min quality "
                f"{model.get('min_quality', 0):.3g}."
                if mesh_ok
                else 'The mesh is not a usable single solid. Repair geometry or increase mesh size.'
            ),
            'POST /api/models with a watertight STL/STEP or a parametric solid.',
        ),
        check(
            'faces_selectable',
            faces_ok,
            (
                f"{len(faces)} selectable surfaces. Clustered STL patches are not CAD faces."
                if faces_ok
                else 'Need at least two selectable faces so one can be fixed and one loaded.'
            ),
            'Repair the mesh or change the feature angle, then rebuild.',
        ),
        check(
            'fixture',
            fixture_ok and not overlap,
            (
                'A face cannot be both fully fixed and loaded.'
                if overlap
                else (
                    f"Fixed faces {fixed}."
                    if fixture_ok
                    else 'Select at least one fully fixed face that belongs to this model revision.'
                )
            ),
            f"Set fixed_faces to a face id from faces[]. Recommended fixture is {rec.get('fixed_face')}.",
        ),
        check(
            'load',
            load_ok and not overlap,
            (
                'A face cannot be both fully fixed and loaded.'
                if overlap
                else (
                    f"Loaded faces {load_ids}."
                    if load_ok
                    else 'Select at least one loaded face with a nonzero global XYZ force.'
                )
            ),
            f"Set loads to [{{face_id, vector}}]. Recommended load face is {rec.get('load_face')}.",
        ),
        check(
            'material',
            material_ok,
            (
                f"{material.get('name') if isinstance(material, dict) else getattr(material, 'name', 'Material')} "
                'is a user-supplied input, not a certified coupon.'
                if material_ok
                else 'Supply name, E, ν, yield and density. Presets are illustrative.'
            ),
            'Include material in the readiness draft and in POST /api/solve.',
        ),
        check(
            'confirm',
            confirm_ok,
            (
                'Setup is marked reviewed. Confirmation is a review gate, not metrology.'
                if confirm_ok
                else 'Review fixtures, loads and material, then check the confirmation box. Agents must send confirmed=true; they cannot skip it.'
            ),
            'POST /api/solve with the same setup and confirmed=true.',
        ),
        check(
            'scope',
            True,
            SCOPE['physics'] + ' Residual must be < 1e-7. Model-generated CAD/solver code is not executed.',
        ),
    ]
    missing = [item['id'] for item in checks if not item['ok']]
    blocked = any(item['id'] in ('mesh_usable', 'faces_selectable') and not item['ok'] for item in checks)
    status = 'blocked' if blocked else ('ready' if not missing else 'incomplete')
    if blocked:
        nxt = 'Repair the solid so it meshes as one watertight body with at least two selectable faces.'
        agent_next = nxt
    elif 'fixture' in missing or 'load' in missing:
        nxt = (
            'Use recommended fixture and load, or select faces on the model. '
            f"Recommended fixture {rec.get('fixed_face')}, load {rec.get('load_face')}."
        )
        agent_next = (
            'Set fixed_faces and loads from faces[] or recommended. '
            f"Recommended fixture {rec.get('fixed_face')}, load {rec.get('load_face')}."
        )
    elif 'material' in missing:
        nxt = 'Supply a complete material (E, ν, yield, density).'
        agent_next = nxt
    elif 'confirm' in missing:
        nxt = 'Review this verdict, check confirmation, then run the simulation.'
        agent_next = 'Review this verdict, then POST /api/solve with confirmed=true.'
    else:
        nxt = (
            'Run the simulation. Trust guidance, residual, mass and hashes — '
            'not peak stress or printed strength.'
        )
        agent_next = (
            'POST /api/solve. Poll GET /api/jobs/{id}. '
            'Trust guidance, relative_residual, mass and hashes — not peak stress or printed strength.'
        )
    spec = model.get('spec') or {}
    return {
        'status': status,
        'ready': status == 'ready',
        'can_solve': status == 'ready',
        'missing': missing,
        'next': nxt,
        'agent_next': agent_next,
        'scope': SCOPE,
        'model': {
            'id': model.get('id'),
            'name': spec.get('name'),
            'kind': spec.get('kind'),
            'tetrahedra': model.get('tetrahedra'),
            'volume_mm3': model.get('volume_mm3'),
            'bounds_mm': model.get('bounds'),
            'sha256': model.get('sha256'),
            'mesh_sha256': model.get('mesh_sha256'),
        },
        'faces': face_catalog(model),
        'recommended': {
            'fixed_faces': [rec['fixed_face']] if rec.get('fixed_face') else [],
            'loads': (
                [{'face_id': rec['load_face'], 'vector': [0, 0, -40]}]
                if rec.get('load_face')
                else []
            ),
        },
        'checks': checks,
    }


def agent_contract() -> dict:
    return {
        'name': 'OpenFEA agent contract',
        'version': '1',
        'gates': {
            'confirm_required': True,
            'max_relative_residual': SCOPE['residual_limit'],
            'no_generated_code': True,
            'cpu_solve': 'POST /api/solve runs the local CPU reference solver.',
            'gpu_solve': (
                'GPU is an explicit browser WebGPU path '
                '(/api/gpu/prepare then /api/gpu/finish). It is not headless. '
                'The server still rejects residual ≥ 1e-7.'
            ),
            'scope': SCOPE,
        },
        'workflow': [
            {
                'id': 'import_stl',
                'method': 'POST',
                'path': '/api/stls',
                'body': 'raw STL bytes',
                'headers': {'X-Filename': 'part.stl'},
                'note': 'Refuse to mesh unless watertight is true.',
            },
            {
                'id': 'import_step',
                'method': 'POST',
                'path': '/api/steps',
                'body': 'raw STEP bytes',
            },
            {
                'id': 'build',
                'method': 'POST',
                'path': '/api/models',
                'body': 'Geometry (kind stl|step|bracket|plate|shaft|custom)',
                'returns': 'job {id, status}',
            },
            {
                'id': 'poll',
                'method': 'GET',
                'path': '/api/jobs/{id}',
                'complete_when': "status == 'complete'",
            },
            {
                'id': 'readiness',
                'method': 'POST',
                'path': '/api/readiness',
                'body': 'ReadinessRequest',
                'note': 'Same verdict the workspace shows. Do not scrape the UI.',
            },
            {
                'id': 'solve',
                'method': 'POST',
                'path': '/api/solve',
                'body': 'Analysis with confirmed=true',
                'rejects': [
                    'confirmed=false',
                    'unknown or overlapping faces',
                    'relative residual ≥ 1e-7',
                    'assemblies / contact / extra physics',
                ],
            },
            {
                'id': 'result',
                'method': 'GET',
                'path': '/api/runs/{id}',
                'read': [
                    'guidance',
                    'relative_residual',
                    'max_displacement_mm',
                    'mass_g',
                    'model_sha256',
                    'mesh_sha256',
                    'warnings',
                ],
            },
            {
                'id': 'report',
                'method': 'GET',
                'path': '/api/runs/{id}/report/json',
            },
        ],
    }
