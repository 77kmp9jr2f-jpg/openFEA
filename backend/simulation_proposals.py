"""Revision-bound simulation proposals, independent of any model transport."""
import hashlib,json
from .schemas import Analysis, Geometry, SimulationContext, SimulationDraft, PrintSettings
from .storage import DATA,identifier,resource,read_json,write_json


def _context(value):
    return SimulationContext.model_validate(value).model_dump(mode='json')


def _digest(context):
    return hashlib.sha256(json.dumps(context,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def _check_model(context,draft):
    model=read_json(resource('models',context['model_id'])/'model.json')
    if Geometry.model_validate(model['spec']) != Geometry.model_validate(context['geometry']):
        raise ValueError('Rebuild the edited geometry before requesting a simulation proposal.')
    face_ids={f['id'] for f in model['faces']}
    selected=set(draft['fixed_faces']) | {force['face_id'] for force in draft['loads']}
    if not selected <= face_ids:
        raise ValueError('Astra proposed a face that does not exist on this model. Re-select the face and ask again.')


def propose_setup(draft,context):
    context=_context(context)
    if context['print']['enabled'] and 'print' not in draft:
        raise ValueError('A printed-part proposal must include explicit print settings.')
    draft=SimulationDraft.model_validate(draft).model_dump(mode='json')
    _check_model(context,draft)
    pid=identifier()
    record={**draft,'id':pid,'model_id':context['model_id'],'source_context':context,'source_hash':_digest(context)}
    write_json(resource('setup_proposals',pid).with_suffix('.json'),record)
    return record


def _applied(record):
    notes=record['notes']
    if record['assumptions']:
        notes+='\n\nAstra setup assumptions:\n'+'\n'.join('- '+a for a in record['assumptions'])
    return {**{k:record[k] for k in ('model_id','material','fixed_faces','loads')},
            'print':record.get('print', PrintSettings().model_dump(mode='json')),
            'notes':notes,'setup_proposal_id':record['id'],'confirmed':False}


def apply_setup(pid,context):
    context=_context(context)
    record=read_json(resource('setup_proposals',pid).with_suffix('.json'))
    if record['model_id']!=context['model_id']:
        raise ValueError('This proposal belongs to an earlier model revision. Ask Astra for a new setup.')
    if _digest(context)!=record['source_hash']:
        raise ValueError('The setup or reference changed after this interview. Ask Astra to refresh the proposal.')
    _check_model(context,record)
    return _applied(record)


def verify_applied_setup(setup: Analysis):
    if not setup.setup_proposal_id:return
    record=read_json(resource('setup_proposals',setup.setup_proposal_id).with_suffix('.json'))
    applied=_applied(record)
    submitted=setup.model_dump(mode='json')
    if any(submitted[k]!=applied[k] for k in ('model_id','material','fixed_faces','loads','notes','print')):
        raise ValueError('The analysis differs from its applied Astra setup. Review a new proposal or clear its provenance for manual edits.')
    if any(submitted[k]!=record['source_context'][k] for k in ('reference_id','annotations')):
        raise ValueError('The reference differs from the applied Astra setup. Review a new proposal or clear its provenance for manual edits.')
