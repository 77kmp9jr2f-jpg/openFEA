"""Bounded child processes keep meshing/solves responsive and failure-isolated."""
import os, signal, subprocess, sys, threading
from concurrent.futures import ThreadPoolExecutor
from .storage import DATA, ROOT, identifier, write_json, read_json, resource

POOL = ThreadPoolExecutor(max_workers=2)
SLOTS = threading.BoundedSemaphore(6)
PROCESSES = {}
PROCESS_LOCK = threading.Lock()

def _stop(process):
    if process.poll() is not None:
        return
    os.killpg(process.pid, signal.SIGTERM)
    try:
        process.wait(timeout=3)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.wait()

def start_job(kind, payload):
    if not SLOTS.acquire(blocking=False):
        raise ValueError('The local worker queue is full. Wait for an active job to finish.')
    jid = identifier(); folder = DATA/'jobs'/jid; folder.mkdir()
    write_json(folder/'input.json',payload)
    write_json(folder/'status.json',{'id':jid,'status':'queued','kind':kind})
    def work():
        try:
            write_json(folder/'status.json',{'id':jid,'status':'running','kind':kind})
            env = dict(os.environ,OPENBLAS_NUM_THREADS='2',OMP_NUM_THREADS='2',VECLIB_MAXIMUM_THREADS='2')
            with (folder/'worker.log').open('w') as log:
                process = subprocess.Popen([sys.executable,'-m','backend.worker',kind,jid],cwd=ROOT,env=env,stdout=log,stderr=log,start_new_session=True)
                with PROCESS_LOCK:
                    PROCESSES[jid] = process
                try:
                    process.wait(timeout=210)
                except subprocess.TimeoutExpired:
                    _stop(process)
                    raise ValueError('The job exceeded 210 seconds. Use a coarser mesh or simplify the request.')
                finally:
                    with PROCESS_LOCK:
                        PROCESSES.pop(jid, None)
            if read_json(folder/'status.json').get('status') == 'cancelled':
                return
            if process.returncode and not (folder/'failure.json').exists():
                raise ValueError('The geometry/solver worker stopped unexpectedly. Simplify the model or increase mesh size.')
            if (folder/'failure.json').exists():
                raise ValueError(read_json(folder/'failure.json')['error'])
            result = read_json(folder/'output.json')
            write_json(folder/'status.json',{'id':jid,'status':'complete','kind':kind,'result':result})
        except Exception as exc:
            if read_json(folder/'status.json').get('status') == 'cancelled':
                return
            write_json(folder/'status.json',{'id':jid,'status':'failed','kind':kind,'error':str(exc)})
        finally: SLOTS.release()
    POOL.submit(work)
    return {'id':jid,'status':'queued'}

def cancel_job(jid):
    folder = resource('jobs', jid)
    status = read_json(folder/'status.json')
    if status['status'] in ('complete','failed','cancelled'):
        return status
    write_json(folder/'status.json',{'id':jid,'status':'cancelled','kind':status.get('kind'),'error':'The job was cancelled.'})
    with PROCESS_LOCK:
        process = PROCESSES.get(jid)
    if process is not None:
        _stop(process)
    return {'id':jid,'status':'cancelled'}
