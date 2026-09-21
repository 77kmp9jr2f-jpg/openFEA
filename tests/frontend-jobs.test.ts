import { test } from 'node:test';
import assert from 'node:assert/strict';
import { job } from '../frontend/src/types.ts';
import { solveGPU } from '../frontend/src/gpu.ts';

test('cancelling a solver cannot cancel a concurrent Astra job', async () => {
  const original = globalThis.fetch;
  const cancelled: string[] = [];
  globalThis.fetch = async (url) => {
    const path = String(url);
    if (path.endsWith('/cancel')) {
      cancelled.push(path);
      return Response.json({ status: 'cancelled' });
    }
    if (path === '/api/solve') return Response.json({ id: 'solver' });
    if (path === '/api/assistant') return Response.json({ id: 'astra' });
    return Response.json({ status: 'complete', result: path });
  };
  try {
    const controller = new AbortController();
    const solver = job('/solve', {}, undefined, controller.signal);
    const rejected = assert.rejects(solver, { name: 'AbortError' });
    const astra = job('/assistant', {});
    controller.abort();
    await rejected;
    assert.equal(await astra, '/api/jobs/astra');
    assert.deepEqual(cancelled, ['/api/jobs/solver/cancel']);
  } finally { globalThis.fetch = original; }
});

test('cancellation before server job ID arrives still cancels that job', async () => {
  const original = globalThis.fetch;
  let resolve!: (response: Response) => void;
  const paths: string[] = [];
  globalThis.fetch = async (url) => {
    paths.push(String(url));
    return paths.length === 1 ? new Promise<Response>(r => { resolve = r; }) : Response.json({});
  };
  try {
    const controller = new AbortController();
    const pending = job('/models', {}, undefined, controller.signal);
    const rejected = assert.rejects(pending, { name: 'AbortError' });
    controller.abort();
    resolve(Response.json({ id: 'late' }));
    await rejected;
    assert.deepEqual(paths, ['/api/models', '/api/jobs/late/cancel']);
  } finally { globalThis.fetch = original; }
});

test('a cancelled GPU solve stops before requesting a device', async () => {
  const controller = new AbortController(); controller.abort();
  await assert.rejects(solveGPU({ id: 'x', n: 1, row_ptr: [0, 1], col_idx: [0], values: [1], rhs: [1], diagonal: [1] }, () => {}, controller.signal), { name: 'AbortError' });
});
