import { test } from 'node:test';
import assert from 'node:assert/strict';
import { solveGPU } from '../frontend/src/gpu.ts';

const system = { id: 'identity', n: 1, row_ptr: [0, 1], col_idx: [0], values: [1], rhs: [1], diagonal: [1] };
function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>(r => { resolve = r; });
  return { promise, resolve };
}

// A controllable API boundary, including operations that never settle after loss.
function fakeGPU(stage: 'adapter' | 'device' | 'compilation' | 'pipeline' | 'readback' | 'complete') {
  const reached = deferred<void>();
  const blocked = deferred<any>();
  const lost = deferred<{ message: string; reason: string }>();
  let requests = 0, destroyed = 0, allocated = 0, released = 0;
  const errors = new Set<(event: any) => void>();
  const pause = (at: string, value: any) => {
    if (stage !== at) return Promise.resolve(value);
    reached.resolve();
    return blocked.promise;
  };
  const device = {
    lost: lost.promise,
    addEventListener(_name: string, listener: (event: any) => void) { errors.add(listener); },
    removeEventListener(_name: string, listener: (event: any) => void) { errors.delete(listener); },
    destroy() { destroyed++; },
    limits: { maxStorageBufferBindingSize: 1e8, maxBufferSize: 1e8 },
    queue: { writeBuffer() {}, submit() {} },
    createBuffer({ size }: { size: number }) {
      allocated++;
      return {
        destroy() { released++; },
        mapAsync() { return pause('readback', undefined); },
        getMappedRange() { return size === 32 ? new Float32Array([1, 0, 0, 0, 1, 0, 0, 0]).buffer : new Float32Array([1]).buffer; },
        unmap() {},
      };
    },
    createBindGroupLayout() {}, createBindGroup() {}, createPipelineLayout() {},
    createShaderModule() { return { getCompilationInfo: () => pause('compilation', { messages: [] }) }; },
    createComputePipelineAsync() { return pause('pipeline', {}); },
    createCommandEncoder() { return { beginComputePass: () => ({ setBindGroup() {}, setPipeline() {}, dispatchWorkgroups() {}, end() {} }), copyBufferToBuffer() {}, finish() {} }; },
  };
  const names = ['navigator', 'GPUBufferUsage', 'GPUShaderStage', 'GPUMapMode'];
  const descriptors = names.map(name => Object.getOwnPropertyDescriptor(globalThis, name));
  const replacements = [{ gpu: { requestAdapter: async () => {
    requests++;
    return pause('adapter', { info: { vendor: 'test', isFallbackAdapter: false }, requestDevice: () => pause('device', device) });
  } } }, { STORAGE: 1, COPY_DST: 2, COPY_SRC: 4, MAP_READ: 8, UNIFORM: 16 }, { COMPUTE: 1 }, { READ: 1 }];
  names.forEach((name, i) => Object.defineProperty(globalThis, name, { configurable: true, value: replacements[i] }));
  return {
    reached: reached.promise, blocked, device,
    loss() { lost.resolve({ message: 'Injected device loss', reason: 'unknown' }); },
    error() { for (const listener of errors) listener({ error: { message: 'Injected out of memory' } }); },
    stats() { return { requests, destroyed, allocated, released, listeners: errors.size }; },
    restore() { names.forEach((name, i) => descriptors[i] ? Object.defineProperty(globalThis, name, descriptors[i]!) : Reflect.deleteProperty(globalThis, name)); },
  };
}

// Bound the assertion separately so a regression reports a failure, not a hung test.
async function settles(pending: Promise<unknown>) {
  let timer: ReturnType<typeof setTimeout>;
  try {
    return await Promise.race([pending, new Promise((_, reject) => { timer = setTimeout(() => reject(new Error('GPU operation did not settle')), 300); })]);
  } finally { clearTimeout(timer!); }
}

for (const stage of ['adapter', 'device', 'compilation', 'pipeline', 'readback'] as const) {
  test(`cancellation settles while GPU ${stage} is pending`, async () => {
    const gpu = fakeGPU(stage), controller = new AbortController();
    try {
      const pending = solveGPU(system, () => {}, controller.signal);
      const rejected = assert.rejects(settles(pending), { name: 'AbortError' });
      await gpu.reached;
      controller.abort();
      await rejected;
      if (stage === 'device') {
        gpu.blocked.resolve(gpu.device);
        await new Promise(resolve => setImmediate(resolve));
      }
      const state = gpu.stats();
      assert.equal(state.destroyed, stage === 'adapter' ? 0 : 1, 'including a device delivered after cancellation');
      assert.equal(state.released, state.allocated);
      assert.equal(state.listeners, 0);
    } finally { gpu.restore(); }
  });
}

for (const stage of ['compilation', 'readback'] as const) {
  test(`device loss settles pending ${stage} and releases resources`, async () => {
    const gpu = fakeGPU(stage);
    try {
      const pending = solveGPU(system, () => {});
      const rejected = assert.rejects(settles(pending), /GPU device was lost.*Retry/i);
      await gpu.reached;
      gpu.loss();
      await rejected;
      assert.equal(gpu.stats().released, gpu.stats().allocated);
      assert.equal(gpu.stats().destroyed, 1);
    } finally { gpu.restore(); }
  });
}

test('uncaptured GPU error interrupts a pending readback', async () => {
  const gpu = fakeGPU('readback');
  try {
    const pending = solveGPU(system, () => {});
    const rejected = assert.rejects(settles(pending), /Injected out of memory/);
    await gpu.reached;
    gpu.error();
    await rejected;
    assert.equal(gpu.stats().released, gpu.stats().allocated);
  } finally { gpu.restore(); }
});

test('deadline includes a readback that never settles', async t => {
  t.mock.timers.enable({ apis: ['setTimeout'] });
  const gpu = fakeGPU('readback');
  try {
    const pending = solveGPU(system, () => {});
    const rejected = assert.rejects(pending, /exceeded 150 seconds/);
    await gpu.reached;
    t.mock.timers.tick(150001);
    // Restore the real clock before the independent hung-test guard.
    t.mock.timers.reset();
    await settles(rejected);
    assert.equal(gpu.stats().released, gpu.stats().allocated);
  } finally { t.mock.timers.reset(); gpu.restore(); }
});

test('a retry acquires a fresh adapter and returns a verified solution', async () => {
  const failed = fakeGPU('readback');
  try {
    const pending = solveGPU(system, () => {});
    const rejected = assert.rejects(settles(pending), /device was lost/);
    await failed.reached;
    failed.loss();
    await rejected;
  } finally { failed.restore(); }
  const retry = fakeGPU('complete');
  try {
    const result = await solveGPU(system, () => {});
    assert.deepEqual(result.displacement, [1]);
    assert.equal(result.system_id, system.id);
    assert.equal(retry.stats().requests, 1);
    assert.equal(retry.stats().released, retry.stats().allocated);
    assert.equal(retry.stats().destroyed, 1);
  } finally { retry.restore(); }
});
