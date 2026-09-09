import sys, traceback
from .storage import resource, read_json, write_json
from .schemas import Geometry, Analysis, AssistantRequest, GPUSolution

if __name__ == '__main__':
    kind,jid = sys.argv[1:]
    folder = resource('jobs',jid)
    try:
        payload = read_json(folder/'input.json')
        if kind == 'model':
            from .geometry import build_model
            result = build_model(Geometry.model_validate(payload))
        elif kind == 'solve':
            from .solver import solve_model
            result = solve_model(Analysis.model_validate(payload))
        elif kind == 'gpu_prepare':
            from .solver import prepare_gpu
            result = prepare_gpu(Analysis.model_validate(payload))
        elif kind == 'gpu_finish':
            from .solver import finish_gpu
            result = finish_gpu(GPUSolution.model_validate(payload))
        elif kind == 'assistant':
            from .assistant import ask_astra
            result = ask_astra(AssistantRequest.model_validate(payload))
        else: raise ValueError('Unknown job type.')
        write_json(folder/'output.json',result)
    except Exception as exc:
        traceback.print_exc()
        message = str(exc) if isinstance(exc,(ValueError,FileNotFoundError)) else 'The operation failed. Check geometry, mesh size and setup; details are in the local job log.'
        write_json(folder/'failure.json',{'error':message})
        sys.exit(1)
