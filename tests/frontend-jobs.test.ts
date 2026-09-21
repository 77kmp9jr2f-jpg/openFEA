import { test } from 'node:test';
import assert from 'node:assert/strict';
import { job, contextKey, normalizeGeometry, demoGeometry } from '../frontend/src/types.ts';
import { solveGPU } from '../frontend/src/gpu.ts';

test('legacy geometry compares equal to a fresh normalized proposal without rebuilding', () => {
  const legacy = { ...demoGeometry };
  delete legacy.accept_stl_preprocessing;
  const fresh = { ...legacy, accept_stl_preprocessing: false };
  assert.equal(contextKey(normalizeGeometry(legacy)), contextKey(fresh));
  assert.notEqual(contextKey(normalizeGeometry(legacy)), contextKey({ ...fresh, unit_scale: 25.4 }));
});

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

test('cancellation during GPU readback destroys device and buffers', async () => {
  const controller = new AbortController();
  const names = ['navigator', 'GPUBufferUsage', 'GPUShaderStage', 'GPUMapMode'];
  const descriptors = names.map(name => Object.getOwnPropertyDescriptor(globalThis, name));
  let destroyed = 0, allocated = 0, released = 0;
  const device = {
    lost: new Promise(() => {}), addEventListener() {}, destroy() { destroyed++; },
    limits: { maxStorageBufferBindingSize: 1e8, maxBufferSize: 1e8 },
    queue: { writeBuffer() {}, submit() {} },
    createBuffer() { allocated++; return { destroy() { released++; }, mapAsync() { controller.abort(); return Promise.reject(new Error('Device destroyed')); } }; },
    createBindGroupLayout() {}, createBindGroup() {}, createPipelineLayout() {},
    createShaderModule() { return { getCompilationInfo: async () => ({ messages: [] }) }; },
    createComputePipelineAsync: async () => ({}),
    createCommandEncoder() { return { beginComputePass: () => ({ setBindGroup() {}, setPipeline() {}, dispatchWorkgroups() {}, end() {} }), copyBufferToBuffer() {}, finish() {} }; },
  };
  const replacements = [{ gpu: { requestAdapter: async () => ({ info: { vendor: 'test', isFallbackAdapter: false }, requestDevice: async () => device }) } },
    { STORAGE: 1, COPY_DST: 2, COPY_SRC: 4, MAP_READ: 8, UNIFORM: 16 }, { COMPUTE: 1 }, { READ: 1 }];
  names.forEach((name, i) => Object.defineProperty(globalThis, name, { configurable: true, value: replacements[i] }));
  try {
    await assert.rejects(solveGPU({ id: 'x', n: 1, row_ptr: [0, 1], col_idx: [0], values: [1], rhs: [1], diagonal: [1] }, () => {}, controller.signal), { name: 'AbortError' });
    assert.ok(allocated > 0); assert.equal(released, allocated); assert.ok(destroyed > 0);
  } finally {
    names.forEach((name, i) => descriptors[i] ? Object.defineProperty(globalThis, name, descriptors[i]!) : Reflect.deleteProperty(globalThis, name));
  }
});
