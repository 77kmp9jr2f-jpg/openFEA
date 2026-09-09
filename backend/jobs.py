"""Bounded child processes keep meshing/solves responsive and failure-isolated."""
import os, signal, subprocess, sys, threading
from concurrent.futures import ThreadPoolExecutor
from .storage import DATA, ROOT, identifier, write_json

POOL = ThreadPoolExecutor(max_workers=2)
SLOTS = threading.BoundedSemaphore(6)

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
                try: process.wait(timeout=210)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid,signal.SIGTERM)
                    try: process.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        os.killpg(process.pid,signal.SIGKILL); process.wait()
                    raise ValueError('The job exceeded 210 seconds. Use a coarser mesh or simplify the request.')
                if process.returncode and not (folder/'failure.json').exists():
                    raise ValueError('The geometry/solver worker stopped unexpectedly. Simplify the model or increase mesh size.')
            from .storage import read_json
            if (folder/'failure.json').exists():
                raise ValueError(read_json(folder/'failure.json')['error'])
            result = read_json(folder/'output.json')
            write_json(folder/'status.json',{'id':jid,'status':'complete','kind':kind,'result':result})
        except Exception as exc:
            write_json(folder/'status.json',{'id':jid,'status':'failed','kind':kind,'error':str(exc)})
        finally: SLOTS.release()
    POOL.submit(work)
    return {'id':jid,'status':'queued'}
