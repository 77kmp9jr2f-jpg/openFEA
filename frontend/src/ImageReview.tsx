import { useEffect, useRef, useState } from "react";
import {
  Upload,
  Camera,
  MousePointer2,
  MoveUpRight,
  Square,
  StickyNote,
  Ruler,
  Undo2,
  Redo2,
  Trash2,
  Check,
} from "lucide-react";
import type { Mark, ReferenceImage } from "./types";
type Props = {
  image: ReferenceImage | null;
  marks: Mark[];
  onChange: (marks: Mark[]) => void;
  upload: (file: File) => void;
  disabled: boolean;
};
export default function ImageReview({
  image,
  marks,
  onChange,
  upload,
  disabled,
}: Props) {
  const [tool, setTool] = useState<Mark["tool"] | "select">("arrow"),
    [drawing, setDrawing] = useState<Mark | null>(null),
    [selected, setSelected] = useState<string | null>(null),
    [past, setPast] = useState<Mark[][]>([]),
    [future, setFuture] = useState<Mark[][]>([]);
  const svg = useRef<SVGSVGElement>(null),
    file = useRef<HTMLInputElement>(null),
    camera = useRef<HTMLInputElement>(null);
  const canvas = useRef<HTMLDivElement>(null);
  const [fitted, setFitted] = useState({ width: 400, height: 300 });
  const moving = useRef<{
    mark: Mark;
    pointer: [number, number];
    before: Mark[];
  } | null>(null);
  const [cameraOpen, setCameraOpen] = useState(false),
    [cameraError, setCameraError] = useState("");
  const video = useRef<HTMLVideoElement>(null),
    stream = useRef<MediaStream | null>(null);
  useEffect(
    () => () => {
      stream.current?.getTracks().forEach((t) => t.stop());
    },
    [],
  );
  useEffect(() => {
    if (!canvas.current || !image) return;
    const element = canvas.current;
    const resize = () => {
      const scale = Math.min(
        (element.clientWidth - 28) / image.width,
        (element.clientHeight - 28) / image.height,
      );
      setFitted({ width: image.width * scale, height: image.height * scale });
    };
    const observer = new ResizeObserver(resize);
    observer.observe(element);
    resize();
    return () => observer.disconnect();
  }, [image]);
  function commit(next: Mark[]) {
    if (disabled) return;
    setPast((p) => [...p.slice(-39), marks]);
    setFuture([]);
    onChange(next);
  }
  function pos(e: React.PointerEvent): [number, number] {
    const b = svg.current!.getBoundingClientRect();
    return [
      Math.max(0, Math.min(1, (e.clientX - b.left) / b.width)),
      Math.max(0, Math.min(1, (e.clientY - b.top) / b.height)),
    ];
  }
  function start(e: React.PointerEvent) {
    if (disabled || tool === "select") return;
    const pt = pos(e);
    const m: Mark = {
      id: crypto.randomUUID(),
      tool,
      start: pt,
      end: pt,
      text: "",
    };
    setDrawing(m);
    svg.current?.setPointerCapture(e.pointerId);
  }
  function end(e: React.PointerEvent) {
    if (disabled) {
      setDrawing(null);
      moving.current = null;
      return;
    }
    if (moving.current) {
      const beforeMove = moving.current.before;
      setPast((p) => [...p.slice(-39), beforeMove]);
      setFuture([]);
      moving.current = null;
      return;
    }
    if (!drawing) return;
    const m = { ...drawing, end: pos(e) };
    commit([...marks, m]);
    setSelected(m.id);
    setDrawing(null);
  }
  function move(e: React.PointerEvent) {
    if (disabled) return;
    if (drawing) setDrawing({ ...drawing, end: pos(e) });
    if (!moving.current) return;
    const { mark, pointer, before } = moving.current,
      current = pos(e);
    const dx = Math.max(
      -Math.min(mark.start[0], mark.end[0]),
      Math.min(
        1 - Math.max(mark.start[0], mark.end[0]),
        current[0] - pointer[0],
      ),
    );
    const dy = Math.max(
      -Math.min(mark.start[1], mark.end[1]),
      Math.min(
        1 - Math.max(mark.start[1], mark.end[1]),
        current[1] - pointer[1],
      ),
    );
    onChange(
      before.map((m) =>
        m.id === mark.id
          ? {
              ...m,
              start: [mark.start[0] + dx, mark.start[1] + dy],
              end: [mark.end[0] + dx, mark.end[1] + dy],
            }
          : m,
      ),
    );
  }
  async function startCamera() {
    setCameraError("");
    setCameraOpen(true);
    try {
      const captured = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: "environment" },
        audio: false,
      });
      if (!video.current) {
        captured.getTracks().forEach((t) => t.stop());
        return;
      }
      stream.current = captured;
      if (video.current) {
        video.current.srcObject = stream.current;
        await video.current.play();
      }
    } catch {
      setCameraError(
        "Camera access is unavailable. Use the photo picker to take or upload a photo.",
      );
    }
  }
  function stopCamera() {
    stream.current?.getTracks().forEach((t) => t.stop());
    stream.current = null;
    setCameraOpen(false);
  }
  function snap() {
    if (!video.current) return;
    const v = video.current,
      c = document.createElement("canvas");
    c.width = v.videoWidth;
    c.height = v.videoHeight;
    c.getContext("2d")!.drawImage(v, 0, 0);
    c.toBlob(
      (b) => {
        if (b)
          upload(new File([b], "camera-reference.jpg", { type: "image/jpeg" }));
        stopCamera();
      },
      "image/jpeg",
      0.92,
    );
  }
  const chosen = marks.find((m) => m.id === selected);
  const icons = {
    arrow: MoveUpRight,
    rectangle: Square,
    note: StickyNote,
    dimension: Ruler,
  };
  return (
    <fieldset
      className="image-review"
      disabled={disabled}
      aria-label="Reference annotations"
    >
      <div className="image-toolbar">
        <div>
          {(["select", "arrow", "rectangle", "note", "dimension"] as const).map(
            (t) => {
              const Icon = t === "select" ? MousePointer2 : icons[t];
              return (
                <button
                  key={t}
                  aria-label={t + " annotation tool"}
                  title={t}
                  className={tool === t ? "active" : ""}
                  onClick={() => setTool(t)}
                >
                  <Icon size={17} />
                </button>
              );
            },
          )}
          <i />
          <button
            title="Undo annotation"
            aria-label="Undo annotation"
            disabled={!past.length}
            onClick={() => {
              setFuture((f) => [marks, ...f]);
              onChange(past[past.length - 1]);
              setPast((p) => p.slice(0, -1));
            }}
          >
            <Undo2 size={17} />
          </button>
          <button
            title="Redo annotation"
            aria-label="Redo annotation"
            disabled={!future.length}
            onClick={() => {
              setPast((p) => [...p, marks]);
              onChange(future[0]);
              setFuture((f) => f.slice(1));
            }}
          >
            <Redo2 size={17} />
          </button>
        </div>
        <span>REFERENCE STUDIO</span>
        <div>
          <button
            title="Upload reference"
            aria-label="Upload reference"
            onClick={() => file.current?.click()}
          >
            <Upload size={17} />
          </button>
          <button
            title="Capture with camera"
            aria-label="Capture with camera"
            onClick={startCamera}
          >
            <Camera size={17} />
          </button>
        </div>
      </div>
      <input
        ref={file}
        type="file"
        accept="image/png,image/jpeg,image/webp"
        hidden
        onChange={(e) => {
          const f = e.target.files?.[0];
          if (f) upload(f);
          e.target.value = "";
        }}
      />
      <input
        ref={camera}
        type="file"
        accept="image/*"
        capture="environment"
        hidden
        onChange={(e) => {
          const f = e.target.files?.[0];
          if (f) upload(f);
        }}
      />
      <div
        ref={canvas}
        className="image-canvas"
        onDragOver={(e) => e.preventDefault()}
        onDrop={(e) => {
          e.preventDefault();
          if (disabled) return;
          const f = e.dataTransfer.files[0];
          if (f) upload(f);
        }}
      >
        {image ? (
          <div
            className="image-fit"
            style={{ width: fitted.width, height: fitted.height }}
          >
            <img src={image.url} alt={image.name} />
            <svg
              ref={svg}
              viewBox={`0 0 1000 ${(1000 * image.height) / image.width}`}
              onPointerDown={start}
              onPointerMove={move}
              onPointerUp={end}
              onPointerCancel={() => {
                setDrawing(null);
                if (moving.current && !disabled) onChange(moving.current.before);
                moving.current = null;
              }}
              style={{ cursor: tool === "select" ? "default" : "crosshair" }}
            >
              <defs>
                <marker
                  id="arrowhead"
                  markerWidth="9"
                  markerHeight="9"
                  refX="7"
                  refY="4.5"
                  orient="auto-start-reverse"
                >
                  <path
                    d="M0,0 L9,4.5 L0,9"
                    fill="none"
                    stroke="#d77042"
                    strokeWidth="1.7"
                  />
                </marker>
              </defs>
              {[...marks, ...(drawing ? [drawing] : [])].map((m, i) => {
                const x = m.start[0] * 1000,
                  y = (m.start[1] * 1000 * image.height) / image.width,
                  ex = m.end[0] * 1000,
                  ey = (m.end[1] * 1000 * image.height) / image.width;
                return (
                  <g
                    key={m.id}
                    role="button"
                    tabIndex={0}
                    aria-label={`Annotation ${i + 1}: ${m.text || m.tool}`}
                    onKeyDown={(e) => {
                      if (!disabled && e.key === "Enter") setSelected(m.id);
                    }}
                    stroke="#d77042"
                    strokeWidth="3"
                    fill="none"
                    onPointerDown={(e) => {
                      if (tool === "select" && !disabled) {
                        e.stopPropagation();
                        setSelected(m.id);
                        moving.current = {
                          mark: m,
                          pointer: pos(e),
                          before: marks,
                        };
                        svg.current?.setPointerCapture(e.pointerId);
                      }
                    }}
                    style={{
                      cursor: tool === "select" ? "pointer" : undefined,
                    }}
                  >
                    {m.tool === "rectangle" ? (
                      <rect
                        x={Math.min(x, ex)}
                        y={Math.min(y, ey)}
                        width={Math.abs(ex - x)}
                        height={Math.abs(ey - y)}
                        fill="#d7704212"
                      />
                    ) : m.tool === "note" ? (
                      <circle cx={x} cy={y} r="15" fill="#d77042" />
                    ) : (
                      <line
                        x1={x}
                        y1={y}
                        x2={ex}
                        y2={ey}
                        markerEnd="url(#arrowhead)"
                        markerStart={
                          m.tool === "dimension" ? "url(#arrowhead)" : undefined
                        }
                      />
                    )}
                    <circle
                      cx={x}
                      cy={y}
                      r="12"
                      fill={m.id === selected ? "#244a3c" : "#d77042"}
                      stroke="white"
                      strokeWidth="2"
                    />
                    <text
                      x={x}
                      y={y + 4}
                      textAnchor="middle"
                      fontSize="12"
                      fill="white"
                      stroke="none"
                    >
                      {i + 1}
                    </text>
                    {m.text && (
                      <text
                        x={x + 18}
                        y={y - 15}
                        fontSize="18"
                        fill="#9e431e"
                        stroke="white"
                        strokeWidth="4"
                        paintOrder="stroke"
                      >
                        {m.text}
                      </text>
                    )}
                  </g>
                );
              })}
            </svg>
          </div>
        ) : (
          <div className="upload-empty">
            <div className="upload-glyph">
              <BoxIllustration />
            </div>
            <h2>From a photo to a part.</h2>
            <p>
              Drop a reference image. Mark the dimensions and details that
              matter, then work through the design with Astra.
            </p>
            <button className="primary" onClick={() => file.current?.click()}>
              <Upload size={16} /> Choose an image
            </button>
            <button className="text-button" onClick={startCamera}>
              <Camera size={15} /> Take a photo
            </button>
            <button
              className="text-button"
              onClick={async () => {
                const response = await fetch("/demo-reference.png");
                upload(
                  new File([await response.blob()], "demo-reference.png", {
                    type: "image/png",
                  }),
                );
              }}
            >
              Use synthetic example reference
            </button>
            <small>
              PNG, JPG, WebP · a known dimension helps establish scale
            </small>
          </div>
        )}
      </div>
      {image && (
        <div className="annotation-bottom">
          <div>
            <b>{image.name}</b>
            <span>{marks.length} annotations · saved with this study</span>
          </div>
          <button className="text-button" onClick={() => file.current?.click()}>
            Replace image
          </button>
        </div>
      )}
      {chosen && (
        <div className="mark-editor">
          <span className="mark-number">
            {marks.findIndex((m) => m.id === selected) + 1}
          </span>
          <input
            aria-label="Annotation note"
            placeholder={
              chosen.tool === "dimension"
                ? "Enter measured dimension, e.g. 80 mm"
                : "Describe this detail for Astra…"
            }
            value={chosen.text}
            onChange={(e) =>
              onChange(
                marks.map((m) =>
                  m.id === selected ? { ...m, text: e.target.value } : m,
                ),
              )
            }
          />
          <button
            title="Delete annotation"
            aria-label="Delete annotation"
            onClick={() => {
              commit(marks.filter((m) => m.id !== selected));
              setSelected(null);
            }}
          >
            <Trash2 size={16} />
          </button>
          <button
            title="Done annotation"
            aria-label="Done annotation"
            onClick={() => setSelected(null)}
          >
            <Check size={17} />
          </button>
        </div>
      )}
      {cameraOpen && (
        <div className="modal-backdrop">
          <div className="camera-modal">
            <h2>Capture a reference</h2>
            <video ref={video} autoPlay playsInline muted />
            {cameraError && <p>{cameraError}</p>}
            <div>
              <button onClick={stopCamera}>Cancel</button>
              {cameraError ? (
                <button
                  className="primary"
                  onClick={() => {
                    stopCamera();
                    camera.current?.click();
                  }}
                >
                  Open photo picker
                </button>
              ) : (
                <button className="primary" onClick={snap}>
                  <Camera size={16} /> Capture photo
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </fieldset>
  );
}
function BoxIllustration() {
  return (
    <svg width="92" height="92" viewBox="0 0 92 92" fill="none">
      <path
        d="M20 35 46 20 72 35 46 50Z M20 35V65L46 80 72 65V35 M46 50V80"
        stroke="currentColor"
        strokeWidth="1.5"
      />
      <path d="M20 35 46 50 72 35" stroke="currentColor" />
      <path
        d="M10 20V10H20 M72 10H82V20 M10 72V82H20 M72 82H82V72"
        stroke="currentColor"
        opacity=".4"
      />
    </svg>
  );
}
