/// <reference types="@webgpu/types" />
/** Real WebGPU sparse CG. Float64 residual refinement corrects float32 GPU drift. */
export type GPUSystem = {
  id: string;
  n: number;
  row_ptr: number[];
  col_idx: number[];
  values: number[];
  rhs: number[];
  diagonal: number[];
};
export type GPUCapability = { available: boolean; device: string };
let adapter: GPUAdapter | null = null;
export async function gpuCapability(): Promise<GPUCapability> {
  if (!navigator.gpu)
    return {
      available: false,
      device: "WebGPU is unavailable in this browser.",
    };
  try {
    adapter = await navigator.gpu.requestAdapter({
      powerPreference: "high-performance",
    });
    if (!adapter || adapter.info.isFallbackAdapter) {
      adapter = null;
      return {
        available: false,
        device: "A hardware GPU adapter is unavailable.",
      };
    }
    const info = adapter.info;
    return {
      available: true,
      device:
        [info.vendor, info.architecture, info.device, info.description]
          .filter(Boolean)
          .join(" · ") || "Local hardware GPU",
    };
  } catch (e) {
    return { available: false, device: (e as Error).message };
  }
}
const shader = /* wgsl */ `
struct Params { n: u32, groups: u32, tolerance_squared: f32, padding: u32 }
@group(0) @binding(0) var<storage, read> row: array<u32>;
@group(0) @binding(1) var<storage, read> col: array<u32>;
@group(0) @binding(2) var<storage, read> val: array<f32>;
// Four non-overlapping arrays: displacement, residual, direction, product.
@group(0) @binding(3) var<storage, read_write> v: array<f32>;
@group(0) @binding(4) var<storage, read_write> partial: array<f32>;
// rho, alpha, beta, residual squared, done (0 running, 1 converged, 2 breakdown)
@group(0) @binding(5) var<storage, read_write> s: array<f32>;
@group(0) @binding(6) var<uniform> u: Params;
var<workgroup> scratch: array<f32,128>;
@compute @workgroup_size(128) fn spmv(@builtin(global_invocation_id) id: vec3<u32>) {
  let i=id.x; if(i>=u.n || s[4]!=0.0){return;}
  var sum=0.0;
  for(var j=row[i];j<row[i+1u];j++){sum+=val[j]*v[2u*u.n+col[j]];}
  v[3u*u.n+i]=sum;
}
@compute @workgroup_size(128) fn dotp(@builtin(global_invocation_id) id: vec3<u32>,@builtin(local_invocation_index) li:u32,@builtin(workgroup_id) group:vec3<u32>) {
  let i=id.x; var value=0.0;
  if(i<u.n){value=v[2u*u.n+i]*v[3u*u.n+i];}
  scratch[li]=value;workgroupBarrier();
  for(var stride=64u;stride>0u;stride/=2u){if(li<stride){scratch[li]+=scratch[li+stride];}workgroupBarrier();}
  if(li==0u){partial[group.x]=scratch[0];}
}
@compute @workgroup_size(128) fn alpha(@builtin(local_invocation_index) li:u32) {
  var value=0.0;for(var i=li;i<u.groups;i+=128u){value+=partial[i];}
  scratch[li]=value;workgroupBarrier();
  for(var stride=64u;stride>0u;stride/=2u){if(li<stride){scratch[li]+=scratch[li+stride];}workgroupBarrier();}
  if(li==0u && s[4]==0.0){
    if(scratch[0]<=0.0){s[4]=2.0;}else{s[1]=s[0]/scratch[0];}
  }
}
@compute @workgroup_size(128) fn update(@builtin(global_invocation_id) id:vec3<u32>) {
  let i=id.x;if(i>=u.n || s[4]!=0.0){return;}
  v[i]+=s[1]*v[2u*u.n+i];v[u.n+i]-=s[1]*v[3u*u.n+i];
}
@compute @workgroup_size(128) fn dotr(@builtin(global_invocation_id) id:vec3<u32>,@builtin(local_invocation_index) li:u32,@builtin(workgroup_id) group:vec3<u32>) {
  let i=id.x;var value=0.0;if(i<u.n){value=v[u.n+i]*v[u.n+i];}
  scratch[li]=value;workgroupBarrier();
  for(var stride=64u;stride>0u;stride/=2u){if(li<stride){scratch[li]+=scratch[li+stride];}workgroupBarrier();}
  if(li==0u){partial[group.x]=scratch[0];}
}
@compute @workgroup_size(128) fn beta(@builtin(local_invocation_index) li:u32) {
  var value=0.0;for(var i=li;i<u.groups;i+=128u){value+=partial[i];}
  scratch[li]=value;workgroupBarrier();
  for(var stride=64u;stride>0u;stride/=2u){if(li<stride){scratch[li]+=scratch[li+stride];}workgroupBarrier();}
  if(li==0u && s[4]==0.0){s[3]=scratch[0];s[2]=s[3]/s[0];s[0]=s[3];if(s[3]<u.tolerance_squared){s[4]=1.0;}}
}
@compute @workgroup_size(128) fn direction(@builtin(global_invocation_id) id:vec3<u32>) {
  let i=id.x;if(i>=u.n || s[4]!=0.0){return;}
  v[2u*u.n+i]=v[u.n+i]+s[2]*v[2u*u.n+i];
}`;
export async function solveGPU(
  system: GPUSystem,
  progress: (message: string) => void,
) {
  const capability = await gpuCapability();
  if (!capability.available || !adapter)
    throw new Error(
      capability.device +
        " Select the CPU reference solver explicitly if needed.",
    );
  const started = performance.now(),
    n = system.n,
    groups = Math.ceil(n / 128);
  const device = await adapter.requestDevice();
  let failure = "",
    iterations = 0;
  device.lost.then((info) => {
    failure = info.message || "The GPU device was lost.";
  });
  device.addEventListener("uncapturederror", (e) => {
    failure = e.error.message;
  });
  const buffers: GPUBuffer[] = [];
  function buffer(
    data: ArrayBufferView<ArrayBuffer> | number,
    usage = GPUBufferUsage.STORAGE | GPUBufferUsage.COPY_DST,
  ) {
    const size = typeof data === "number" ? data : data.byteLength;
    if (
      size > device.limits.maxStorageBufferBindingSize ||
      size > device.limits.maxBufferSize
    )
      throw new Error(
        "This mesh exceeds this GPU’s buffer limit. Use a coarser mesh.",
      );
    const b = device.createBuffer({ size: Math.max(4, size), usage });
    buffers.push(b);
    if (typeof data !== "number") device.queue.writeBuffer(b, 0, data);
    return b;
  }
  try {
    const scales = Float64Array.from(system.diagonal, (d) => 1 / Math.sqrt(d));
    const values = new Float32Array(system.values.length);
    for (let i = 0; i < n; i++)
      for (let j = system.row_ptr[i]; j < system.row_ptr[i + 1]; j++)
        values[j] = system.values[j] * scales[i] * scales[system.col_idx[j]];
    const row = buffer(new Uint32Array(system.row_ptr)),
      col = buffer(new Uint32Array(system.col_idx)),
      matrix = buffer(values);
    const vectors = buffer(
      n * 16,
      GPUBufferUsage.STORAGE |
        GPUBufferUsage.COPY_DST |
        GPUBufferUsage.COPY_SRC,
    );
    const partial = buffer(groups * 4),
      state = buffer(
        32,
        GPUBufferUsage.STORAGE |
          GPUBufferUsage.COPY_DST |
          GPUBufferUsage.COPY_SRC,
      );
    const paramsData = new ArrayBuffer(16);
    new Uint32Array(paramsData).set([n, groups]);
    new Float32Array(paramsData)[2] = 1e-10;
    const params = buffer(
      new Uint8Array(paramsData),
      GPUBufferUsage.UNIFORM | GPUBufferUsage.COPY_DST,
    );
    const readState = buffer(
      32,
      GPUBufferUsage.COPY_DST | GPUBufferUsage.MAP_READ,
    );
    const readX = buffer(
      n * 4,
      GPUBufferUsage.COPY_DST | GPUBufferUsage.MAP_READ,
    );
    const layout = device.createBindGroupLayout({
      entries: [0, 1, 2, 3, 4, 5, 6].map((binding) => ({
        binding,
        visibility: GPUShaderStage.COMPUTE,
        buffer: {
          type:
            binding === 6
              ? "uniform"
              : binding < 3
                ? "read-only-storage"
                : "storage",
        },
      })),
    });
    const bind = device.createBindGroup({
      layout,
      entries: [row, col, matrix, vectors, partial, state, params].map(
        (b, binding) => ({ binding, resource: { buffer: b } }),
      ),
    });
    const pipelineLayout = device.createPipelineLayout({
      bindGroupLayouts: [layout],
    });
    const module = device.createShaderModule({ code: shader });
    const compilation = await module.getCompilationInfo();
    const errors = compilation.messages.filter((m) => m.type === "error");
    if (errors.length) throw new Error(errors.map((m) => m.message).join(" "));
    const pipelines = await Promise.all(
      ["spmv", "dotp", "alpha", "update", "dotr", "beta", "direction"].map(
        (entryPoint) =>
          device.createComputePipelineAsync({
            layout: pipelineLayout,
            compute: { module, entryPoint },
          }),
      ),
    );
    const x = new Float64Array(n),
      residual = new Float64Array(system.rhs);
    const norm = (a: ArrayLike<number>) => {
      let sum = 0;
      for (let i = 0; i < a.length; i++) sum += a[i] * a[i];
      return Math.sqrt(sum);
    };
    const rhsNorm = norm(residual);
    let relative = 1;
    for (let outer = 0; outer < 8; outer++) {
      let scaledNorm = 0;
      for (let i = 0; i < n; i++) scaledNorm += (residual[i] * scales[i]) ** 2;
      scaledNorm = Math.sqrt(scaledNorm);
      const initial = new Float32Array(n * 4);
      for (let i = 0; i < n; i++)
        initial[n + i] = initial[2 * n + i] =
          (residual[i] * scales[i]) / scaledNorm;
      device.queue.writeBuffer(vectors, 0, initial);
      device.queue.writeBuffer(
        state,
        0,
        new Float32Array([1, 0, 0, 1, 0, 0, 0, 0]),
      );
      for (let inner = 0; inner < 2400; inner += 20) {
        if (failure) throw new Error(failure);
        if (performance.now() - started > 150000)
          throw new Error(
            "GPU solve exceeded 150 seconds. Increase mesh size.",
          );
        const encoder = device.createCommandEncoder();
        const pass = encoder.beginComputePass();
        pass.setBindGroup(0, bind);
        for (let batch = 0; batch < 20; batch++)
          for (let k = 0; k < pipelines.length; k++) {
            pass.setPipeline(pipelines[k]);
            pass.dispatchWorkgroups(k === 2 || k === 5 ? 1 : groups);
          }
        pass.end();
        encoder.copyBufferToBuffer(state, 0, readState, 0, 32);
        device.queue.submit([encoder.finish()]);
        await readState.mapAsync(GPUMapMode.READ);
        const status = new Float32Array(readState.getMappedRange().slice(0));
        readState.unmap();
        iterations += 20;
        if (!Number.isFinite(status[3]) || status[4] === 2)
          throw new Error(
            "GPU iteration broke down. Check mesh quality and constraints.",
          );
        progress(
          `Local GPU · ${iterations} iterations · refinement ${outer + 1}`,
        );
        if (status[4] === 1) break;
      }
      const encoder = device.createCommandEncoder();
      encoder.copyBufferToBuffer(vectors, 0, readX, 0, n * 4);
      device.queue.submit([encoder.finish()]);
      await readX.mapAsync(GPUMapMode.READ);
      const correction = new Float32Array(readX.getMappedRange().slice(0));
      readX.unmap();
      for (let i = 0; i < n; i++)
        x[i] += correction[i] * scaledNorm * scales[i];
      // Recompute against the original float64 matrix. Never accept a recursive f32 residual alone.
      for (let i = 0; i < n; i++) {
        let product = 0;
        for (let j = system.row_ptr[i]; j < system.row_ptr[i + 1]; j++)
          product += system.values[j] * x[system.col_idx[j]];
        residual[i] = system.rhs[i] - product;
      }
      relative = norm(residual) / rhsNorm;
      if (!Number.isFinite(relative))
        throw new Error("GPU solution contains non-finite values.");
      if (relative < 1e-8)
        return {
          system_id: system.id,
          displacement: Array.from(x),
          device: capability.device,
          iterations,
          refinements: outer + 1,
          seconds: (performance.now() - started) / 1000,
        };
    }
    throw new Error(
      `GPU residual ${relative.toExponential(2)} exceeds the acceptance threshold. Use a coarser mesh or the CPU reference solver.`,
    );
  } finally {
    buffers.forEach((b) => b.destroy());
    device.destroy();
  }
}
