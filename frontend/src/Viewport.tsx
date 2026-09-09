import { useEffect, useRef, useState } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { Box, Maximize2, Camera, Layers3, RotateCcw } from "lucide-react";
import type { Model, Result, Load, Vec3 } from "./types";
import { format } from "./types";

type Props = {
  model: Model | null;
  result: Result | null;
  fixed: number[];
  loads: Load[];
  selected: number | null;
  onSelect: (id: number) => void;
  field: "solid" | "stress" | "displacement";
  deform: boolean;
  wireframe: boolean;
  setWireframe: (b: boolean) => void;
};
const palette = [
  "#194d6b",
  "#347fa4",
  "#57afb0",
  "#b9cf87",
  "#efc260",
  "#de6b45",
  "#ae383a",
];
function colorAt(t: number) {
  const p = Math.max(0, Math.min(1, t)) * (palette.length - 1);
  return new THREE.Color(palette[Math.floor(p)]).lerp(
    new THREE.Color(palette[Math.min(Math.floor(p) + 1, palette.length - 1)]),
    p % 1,
  );
}
function label(text: string, color = "#263b33") {
  const c = document.createElement("canvas");
  c.width = 512;
  c.height = 100;
  const cx = c.getContext("2d")!;
  cx.font = "500 60px Arial";
  cx.textAlign = "center";
  cx.fillStyle = "rgba(246,247,241,.92)";
  cx.roundRect(0, 0, 512, 100, 20);
  cx.fill();
  cx.fillStyle = color;
  cx.fillText(text, 256, 64);
  const tex = new THREE.CanvasTexture(c);
  const mat = new THREE.SpriteMaterial({ map: tex, depthTest: false });
  const sprite = new THREE.Sprite(mat);
  sprite.scale.set(36, 8, 1);
  return sprite;
}
export default function Viewport(p: Props) {
  const host = useRef<HTMLDivElement>(null),
    sceneRef = useRef<
      { renderer: THREE.WebGLRenderer; reset: () => void } | undefined
    >(undefined),
    onSelect = useRef(p.onSelect);
  onSelect.current = p.onSelect;
  const [hover, setHover] = useState<number | null>(null),
    [error, setError] = useState("");
  const savedCamera = useRef<
    { position: Vec3; target: Vec3; zoom: number; mid: string } | undefined
  >(undefined);
  useEffect(() => {
    if (!host.current || !p.model) return;
    const container = host.current,
      m = p.model;
    let renderer: THREE.WebGLRenderer;
    try {
      renderer = new THREE.WebGLRenderer({
        antialias: true,
        alpha: true,
        preserveDrawingBuffer: true,
      });
    } catch {
      setError(
        "WebGL could not start. Enable hardware acceleration to view the model. The solver and exports remain available.",
      );
      return;
    }
    setError("");
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setClearColor(0xf4f5ef, 0);
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.domElement.setAttribute(
      "aria-label",
      "Interactive 3D model. Drag to orbit; click a face to select it.",
    );
    container.appendChild(renderer.domElement);
    const scene = new THREE.Scene();
    const lo = new THREE.Vector3(...m.bounds[0]),
      hi = new THREE.Vector3(...m.bounds[1]);
    const center = lo.clone().add(hi).multiplyScalar(0.5);
    const span = hi.clone().sub(lo).length();
    const cam = new THREE.OrthographicCamera(
      -span,
      span,
      span,
      -span,
      0.01,
      span * 30,
    );
    cam.up.set(0, 0, 1);
    cam.position
      .copy(center)
      .add(new THREE.Vector3(1.6, -2.2, 1.6).multiplyScalar(span));
    const controls = new OrbitControls(cam, renderer.domElement);
    controls.target.copy(center);
    controls.enableDamping = true;
    controls.minZoom = 0.4;
    controls.maxZoom = 7;
    if (savedCamera.current?.mid === m.id) {
      cam.position.fromArray(savedCamera.current.position);
      controls.target.fromArray(savedCamera.current.target);
      cam.zoom = savedCamera.current.zoom;
    }
    const reset = () => {
      cam.position
        .copy(center)
        .add(new THREE.Vector3(1.6, -2.2, 1.6).multiplyScalar(span));
      controls.target.copy(center);
      cam.zoom = 1;
      cam.updateProjectionMatrix();
      controls.update();
    };
    sceneRef.current = { renderer, reset };
    scene.add(new THREE.HemisphereLight(0xffffff, 0x657066, 2.5));
    const light = new THREE.DirectionalLight(0xfff4df, 3);
    light.position.set(span, -span, span * 3);
    scene.add(light);
    const fill = new THREE.DirectionalLight(0xe5f2ff, 1.8);
    fill.position.set(-span, span, span);
    scene.add(fill);
    const grid = new THREE.GridHelper(span * 3, 40, 0xcbd1c3, 0xe0e4d8);
    grid.rotation.x = Math.PI / 2;
    grid.position.set(center.x, center.y, lo.z - 1);
    scene.add(grid);
    const isResult = p.result && p.field !== "solid";
    const deformation =
      isResult && p.deform && p.result!.max_displacement_mm > 0
        ? (span * 0.06) / p.result!.max_displacement_mm
        : 0;
    const meshes: THREE.Mesh[] = [];
    for (const face of m.faces) {
      const positions: number[] = [],
        colors: number[] = [];
      for (const tri of face.triangles)
        for (const ni of tri) {
          const node = m.nodes[ni],
            d = p.result?.displacement[ni] || [0, 0, 0];
          positions.push(...node.map((v, j) => v + d[j] * deformation));
          if (isResult) {
            const val =
              p.field === "stress"
                ? p.result!.nodal_stress_mpa[ni] /
                  p.result!.max_display_stress_mpa
                : Math.hypot(...d) / p.result!.max_displacement_mm;
            const c = colorAt(val);
            colors.push(c.r, c.g, c.b);
          }
        }
      const g = new THREE.BufferGeometry();
      g.setAttribute(
        "position",
        new THREE.Float32BufferAttribute(positions, 3),
      );
      if (isResult)
        g.setAttribute("color", new THREE.Float32BufferAttribute(colors, 3));
      g.computeVertexNormals();
      const fixed = p.fixed.includes(face.id),
        loaded = p.loads.some((l) => l.face_id === face.id),
        selected = p.selected === face.id;
      const mat = new THREE.MeshStandardMaterial({
        color: isResult
          ? 0xffffff
          : selected
            ? 0xaacaca
            : fixed
              ? 0x6d957a
              : loaded
                ? 0xd9ac79
                : 0x658b7d,
        roughness: 0.43,
        metalness: 0.18,
        side: THREE.DoubleSide,
        vertexColors: !!isResult,
        emissive: selected ? 0x203e38 : 0x000000,
        emissiveIntensity: 0.2,
      });
      const mesh = new THREE.Mesh(g, mat);
      mesh.userData.faceId = face.id;
      meshes.push(mesh);
      scene.add(mesh);
      const edges = new THREE.LineSegments(
        new THREE.EdgesGeometry(g, 23),
        new THREE.LineBasicMaterial({
          color: 0x2c4d42,
          transparent: true,
          opacity: 0.42,
        }),
      );
      scene.add(edges);
      if (p.wireframe)
        scene.add(
          new THREE.LineSegments(
            new THREE.WireframeGeometry(g),
            new THREE.LineBasicMaterial({
              color: 0x173b32,
              transparent: true,
              opacity: 0.18,
            }),
          ),
        );
    }
    for (const [i, fid] of p.fixed.entries()) {
      const f = m.faces.find((f) => f.id === fid);
      if (!f) continue;
      const pin = label("F" + (i + 1) + " · FIXED");
      pin.position.set(...f.center);
      pin.position.z += span * 0.14;
      scene.add(pin);
    }
    for (const [i, l] of p.loads.entries()) {
      const f = m.faces.find((f) => f.id === l.face_id);
      if (!f) continue;
      const dir = new THREE.Vector3(...l.vector).normalize(),
        target = new THREE.Vector3(...f.center),
        origin = target.clone().addScaledVector(dir, -span * 0.35);
      scene.add(
        new THREE.ArrowHelper(
          dir,
          origin,
          span * 0.35,
          0xd4763c,
          span * 0.08,
          span * 0.035,
        ),
      );
      const pin = label(
        "L" + (i + 1) + " · " + format(Math.hypot(...l.vector)) + " N",
        "#a94f21",
      );
      pin.position.copy(origin).add(new THREE.Vector3(0, 0, span * 0.05));
      scene.add(pin);
    }
    const dimension = label(format(hi.x - lo.x) + " mm");
    dimension.position.set(center.x, lo.y - span * 0.18, lo.z);
    scene.add(dimension);
    const axes = new THREE.AxesHelper(span * 0.15);
    axes.position.set(lo.x - span * 0.25, lo.y - span * 0.25, lo.z);
    scene.add(axes);
    ["X", "Y", "Z"].forEach((s, i) => {
      const a = label(s, ["#ab5b4c", "#52815a", "#547ab0"][i]);
      a.scale.set(5, 3, 1);
      a.position.copy(axes.position);
      a.position.setComponent(i, a.position.getComponent(i) + span * 0.19);
      scene.add(a);
    });
    const ray = new THREE.Raycaster(),
      pointer = new THREE.Vector2();
    let down = { x: 0, y: 0 },
      hovered: THREE.Mesh | null = null;
    const pick = (e: PointerEvent) => {
      const b = renderer.domElement.getBoundingClientRect();
      pointer.set(
        ((e.clientX - b.left) / b.width) * 2 - 1,
        (-(e.clientY - b.top) / b.height) * 2 + 1,
      );
      ray.setFromCamera(pointer, cam);
      return ray.intersectObjects(meshes)[0]?.object as THREE.Mesh | undefined;
    };
    const move = (e: PointerEvent) => {
      const hit = pick(e);
      if (hovered && hovered !== hit) {
        (hovered.material as THREE.MeshStandardMaterial).emissive.setHex(
          hovered.userData.faceId === p.selected ? 0x203e38 : 0,
        );
      }
      if (hit)
        (hit.material as THREE.MeshStandardMaterial).emissive.setHex(0x284d43);
      hovered = hit || null;
      setHover(hit?.userData.faceId ?? null);
      renderer.domElement.style.cursor = hit ? "pointer" : "grab";
    };
    const pd = (e: PointerEvent) => {
      down = { x: e.clientX, y: e.clientY };
    };
    const pu = (e: PointerEvent) => {
      if (Math.hypot(e.clientX - down.x, e.clientY - down.y) < 5) {
        const hit = pick(e);
        if (hit) onSelect.current(hit.userData.faceId);
      }
    };
    renderer.domElement.addEventListener("pointermove", move);
    renderer.domElement.addEventListener("pointerdown", pd);
    renderer.domElement.addEventListener("pointerup", pu);
    const resize = () => {
      const w = container.clientWidth,
        h = container.clientHeight;
      renderer.setSize(w, h);
      const v = span * 0.68;
      cam.left = (-v * w) / h;
      cam.right = (v * w) / h;
      cam.top = v;
      cam.bottom = -v;
      cam.updateProjectionMatrix();
    };
    const ro = new ResizeObserver(resize);
    ro.observe(container);
    resize();
    let frame = 0;
    function draw() {
      frame = requestAnimationFrame(draw);
      controls.update();
      renderer.render(scene, cam);
    }
    draw();
    return () => {
      savedCamera.current = {
        position: cam.position.toArray() as Vec3,
        target: controls.target.toArray() as Vec3,
        zoom: cam.zoom,
        mid: m.id,
      };
      cancelAnimationFrame(frame);
      ro.disconnect();
      controls.dispose();
      scene.traverse((obj) => {
        const o = obj as THREE.Mesh;
        if (o.geometry) o.geometry.dispose();
        if (o.material) {
          const mats = Array.isArray(o.material) ? o.material : [o.material];
          mats.forEach((mat) => {
            const mp = (mat as THREE.MeshStandardMaterial).map;
            mp?.dispose();
            mat.dispose();
          });
        }
      });
      renderer.dispose();
      renderer.domElement.remove();
      sceneRef.current = undefined;
    };
  }, [
    p.model,
    p.result,
    p.fixed,
    p.loads,
    p.selected,
    p.field,
    p.deform,
    p.wireframe,
  ]);
  function capture() {
    const r = sceneRef.current?.renderer;
    if (!r) return;
    const a = document.createElement("a");
    a.download = "FEA-R-viewport.png";
    a.href = r.domElement.toDataURL("image/png");
    a.click();
  }
  return (
    <div className="viewport-wrap">
      <div className="viewport" ref={host} />
      <div className="viewport-top">
        <span className="viewport-label">
          <Box size={14} />
          {p.field === "solid"
            ? "SOLID GEOMETRY"
            : p.field === "stress"
              ? "VON MISES STRESS"
              : "TOTAL DISPLACEMENT"}
        </span>
        <span className="quiet">
          {p.model ? "Orthographic · mm" : "Preparing workspace"}
        </span>
      </div>
      {!p.model && (
        <div className="viewport-empty">
          <div className="orbit-loader" />
          <h3>Your next part starts here.</h3>
          <p>Building the example solid…</p>
        </div>
      )}
      {error && <div className="viewport-empty error">{error}</div>}
      <div className="viewport-controls">
        <button
          title="Reset view"
          aria-label="Reset view"
          onClick={() => sceneRef.current?.reset()}
        >
          <RotateCcw size={17} />
        </button>
        <button
          className={p.wireframe ? "active" : ""}
          title="Toggle mesh"
          aria-label="Toggle mesh"
          onClick={() => p.setWireframe(!p.wireframe)}
        >
          <Layers3 size={17} />
        </button>
        <button
          title="Save viewport PNG"
          aria-label="Save viewport PNG"
          onClick={capture}
        >
          <Camera size={17} />
        </button>
        <button
          title="Expand viewport"
          aria-label="Expand viewport"
          onClick={() => host.current?.parentElement?.requestFullscreen()}
        >
          <Maximize2 size={17} />
        </button>
      </div>
      <div className="viewport-footer">
        <span>
          {hover
            ? `Face ${hover} · ${p.model?.faces.find((f) => f.id === hover)?.label}`
            : "Drag to orbit · scroll to zoom · click a face"}
        </span>
        <span>{p.model?.tetrahedra.toLocaleString()} tetrahedra</span>
      </div>
      {p.result && p.field !== "solid" && (
        <div className="legend">
          <div>
            <b>{p.field === "stress" ? "Stress" : "Displacement"}</b>
            <span>{p.field === "stress" ? "MPa · nodal average" : "mm"}</span>
          </div>
          <div className="legend-bar" />
          <div>
            <span>0</span>
            <span>
              {format(
                p.field === "stress"
                  ? p.result.max_display_stress_mpa
                  : p.result.max_displacement_mm,
              )}
            </span>
          </div>
          {p.deform && (
            <small>
              Deformation ×
              {format(
                (Math.hypot(
                  ...p.model!.bounds[1].map(
                    (v, i) => v - p.model!.bounds[0][i],
                  ),
                ) *
                  0.06) /
                  p.result.max_displacement_mm,
              )}
            </small>
          )}
        </div>
      )}
    </div>
  );
}
