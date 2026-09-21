import { useEffect, useRef, useState } from "react";
import {
  ArrowDownToLine,
  ArrowRight,
  ArrowUp,
  Box,
  Check,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  CircleHelp,
  Copy,
  FileText,
  FolderOpen,
  Image as ImageIcon,
  Layers3,
  Loader2,
  MoreHorizontal,
  MoveUpRight,
  Play,
  Plus,
  Printer,
  Save,
  Settings2,
  ShieldCheck,
  Sparkles,
  Trash2,
  X,
  Zap,
} from "lucide-react";
import Viewport from "./Viewport";
import {
  gpuCapability,
  solveGPU,
  type GPUSystem,
  type GPUCapability,
} from "./gpu";
import ImageReview from "./ImageReview";
import SetupProposalCard from "./SetupProposalCard";
import PrintWorkspace from "./PrintWorkspace";
import CompareTable from "./CompareTable";
import ResultGuidance from "./ResultGuidance";
import ReadinessPanel from "./ReadinessPanel";
import {
  api,
  job,
  demoGeometry,
  materials,
  format,
  contextKey,
  normalizeGeometry,
  defaultPrint,
} from "./types";
import type {
  Geometry,
  Model,
  Result,
  Material,
  Load,
  Vec3,
  ReferenceImage,
  Mark,
  Message,
  SimulationContext,
  SimulationProposal,
  AppliedSetup,
  PrintSettings,
  PrintPreview,
  StlInspect,
  RunCompare,
  Readiness,
} from "./types";

type Tab = "reference" | "model" | "print" | "setup" | "results";
type Saved = {
  spec: Geometry;
  modelId?: string;
  resultId?: string;
  pinnedId?: string;
  material: Material;
  fixed: number[];
  loads: Load[];
  image: ReferenceImage | null;
  marks: Mark[];
  messages: Message[];
  notes: string;
  setupProposalId?: string | null;
  print?: PrintSettings;
};
const intro: Message = {
  role: "assistant",
  text: "Let’s give your design a little more certainty. Add a photo or start with this example, then tell me what the part needs to do.",
  questions: [
    "What dimensions are known?",
    "How is it held, and where does the force act?",
  ],
  live: false,
};
const firstAnalysisIntro: Message = {
  role: "assistant",
  text: "This example coupon has labelled demonstration conditions. Run the simulation, then change infill, review and confirm the setup, and run again. Check mesh convergence before interpreting displacement; the print model is not calibrated strength.",
  live: false,
};
export default function App() {
  const [spec, setSpec] = useState<Geometry>({ ...demoGeometry }),
    [model, setModel] = useState<Model | null>(null),
    [result, setResult] = useState<Result | null>(null),
    [material, setMaterial] = useState<Material>(materials[0]);
  const [fixed, setFixed] = useState<number[]>([]),
    [loads, setLoads] = useState<Load[]>([]),
    [selected, setSelected] = useState<number | null>(null),
    [vector, setVector] = useState<Vec3>([0, 0, -100]),
    [confirmed, setConfirmed] = useState(false);
  const [tab, setTab] = useState<Tab>("model"),
    [field, setField] = useState<"solid" | "stress" | "displacement">("solid"),
    [deform, setDeform] = useState(false),
    [wireframe, setWireframe] = useState(false);
  const [image, setImage] = useState<ReferenceImage | null>(null),
    [marks, setMarks] = useState<Mark[]>([]),
    [messages, setMessages] = useState<Message[]>([intro]),
    [prompt, setPrompt] = useState(""),
    [notes, setNotes] = useState("");
  const [print, setPrint] = useState<PrintSettings>({ ...defaultPrint });
  const [printPreview, setPrintPreview] = useState<PrintPreview | null>(null);
  const [stlInspect, setStlInspect] = useState<StlInspect | null>(null);
  const [pinned, setPinned] = useState<Result | null>(null);
  const [compare, setCompare] = useState<RunCompare | null>(null);
  const [busy, setBusy] = useState(""),
    [aiBusy, setAiBusy] = useState(false),
    [status, setStatus] = useState("Starting local engine"),
    [aiAvailable, setAiAvailable] = useState(false),
    [toast, setToast] = useState(""),
    [error, setError] = useState(""),
    [ready, setReady] = useState(false);
  const [library, setLibrary] = useState<
      { id: string; name: string; updated_at: number }[] | null
    >(null),
    [help, setHelp] = useState(false),
    [featureText, setFeatureText] = useState(""),
    [featureError, setFeatureError] = useState("");
  const [compute, setCompute] = useState<"webgpu" | "cpu">("cpu");
  const [readiness, setReadiness] = useState<Readiness | null>(null);
  const [setupPreview, setSetupPreview] = useState<SimulationProposal | null>(
    null,
  );
  const [setupProposalId, setSetupProposalId] = useState<string | null>(null);
  const [gpu, setGpu] = useState<GPUCapability>({
    available: false,
    device: "Checking local GPU…",
  });
  useEffect(() => {
    gpuCapability().then(setGpu);
  }, []);
  const operation = useRef<AbortController | null>(null);
  const started = useRef(false),
    stepFile = useRef<HTMLInputElement>(null),
    stlFile = useRef<HTMLInputElement>(null),
    stageElement = useRef<HTMLDivElement>(null),
    chatEnd = useRef<HTMLDivElement>(null);
  const dirty =
    !!model &&
    contextKey(normalizeGeometry(spec)) !==
      contextKey(normalizeGeometry(model.spec));
  const simulationContext: SimulationContext | null = model
    ? {
        model_id: model.id,
        geometry: normalizeGeometry(spec),
        print,
        material,
        fixed_faces: fixed,
        loads,
        notes,
        reference_id: image?.id || null,
        annotations: marks,
      }
    : null;
  function proposalCurrent(proposal: SimulationProposal) {
    return (
      !dirty &&
      !!simulationContext &&
      contextKey(simulationContext) === contextKey(proposal.source_context)
    );
  }
  const previewing =
    tab === "setup" && !!setupPreview && proposalCurrent(setupPreview);
  useEffect(() => {
    if (previewing)
      stageElement.current?.scrollIntoView({
        behavior: "instant",
        block: "start",
      });
  }, [previewing]);
  function flash(text: string) {
    setToast(text);
    setTimeout(() => setToast(""), 4500);
  }
  function invalidate() {
    setConfirmed(false);
    setResult(null);
    setField("solid");
    setSetupPreview(null);
    setSetupProposalId(null);
    setCompare(null);
  }
  function updateSpec(patch: Partial<Geometry>) {
    setSpec((s) => ({
      ...s,
      ...patch,
      provenance: s.provenance === "demo" ? "user_dimensions" : s.provenance,
    }));
    invalidate();
  }
  function snapshot(): Saved {
    return {
      spec,
      modelId: model?.id,
      resultId: result?.id,
      pinnedId: pinned?.id,
      material,
      fixed,
      loads,
      image,
      marks,
      messages,
      notes,
      setupProposalId,
      print,
    };
  }
  async function restore(s: Saved) {
    setSpec(normalizeGeometry(s.spec));
    setMaterial(s.material);
    setFixed(s.fixed || []);
    setLoads(s.loads || []);
    setImage(s.image);
    setMarks(s.marks || []);
    setMessages(s.messages || [intro]);
    setNotes(s.notes || "");
    setSetupProposalId(s.setupProposalId || null);
    setPrint(s.print || { ...defaultPrint });
    setSetupPreview(null);
    setSelected(null);
    setConfirmed(false);
    setResult(null);
    setModel(null);
    setPinned(null);
    setCompare(null);
    setStlInspect(null);
    setField("solid");
    if (s.spec.kind === "stl" && s.spec.stl_id)
      setStlInspect(
        await api<StlInspect>(
          `/stls/${s.spec.stl_id}?scale=${s.spec.unit_scale}`,
        ),
      );
    if (s.pinnedId) setPinned(await api<Result>("/runs/" + s.pinnedId));
    if (s.modelId) {
      const m = await api<Model>("/models/" + s.modelId);
      setModel(m);
    }
    if (s.resultId && s.modelId) {
      const r = await api<Result>("/runs/" + s.resultId);
      if (r.model_id === s.modelId) setResult(r);
    }
  }
  async function build(
    next = spec,
    options:
      | { demo?: boolean; applyRecommended?: boolean; firstAnalysis?: boolean }
      | boolean = false,
  ) {
    const flags = typeof options === "boolean" ? { demo: options } : options;
    const controller = new AbortController();
    operation.current = controller;
    setBusy("Building solid & mesh");
    setError("");
    invalidate();
    try {
      const m = await job<Model>("/models", next, undefined, controller.signal);
      setModel(m);
      setSpec(m.spec);
      const preset = flags.demo || flags.firstAnalysis;
      setFixed(preset ? [m.recommended.fixed_face] : []);
      setLoads(
        preset
          ? [
              {
                face_id: m.recommended.load_face,
                vector: [0, 0, flags.demo ? -100 : -40],
              },
            ]
          : [],
      );
      setSelected(null);
      if (flags.firstAnalysis) setTab("print");
      else if (flags.applyRecommended)
        setTab(next.kind === "stl" ? "print" : "setup");
      else setTab("model");
      if (flags.firstAnalysis) setConfirmed(true);
      if (flags.firstAnalysis) {
        setCompute("cpu");
        setMessages([firstAnalysisIntro]);
      } else {
        setMessages((messages) =>
          messages.some((message) => message.interviewFor === m.id)
            ? messages
            : [
                ...messages,
                {
                  role: "assistant",
                  live: false,
                  interviewFor: m.id,
                  text: "Your solid and mesh are ready. Next, let’s describe how the part is used so Astra can propose the simulation setup.",
                  questions: [
                    "Which material properties should we use?",
                    "How is it attached or held? Select a face if that helps.",
                    "Where does the load act, and what is its magnitude and global X/Y/Z direction?",
                  ],
                },
              ],
        );
      }
      flash(`${m.tetrahedra.toLocaleString()} tetrahedra · solid ready`);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      operation.current = null;
      setBusy("");
    }
  }
  useEffect(() => {
    if (started.current) return;
    started.current = true;
    (async () => {
      try {
        const h = await api<{ assistant: { available: boolean } }>("/health");
        setAiAvailable(h.assistant.available);
        setStatus("Local engine ready");
        const saved =
          localStorage.getItem("openfea-current") ||
          localStorage.getItem("fea-r-current");
        if (saved) {
          try {
            await restore(JSON.parse(saved));
          } catch {
            localStorage.removeItem("openfea-current");
            localStorage.removeItem("fea-r-current");
            await startFirstAnalysis();
          }
        } else await startFirstAnalysis();
      } catch (e) {
        setError((e as Error).message);
        setStatus("Local engine offline");
      } finally {
        setReady(true);
      }
    })();
  }, []);
  useEffect(() => {
    if (!ready) return;
    const t = setTimeout(() => {
      try {
        localStorage.setItem("openfea-current", JSON.stringify(snapshot()));
        localStorage.removeItem("fea-r-current");
      } catch {
        setError(
          "Browser storage is full. Save a study to preserve this work.",
        );
      }
    }, 350);
    return () => clearTimeout(t);
  }, [
    spec,
    model,
    result,
    material,
    fixed,
    loads,
    image,
    marks,
    messages,
    notes,
    setupProposalId,
    print,
    pinned,
    ready,
  ]);
  useEffect(() => {
    chatEnd.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [messages, aiBusy]);
  useEffect(() => {
    if (!model || !print.enabled) {
      setPrintPreview(null);
      return;
    }
    let cancelled = false;
    api<PrintPreview>("/print-preview", {
      model_id: model.id,
      material,
      print,
    })
      .then((value) => {
        if (!cancelled) setPrintPreview(value);
      })
      .catch(() => {
        if (!cancelled) setPrintPreview(null);
      });
    return () => {
      cancelled = true;
    };
  }, [model, material, print]);
  useEffect(() => {
    if (!pinned || !result || pinned.id === result.id) {
      setCompare(null);
      return;
    }
    api<RunCompare>(`/runs/${pinned.id}/compare/${result.id}`)
      .then(setCompare)
      .catch(() => setCompare(null));
  }, [pinned, result]);
  useEffect(() => {
    if (!model || dirty) {
      setReadiness(null);
      return;
    }
    let cancelled = false;
    api<Readiness>("/readiness", {
      model_id: model.id,
      material,
      fixed_faces: fixed,
      loads,
      confirmed,
      print,
    })
      .then((value) => {
        if (!cancelled) setReadiness(value);
      })
      .catch(() => {
        if (!cancelled) setReadiness(null);
      });
    return () => {
      cancelled = true;
    };
  }, [model, dirty, material, fixed, loads, confirmed, print]);
  async function upload(file: File) {
    if (busy) return;
    setBusy("Importing reference");
    setError("");
    try {
      const data = await new Promise<string>((resolve, reject) => {
        const r = new FileReader();
        r.onload = () => resolve(r.result as string);
        r.onerror = reject;
        r.readAsDataURL(file);
      });
      const img = await api<ReferenceImage>("/images", {
        name: file.name,
        data_url: data,
      });
      setImage(img);
      setMarks([]);
      invalidate();
      setTab("reference");
      flash(
        "Reference ready. Annotate a known dimension or ask Astra to inspect it.",
      );
    } catch (e) {
      setError((e as Error).message);
    } finally {
      operation.current = null;
      setBusy("");
    }
  }
  async function importStep(file: File) {
    setBusy("Importing STEP");
    setError("");
    try {
      if (file.size > 80_000_000) {
        throw new Error(
          "This STEP file is over 80 MB. Export a simpler solid.",
        );
      }
      const res = await fetch("/api/steps", {
        method: "POST",
        headers: { "Content-Type": "application/octet-stream" },
        body: file,
      });
      const body = await res.json();
      if (!res.ok) throw new Error(body.detail);
      const s = {
        ...spec,
        kind: "step" as const,
        name: file.name.replace(/\.(step|stp)$/i, ""),
        step_id: body.id,
        provenance: "step_import",
        assumptions: ["STEP units converted to mm; verify model bounds."],
      };
      setSpec(s);
      await build(s, { applyRecommended: true });
    } catch (e) {
      setError((e as Error).message);
    } finally {
      operation.current = null;
      setBusy("");
    }
  }
  async function startFirstAnalysis() {
    setCompute("cpu");
    try {
      const response = await fetch("/print-coupon.stl");
      if (!response.ok) throw new Error("The example coupon is missing.");
      await importStl(
        new File([await response.blob()], "print-coupon.stl", {
          type: "model/stl",
        }),
        { firstAnalysis: true },
      );
    } catch (e) {
      setError((e as Error).message);
      await build(demoGeometry, true);
    }
  }
  async function importStl(
    file: File,
    options: { firstAnalysis?: boolean } = {},
  ) {
    setBusy("Inspecting STL");
    setError("");
    try {
      if (file.size > 80_000_000) {
        throw new Error(
          "This STL is over 80 MB. Export a binary STL from CAD, or a coarser tessellation.",
        );
      }
      const res = await fetch("/api/stls", {
        method: "POST",
        headers: {
          "Content-Type": "application/octet-stream",
          "X-Filename": file.name,
        },
        body: file,
      });
      const body = await res.json();
      if (!res.ok) throw new Error(body.detail);
      setStlInspect(body);
      const extent = Math.max(...(body.extent_mm || [0]));
      const meshSize = Math.min(
        40,
        Math.max(spec.mesh_size, Math.round(extent / 25) || spec.mesh_size),
      );
      const s: Geometry = {
        ...spec,
        kind: "stl",
        name: file.name.replace(/\.stl$/i, ""),
        stl_id: body.id,
        unit_scale: 1,
        accept_stl_preprocessing: false,
        mesh_size: meshSize,
        provenance: "stl_import",
        assumptions: body.warnings,
      };
      setSpec(s);
      setPrint((current) => ({ ...current, enabled: true }));
      invalidate();
      setModel(null);
      setFixed([]);
      setLoads([]);
      if (options.firstAnalysis && materials[3])
        setMaterial({ ...materials[3] });
      if (!body.watertight) {
        setTab("model");
        flash("STL inspected. Repair watertightness before meshing.");
        return;
      }
      if (!options.firstAnalysis) {
        setTab("model");
        flash(
          "Review STL dimensions, units and preprocessing, then build the model and define its real supports and loads.",
        );
        return;
      }
      await build(s, {
        applyRecommended: true,
        firstAnalysis: options.firstAnalysis,
      });
      flash(
        options.firstAnalysis
          ? "Example coupon ready. Run on this computer, then change infill and run again."
          : "STL meshed. Print settings and end-face supports/loads are ready for review.",
      );
    } catch (e) {
      setError((e as Error).message);
    } finally {
      operation.current = null;
      setBusy("");
    }
  }
  async function ask(
    text = prompt,
    stage?: "geometry" | "loading" | "results",
  ) {
    if (!text.trim() || aiBusy) return;
    setPrompt("");
    setAiBusy(true);
    setError("");
    const history = messages
      .slice(-10)
      .map((m) => ({ role: m.role, content: m.text }));
    setMessages((m) => [...m, { role: "user", text }]);
    try {
      const answer = await job<{
        message: string;
        questions: string[];
        proposal: Geometry | null;
        simulation_proposal: SimulationProposal | null;
        live: boolean;
      }>("/assistant", {
        message: text,
        image_id: image?.id || null,
        annotations: marks,
        geometry: spec,
        history,
        model_id: model?.id || null,
        material,
        print,
        fixed_faces: fixed,
        loads,
        application_notes: notes,
        run_id: result?.id || null,
        selected_face: selected,
        stage:
          stage ||
          (tab === "setup" || tab === "print"
            ? "loading"
            : tab === "results"
              ? "results"
              : "geometry"),
      });
      setMessages((m) => [
        ...m,
        {
          role: "assistant",
          text: answer.message,
          questions: answer.questions,
          proposal: answer.proposal || undefined,
          simulation_proposal: answer.simulation_proposal || undefined,
          live: answer.live,
        },
      ]);
    } catch (e) {
      setError((e as Error).message);
      setMessages((m) => [
        ...m,
        { role: "assistant", text: (e as Error).message, live: false },
      ]);
    } finally {
      setAiBusy(false);
    }
  }
  function startInterview() {
    setTab("setup");
    setField("solid");
    ask(
      "Help me define the simulation for this built part. Interview me about the material, how it is held, and the magnitude, global direction and location of the loads. Ask only for missing inputs before proposing a complete setup.",
      "loading",
    );
  }
  async function applySimulation(proposal: SimulationProposal) {
    if (!simulationContext || !proposalCurrent(proposal) || busy) return;
    setBusy("Applying reviewed setup");
    setError("");
    try {
      const applied = await api<AppliedSetup>(
        `/setup-proposals/${proposal.id}/apply`,
        simulationContext,
      );
      invalidate();
      setMaterial(applied.material);
      setPrint(applied.print);
      setFixed(applied.fixed_faces);
      setLoads(applied.loads);
      setNotes(applied.notes);
      setSetupProposalId(applied.setup_proposal_id);
      setTab("setup");
      flash(
        "Astra’s setup applied. Review the model and confirm before running.",
      );
    } catch (e) {
      setError((e as Error).message);
    } finally {
      operation.current = null;
      setBusy("");
    }
  }
  async function solve() {
    if (!model || dirty) return;
    const controller = new AbortController();
    operation.current = controller;
    setBusy("Solving 3D elasticity");
    setError("");
    try {
      const setup = {
        model_id: model.id,
        material,
        fixed_faces: fixed,
        loads,
        confirmed,
        notes,
        reference_id: image?.id || null,
        annotations: marks,
        setup_proposal_id: setupProposalId,
        conversation: messages
          .slice(-24)
          .map(({ role, text, live }) => ({ role, text, live: !!live })),
        print,
      };
      let r: Result;
      if (compute === "webgpu") {
        setBusy("Assembling finite-element system");
        const system = await job<GPUSystem>(
          "/gpu/prepare",
          setup,
          undefined,
          controller.signal,
        );
        setBusy("Starting local GPU solver");
        const solution = await solveGPU(system, setBusy, controller.signal);
        setBusy("Verifying residual & calculating stress");
        r = await job<Result>(
          "/gpu/finish",
          solution,
          undefined,
          controller.signal,
        );
      } else
        r = await job<Result>("/solve", setup, undefined, controller.signal);
      setResult(r);
      setTab("results");
      setField(r.print?.enabled ? "displacement" : "stress");
      setDeform(false);
      if (r.print?.enabled && !pinned) {
        setPinned(r);
        flash(
          `Analysis complete in ${format(r.seconds)} s. This run is pinned — change infill and run again.`,
        );
      } else flash(`Analysis complete in ${format(r.seconds)} s`);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      operation.current = null;
      setBusy("");
    }
  }
  async function save() {
    try {
      await api("/studies", { name: spec.name, state: snapshot() });
      flash("Study snapshot saved on this computer.");
    } catch (e) {
      setError((e as Error).message);
    }
  }
  async function openLibrary() {
    try {
      setLibrary(await api("/studies"));
    } catch (e) {
      setError((e as Error).message);
    }
  }
  const face = model?.faces.find((f) => f.id === selected),
    canSolve =
      !!model &&
      !dirty &&
      !!fixed.length &&
      !!loads.length &&
      confirmed &&
      !previewing &&
      (compute === "cpu" || gpu.available) &&
      !busy;
  const steps: [Tab, string, typeof Box][] = [
    ["reference", "Reference", ImageIcon],
    ["model", "Model", Box],
    ["print", "Print", Printer],
    ["setup", "Simulation", Settings2],
    ["results", "Results", Layers3],
  ];
  function changeSetup(fn: () => void) {
    fn();
    invalidate();
  }
  function applyRecommendedSetup() {
    if (!model) return;
    invalidate();
    const suggested = readiness?.recommended.loads[0]?.vector || vector;
    setFixed(
      readiness?.recommended.fixed_faces.length
        ? readiness.recommended.fixed_faces
        : [model.recommended.fixed_face],
    );
    setLoads([
      {
        face_id:
          readiness?.recommended.loads[0]?.face_id ||
          model.recommended.load_face,
        vector: suggested,
      },
    ]);
    setSelected(null);
  }
  return (
    <div className="app-shell">
      <header className="topbar">
        <a className="brand" href="/" aria-label="OpenFEA home">
          <span className="brand-mark">
            <Box size={24} strokeWidth={1.6} />
          </span>
          <b>OpenFEA</b>
          <span className="beta">WORKSPACE</span>
        </a>
        <div className="top-center">
          <span>Studies</span>
          <ChevronRight size={13} />
          <strong>{spec.name}</strong>
          <span className="small-tag">Local</span>
        </div>
        <div className="top-actions">
          <button
            className="icon-button"
            aria-label="Help"
            onClick={() => setHelp(true)}
          >
            <CircleHelp size={18} />
          </button>
          <button className="subtle-button" onClick={save} disabled={!!busy}>
            <Save size={15} /> Save study
          </button>
          <button
            className="avatar"
            onClick={openLibrary}
            title="Saved studies"
          >
            Z
          </button>
        </div>
      </header>
      <aside className="sidebar">
        <div className="sidebar-heading">
          <span>DESIGN EXPLORER</span>
          <button aria-label="Saved studies" onClick={openLibrary}>
            <FolderOpen size={16} />
          </button>
        </div>
        <button className="study-item" onClick={() => setTab("model")}>
          <span className="study-icon">
            <Box size={20} />
          </span>
          <span>
            <b>{spec.name}</b>
            <small>
              {spec.kind === "step"
                ? "Imported solid"
                : spec.kind === "stl"
                  ? "Imported mesh"
                  : "Parametric part"}{" "}
              · rev {model?.id.slice(0, 4) || "—"}
            </small>
          </span>
          <MoreHorizontal size={16} />
        </button>
        <nav className="tree-nav">
          {steps.map(([key, label, Icon], i) => (
            <button
              key={key}
              className={tab === key ? "active" : ""}
              onClick={() => {
                setTab(key);
                if (key === "results" && result) setField("stress");
                else if (key !== "results") setField("solid");
              }}
            >
              <span className="step-number">0{i + 1}</span>
              <Icon size={16} />
              <span>{label}</span>
              {(key === "reference"
                ? !!image
                : key === "model"
                  ? !!model && !dirty
                  : key === "print"
                    ? print.enabled
                    : key === "setup"
                      ? fixed.length > 0 && loads.length > 0
                      : !!result) && <Check size={13} className="nav-check" />}
            </button>
          ))}
        </nav>
        <div className="sidebar-rule" />
        <fieldset disabled={!!busy} className="properties">
          <div className="section-label">
            {tab === "setup" ? "MATERIAL PROPERTIES" : "MODEL PARAMETERS"}
            <Settings2 size={14} />
          </div>
          {tab === "setup" ? (
            <>
              <label>
                Material
                <select
                  aria-label="Material preset"
                  value={materials.findIndex((m) => m.name === material.name)}
                  onChange={(e) =>
                    changeSetup(() =>
                      setMaterial({ ...materials[+e.target.value] }),
                    )
                  }
                >
                  <option value={-1} disabled>
                    Custom material
                  </option>
                  {materials.map((m, i) => (
                    <option key={m.name} value={i}>
                      {m.name}
                    </option>
                  ))}
                </select>
              </label>
              <NumberInput
                label="Young’s modulus"
                unit="MPa"
                value={material.young_mpa}
                onChange={(v) =>
                  changeSetup(() => setMaterial({ ...material, young_mpa: v }))
                }
              />
              <NumberInput
                label="Poisson’s ratio"
                unit="ν"
                value={material.poisson}
                step={0.01}
                onChange={(v) =>
                  changeSetup(() => setMaterial({ ...material, poisson: v }))
                }
              />
              <NumberInput
                label="Yield strength"
                unit="MPa"
                value={material.yield_mpa}
                onChange={(v) =>
                  changeSetup(() => setMaterial({ ...material, yield_mpa: v }))
                }
              />
              <NumberInput
                label="Density"
                unit="kg/m³"
                value={material.density_kg_m3}
                onChange={(v) =>
                  changeSetup(() =>
                    setMaterial({ ...material, density_kg_m3: v }),
                  )
                }
              />
              <p className="field-help">
                Presets are illustrative. Use verified properties for your
                actual material.
              </p>
            </>
          ) : (
            <>
              <label>
                Part type
                <select
                  aria-label="Part type"
                  value={spec.kind}
                  onChange={(e) => {
                    const kind = e.target.value as Geometry["kind"];
                    if (kind === "step") {
                      stepFile.current?.click();
                      return;
                    }
                    if (kind === "stl") {
                      stlFile.current?.click();
                      return;
                    }
                    const features =
                      kind === "custom" && !spec.features.length
                        ? [
                            {
                              operation: "add" as const,
                              primitive: "box" as const,
                              origin: [0, 0, 0] as Vec3,
                              size: [80, 30, 10] as Vec3,
                              axis: [0, 0, 10] as Vec3,
                              radius: 5,
                            },
                          ]
                        : spec.features;
                    updateSpec({ kind, features });
                    setFeatureText(JSON.stringify(features, null, 2));
                  }}
                >
                  <option value="bracket">Mounting bracket</option>
                  <option value="plate">Plate / beam</option>
                  <option value="shaft">Shaft / tube</option>
                  <option value="custom">Custom solid (CSG)</option>
                  <option value="step">Import STEP…</option>
                  <option value="stl">Import STL…</option>
                </select>
              </label>
              {spec.kind !== "step" &&
                spec.kind !== "custom" &&
                spec.kind !== "stl" && (
                  <>
                    <NumberInput
                      label="Length"
                      unit="mm"
                      value={spec.length}
                      onChange={(v) => updateSpec({ length: v })}
                    />
                    <NumberInput
                      label={spec.kind === "shaft" ? "Diameter" : "Width"}
                      unit="mm"
                      value={spec.width}
                      onChange={(v) => updateSpec({ width: v })}
                    />
                    {spec.kind === "bracket" && (
                      <NumberInput
                        label="Height"
                        unit="mm"
                        value={spec.height}
                        onChange={(v) => updateSpec({ height: v })}
                      />
                    )}{" "}
                    {spec.kind !== "shaft" && (
                      <NumberInput
                        label="Thickness"
                        unit="mm"
                        value={spec.thickness}
                        onChange={(v) => updateSpec({ thickness: v })}
                      />
                    )}
                    <NumberInput
                      label="Bore diameter"
                      unit="mm"
                      value={spec.hole_diameter}
                      onChange={(v) => updateSpec({ hole_diameter: v })}
                    />
                  </>
                )}
              {spec.kind === "custom" && (
                <label>
                  Solid recipe
                  <textarea
                    className="recipe"
                    aria-label="Custom solid recipe"
                    value={
                      featureText || JSON.stringify(spec.features, null, 2)
                    }
                    onChange={(e) => {
                      setFeatureText(e.target.value);
                      try {
                        updateSpec({ features: JSON.parse(e.target.value) });
                        setFeatureError("");
                      } catch {
                        setFeatureError("Complete a valid JSON feature array.");
                      }
                    }}
                  />
                  {featureError && (
                    <small className="error-text">{featureError}</small>
                  )}
                </label>
              )}
              <NumberInput
                label="Mesh size"
                unit="mm"
                value={spec.mesh_size}
                step={0.5}
                onChange={(v) => updateSpec({ mesh_size: v })}
              />
              <button
                className="outline-button full-width"
                onClick={() => build()}
                disabled={!!featureError}
              >
                <Layers3 size={15} />
                {dirty ? "Rebuild model" : "Build model"}
              </button>
              {spec.kind === "stl" && (
                <>
                  <NumberInput
                    label="Unit scale"
                    unit="×"
                    value={spec.unit_scale}
                    step={0.1}
                    onChange={(v) =>
                      updateSpec({
                        unit_scale: v,
                        accept_stl_preprocessing: false,
                      })
                    }
                  />
                  <NumberInput
                    label="Feature angle"
                    unit="deg"
                    value={spec.feature_angle_deg}
                    onChange={(v) => updateSpec({ feature_angle_deg: v })}
                  />
                  {stlInspect && (
                    <p>
                      Dimensions at this scale:{" "}
                      {stlInspect.extent_mm
                        .map((v) =>
                          format(
                            (v * spec.unit_scale) / (stlInspect.scale || 1),
                          ),
                        )
                        .join(" × ")}{" "}
                      mm. Suggested scale {stlInspect.suggested_scale}×; verify
                      against a known dimension.
                    </p>
                  )}
                  {stlInspect?.preprocessing?.changed && (
                    <label className="inline-check">
                      <input
                        type="checkbox"
                        checked={!!spec.accept_stl_preprocessing}
                        onChange={(e) =>
                          updateSpec({
                            accept_stl_preprocessing: e.target.checked,
                          })
                        }
                      />
                      I reviewed the simplified geometry: maximum original
                      vertex distance to a working vertex{" "}
                      {format(
                        (stlInspect.preprocessing.vertex_distance_bound_mm *
                          spec.unit_scale) /
                          (stlInspect.scale || 1),
                      )}{" "}
                      mm; volume change{" "}
                      {format(
                        100 * stlInspect.preprocessing.relative_volume_change,
                      )}
                      %. Small features still require inspection.
                    </label>
                  )}
                  {stlInspect && (
                    <p className="stl-report">
                      {stlInspect.triangles.toLocaleString()} triangles ·{" "}
                      {stlInspect.shells} shell
                      {stlInspect.shells === 1 ? "" : "s"} ·{" "}
                      {stlInspect.watertight ? "watertight" : "not watertight"}
                      {stlInspect.warnings[0]
                        ? `. ${stlInspect.warnings[0]}`
                        : ""}
                    </p>
                  )}
                </>
              )}
              <button
                className="text-button full-width"
                onClick={() => stepFile.current?.click()}
              >
                <ArrowDownToLine size={14} /> Import STEP file
              </button>
              <button
                className="text-button full-width"
                onClick={() => stlFile.current?.click()}
              >
                <ArrowDownToLine size={14} /> Import STL file
              </button>
              <button
                className="text-button full-width"
                onClick={async () => {
                  const response = await fetch("/print-coupon.stl");
                  importStl(
                    new File([await response.blob()], "print-coupon.stl", {
                      type: "model/stl",
                    }),
                  );
                }}
              >
                Use example print coupon
              </button>
              <input
                ref={stepFile}
                type="file"
                accept=".step,.stp"
                hidden
                onChange={(e) => {
                  const f = e.target.files?.[0];
                  if (f) importStep(f);
                  e.target.value = "";
                }}
              />
              <input
                ref={stlFile}
                type="file"
                accept=".stl"
                hidden
                onChange={(e) => {
                  const f = e.target.files?.[0];
                  if (f) importStl(f);
                  e.target.value = "";
                }}
              />
            </>
          )}
        </fieldset>
        <div className="sidebar-bottom">
          <div className="engine-status">
            <span className="status-dot" />
            {status}
          </div>
          <span>Open geometry. Real simulation.</span>
          <button className="text-button" onClick={() => setHelp(true)}>
            About the open-source stack <MoveUpRight size={13} />
          </button>
        </div>
      </aside>
      <main className="workspace">
        <div className="workspace-heading">
          <div>
            <div className="eyebrow">ENGINEER WITH CONTEXT</div>
            <h1>
              {tab === "reference"
                ? "Start with what you see."
                : tab === "results"
                  ? "Understand how it responds."
                  : tab === "setup"
                    ? "Define the real-world forces."
                    : tab === "print"
                      ? "Set how it would be printed."
                      : "A clearer view of your design."}
            </h1>
            <p>
              {tab === "reference"
                ? "Capture the details. Make the assumptions explicit."
                : tab === "results"
                  ? "Traceable results, from applied loads to support reactions."
                  : tab === "setup"
                    ? "Assign supports and forces on selectable surfaces, then confirm before solving."
                    : tab === "print"
                      ? "Run the coupon on this computer, then change infill. Settings change a homogenized solid, not a sliced print."
                      : "From a reference, STEP or STL to a solid, ready for the questions that matter."}
            </p>
          </div>
          <button className="outline-button" onClick={openLibrary}>
            <FolderOpen size={15} /> Studies
          </button>
        </div>
        <div className="stage-bar">
          <div className="stage-tabs">
            {steps.map(([key, label], i) => (
              <button
                key={key}
                className={tab === key ? "active" : ""}
                onClick={() => {
                  setTab(key);
                  setField(
                    key === "results" && result
                      ? result.print?.enabled
                        ? "displacement"
                        : "stress"
                      : "solid",
                  );
                }}
              >
                <span>{i + 1}</span>
                {label}
              </button>
            ))}
          </div>
          <span className="stage-meta">
            {model && !dirty ? (
              <>
                <span className="status-dot" />
                Solid ready
              </>
            ) : dirty ? (
              "Model has changes"
            ) : (
              "Building geometry"
            )}
          </span>
        </div>
        {error && (
          <div className="error-banner" role="alert">
            <span>{error}</span>
            <button onClick={() => setError("")} aria-label="Dismiss error">
              <X size={16} />
            </button>
          </div>
        )}
        <div className="main-stage" ref={stageElement}>
          {tab === "print" ? (
            <div className="print-review-layout">
              <div className="print-orientation-view">
                <Viewport
                  model={model}
                  result={null}
                  fixed={fixed}
                  loads={loads}
                  selected={selected}
                  onSelect={setSelected}
                  field="solid"
                  deform={false}
                  wireframe={wireframe}
                  setWireframe={setWireframe}
                  printRotation={print.enabled ? print.rotation_deg : undefined}
                />
              </div>
              <PrintWorkspace
                print={print}
                onChange={(next) => {
                  setPrint(next);
                  invalidate();
                }}
                model={model}
                material={material}
                preview={printPreview}
                disabled={!!busy}
              />
            </div>
          ) : tab === "reference" ? (
            <ImageReview
              key={image?.id || "empty"}
              image={image}
              marks={marks}
              onChange={(marks) => {
                setMarks(marks);
                invalidate();
              }}
              upload={upload}
              disabled={!!busy}
            />
          ) : (
            <Viewport
              model={model}
              printRotation={
                previewing && setupPreview!.print?.enabled
                  ? setupPreview!.print.rotation_deg
                  : undefined
              }
              result={previewing ? null : result}
              fixed={previewing ? setupPreview!.fixed_faces : fixed}
              loads={previewing ? setupPreview!.loads : loads}
              selected={selected}
              onSelect={(id) => {
                if (busy) return;
                setSelected(id);
                if (tab === "model") setTab("setup");
              }}
              field={previewing ? "solid" : field}
              deform={previewing ? false : deform}
              wireframe={wireframe}
              setWireframe={setWireframe}
            />
          )}
          {!!busy && (
            <div className="busy-overlay">
              <Loader2 size={17} className="spin" />
              {busy}
              <span>Local worker</span>
              {operation.current && (
                <button
                  className="outline-button"
                  onClick={() => operation.current?.abort()}
                >
                  Cancel
                </button>
              )}
            </div>
          )}
        </div>
        {previewing && (
          <div className="setup-preview-banner" role="status">
            <div>
              <b>Previewing Astra’s setup</b>
              <span>
                Fixtures and arrows show the proposal. Apply it to update your
                simulation.
              </span>
            </div>
            <button
              className="primary small"
              disabled={!!busy}
              onClick={() => applySimulation(setupPreview!)}
            >
              Apply reviewed setup
            </button>
            <button
              className="icon-button"
              aria-label="Close setup preview"
              onClick={() => setSetupPreview(null)}
            >
              <X size={16} />
            </button>
          </div>
        )}
        {tab === "results" &&
        result &&
        model &&
        result.model_id === model.id ? (
          <>
            <div className="result-toolbar">
              <div className="segmented">
                <button
                  className={field === "stress" ? "active" : ""}
                  onClick={() => setField("stress")}
                >
                  Stress
                </button>
                <button
                  className={field === "displacement" ? "active" : ""}
                  onClick={() => setField("displacement")}
                >
                  Displacement
                </button>
              </div>
              <label className="inline-check">
                <input
                  type="checkbox"
                  checked={deform}
                  onChange={(e) => setDeform(e.target.checked)}
                />{" "}
                Exaggerate deformation
              </label>
              <a
                className="outline-button"
                href={`/api/runs/${result.id}/report/pdf`}
                target="_blank"
              >
                <FileText size={15} /> PDF report
              </a>
              <a
                className="primary small"
                href={`/api/runs/${result.id}/report/zip`}
              >
                <ArrowDownToLine size={15} /> Export package
              </a>
            </div>
            <ResultGuidance result={result} />
            <div className="metrics-grid">
              <Metric
                title="Max displacement"
                value={format(result.max_displacement_mm)}
                unit="mm"
                detail="Compare this when print settings change"
              />
              {result.print?.enabled && (
                <Metric
                  title="Filament mass"
                  value={format(result.print.filament_mass_g)}
                  unit="g"
                  detail={`${format(100 * result.print.volume_fraction)}% solid equivalent`}
                />
              )}
              <Metric
                title="Solve residual"
                value={result.relative_residual.toExponential(1)}
                unit=""
                detail={`Force balance ${result.force_balance_error_n.toExponential(1)} N`}
              />
              <Metric
                title="Peak von Mises"
                value={format(result.peak_von_mises_mpa)}
                unit="MPa"
                detail="Often singular at fixtures — not printed strength"
              />
              <Metric
                title="Yield ratio"
                value={format(result.yield_ratio)}
                unit="×"
                detail="Uses that peak and the supplied yield"
              />
            </div>
            <div className="compare-bar">
              <button
                className="outline-button"
                onClick={() => setPinned(result)}
              >
                Pin this run
              </button>
              {pinned && (
                <button className="text-button" onClick={() => setPinned(null)}>
                  Clear pin
                </button>
              )}
              <span>
                {pinned && pinned.id === result.id
                  ? "Pinned. Change print settings and run again to compare."
                  : pinned
                    ? "Current run is compared with the pinned configuration."
                    : "Pin a run, change orientation/walls/infill, then solve again."}
              </span>
            </div>
            {compare && pinned && pinned.id !== result.id && (
              <CompareTable compare={compare} />
            )}
            <details className="assumptions" open>
              <summary>
                <ShieldCheck size={16} /> Interpretation & assumptions{" "}
                <ChevronDown size={15} />
              </summary>
              <p>
                {result.elements.toLocaleString()}{" "}
                {result.element_order === 1 ? "linear" : "quadratic"} tetrahedra
                · {result.dofs.toLocaleString()} degrees of freedom ·{" "}
                {format(result.seconds)} s solve · {format(result.mass_g)} g
              </p>
              {(result.model_sha256 || result.mesh_sha256) && (
                <p className="hash-line">
                  Geometry {result.model_sha256?.slice(0, 12)} · mesh{" "}
                  {result.mesh_sha256?.slice(0, 12)}
                </p>
              )}
              <p className="execution-evidence">
                {result.execution?.backend === "webgpu"
                  ? "Solved on local GPU"
                  : "Solved on local CPU"}{" "}
                · {result.execution?.device || "SciPy sparse direct"}
                <br />
                {result.execution?.precision}
                {result.execution?.backend === "webgpu" &&
                  ` · ${result.execution.iterations} dispatched iterations · ${result.execution.refinements} refinement passes`}
              </p>
              <ul>
                {result.warnings.map((w, i) => (
                  <li key={i}>{w}</li>
                ))}
              </ul>
            </details>
          </>
        ) : tab === "setup" ? (
          <fieldset className="setup-panel" disabled={!!busy}>
            <div className="interview-invite">
              <Sparkles size={19} />
              <div>
                <b>Describe how this part is used.</b>
                <p>
                  Astra will ask for missing details and propose material,
                  supports and forces for your review.
                </p>
              </div>
              <button
                className="outline-button"
                disabled={!model || dirty || aiBusy || !aiAvailable}
                onClick={startInterview}
              >
                Discuss loading <ArrowRight size={14} />
              </button>
            </div>
            <div className="setup-top">
              <div>
                <span className="eyebrow">BOUNDARY CONDITIONS</span>
                <h3>
                  {face
                    ? `Face ${face.id} selected`
                    : "Select a face on the model"}
                </h3>
                {face && (
                  <p>
                    {face.label} · {format(face.area_mm2)} mm²
                  </p>
                )}
              </div>
              <select
                aria-label="Select model face"
                value={selected ?? ""}
                onChange={(e) => setSelected(+e.target.value)}
              >
                <option value="" disabled>
                  Choose a face…
                </option>
                {model?.faces.map((f) => (
                  <option key={f.id} value={f.id}>
                    Face {f.id} · {f.label}
                  </option>
                ))}
              </select>
            </div>
            <div className="load-editor">
              <button
                className="fixture-button"
                disabled={!face || dirty}
                onClick={() =>
                  changeSetup(() => {
                    setFixed((f) =>
                      f.includes(selected!) ? f : [...f, selected!],
                    );
                    setLoads((l) => l.filter((v) => v.face_id !== selected));
                  })
                }
              >
                <ShieldCheck size={17} /> Fix selected face
              </button>
              <div className="force-components">
                {["X", "Y", "Z"].map((axis, i) => (
                  <label key={axis}>
                    <span>{axis}</span>
                    <input
                      aria-label={`Force ${axis}`}
                      type="number"
                      value={vector[i]}
                      onChange={(e) =>
                        setVector(
                          (v) =>
                            v.map((n, j) =>
                              j === i ? +e.target.value : n,
                            ) as Vec3,
                        )
                      }
                    />
                    <small>N</small>
                  </label>
                ))}
              </div>
              <button
                className="load-button"
                disabled={!face || dirty || !Math.hypot(...vector)}
                onClick={() =>
                  changeSetup(() => {
                    setLoads((l) => [
                      ...l.filter((v) => v.face_id !== selected),
                      { face_id: selected!, vector: [...vector] },
                    ]);
                    setFixed((f) => f.filter((v) => v !== selected));
                  })
                }
              >
                <MoveUpRight size={17} /> Apply force
              </button>
            </div>
            <div className="condition-list">
              {fixed.map((id, i) => (
                <span className="condition fixed" key={id}>
                  <ShieldCheck size={13} /> F{i + 1} · Face {id} · fixed XYZ
                  <button
                    aria-label={`Remove fixture ${i + 1}`}
                    onClick={() =>
                      changeSetup(() =>
                        setFixed((f) => f.filter((v) => v !== id)),
                      )
                    }
                  >
                    <X size={13} />
                  </button>
                </span>
              ))}
              {loads.map((l, i) => (
                <span className="condition force" key={l.face_id}>
                  <MoveUpRight size={13} /> L{i + 1} · Face {l.face_id} · [
                  {l.vector.join(", ")}] N
                  <button
                    aria-label={`Remove load ${i + 1}`}
                    onClick={() =>
                      changeSetup(() =>
                        setLoads((ls) => ls.filter((v) => v !== l)),
                      )
                    }
                  >
                    <X size={13} />
                  </button>
                </span>
              ))}
            </div>
            <p className="field-help">
              Total force is spread uniformly over the selected face. Directions
              use the model’s global XYZ axes. A fixed face restrains all three
              translations.
            </p>
            <label>
              Application notes
              <textarea
                aria-label="Application notes"
                placeholder="How is the part used? Include assembly details and omitted effects."
                value={notes}
                onChange={(e) => changeSetup(() => setNotes(e.target.value))}
              />
            </label>
          </fieldset>
        ) : tab === "model" ? (
          <div className="model-summary">
            <div className="summary-icon">
              <Box size={22} />
            </div>
            <div>
              <h3>{spec.name}</h3>
              <p>
                {model
                  ? `${format(model.bounds[1][0] - model.bounds[0][0])} × ${format(model.bounds[1][1] - model.bounds[0][1])} × ${format(model.bounds[1][2] - model.bounds[0][2])} mm · ${model.faces.length} selectable faces`
                  : "Preparing solid geometry"}
              </p>
              <span className="provenance">
                {spec.provenance === "demo"
                  ? "Example dimensions"
                  : spec.provenance === "image_proposal"
                    ? "Image-based proposal · verify dimensions"
                    : spec.provenance === "step_import"
                      ? "STEP import · verify units"
                      : spec.provenance === "stl_import"
                        ? "STL import · selectable patches, not CAD faces"
                        : "User-specified geometry"}
              </span>
            </div>
            <div className="model-exports">
              {model && (
                <>
                  {model.spec.kind !== "stl" && (
                    <a href={`/api/models/${model.id}/files/model.step`}>
                      STEP <ArrowDownToLine size={13} />
                    </a>
                  )}
                  <a href={`/api/models/${model.id}/files/model.stl`}>
                    STL <ArrowDownToLine size={13} />
                  </a>
                </>
              )}
              <button
                className="primary small"
                disabled={!model || dirty}
                onClick={() => setTab("setup")}
              >
                Set up simulation <ArrowRight size={15} />
              </button>
              <button
                className="text-button"
                disabled={!model || dirty || aiBusy || !aiAvailable || !!busy}
                onClick={startInterview}
              >
                Discuss loading with Astra
              </button>
            </div>
          </div>
        ) : (
          <div className="reference-tip">
            <Sparkles size={18} />
            <div>
              <b>A good simulation starts with a known scale.</b>
              <p>
                Mark one measured dimension. Tell Astra about unseen features,
                material and how the part is used.
              </p>
            </div>
            <button
              className="text-button"
              disabled={!image || aiBusy}
              onClick={() =>
                ask(
                  "Inspect the reference image and my annotations. Ask for the critical specifications needed to model this part faithfully.",
                )
              }
            >
              Ask Astra <ArrowRight size={14} />
            </button>
          </div>
        )}
        {tab === "results" && !result && (
          <div className="empty-results">
            <Layers3 size={22} />
            <h3>Your results will appear here.</h3>
            <p>
              Confirm the model, add supports and forces, then run a simulation.
            </p>
            <button className="outline-button" onClick={() => setTab("setup")}>
              Set up simulation <ArrowRight size={14} />
            </button>
          </div>
        )}
        {(tab === "model" || tab === "print" || tab === "setup") && (
          <div className="compute-choice">
            <label>
              Simulation device{" "}
              <select
                aria-label="Simulation device"
                value={compute}
                disabled={!!busy}
                onChange={(e) => setCompute(e.target.value as "webgpu" | "cpu")}
              >
                <option value="webgpu">Local GPU · WebGPU</option>
                <option value="cpu">Local CPU · reference solver</option>
              </select>
            </label>
            <span>
              {compute === "webgpu"
                ? gpu.device
                : "Float64 sparse direct solve on this computer"}
            </span>
            {busy && <strong role="status">{busy}</strong>}
          </div>
        )}
        {(tab === "model" || tab === "print" || tab === "setup") &&
          readiness &&
          !dirty && (
            <ReadinessPanel
              readiness={readiness}
              onApplyRecommended={applyRecommendedSetup}
            />
          )}
        {(tab === "model" || tab === "print" || tab === "setup") && (
          <div className="run-bar">
            <div>
              <label className="inline-check">
                <input
                  type="checkbox"
                  checked={confirmed}
                  disabled={!model || dirty || !!busy || previewing}
                  onChange={(e) => setConfirmed(e.target.checked)}
                />
                <span>
                  I’ve reviewed dimensions, material,{" "}
                  {print.enabled ? "print settings, " : ""}fixtures and loads.
                </span>
              </label>
              <small>
                {dirty
                  ? "Rebuild geometry to update the mesh and reselect faces."
                  : !fixed.length || !loads.length
                    ? "Select at least one fixture and one loaded face."
                    : print.enabled
                      ? "Review print settings and conditions before every run; check mesh convergence before interpreting trends."
                      : "Static · 3D elasticity · quadratic tetrahedra"}
              </small>
            </div>
            <button
              className="primary run"
              onClick={solve}
              disabled={!canSolve}
            >
              {busy ? (
                <Loader2 size={16} className="spin" />
              ) : (
                <Play size={15} fill="currentColor" />
              )}{" "}
              Run simulation
            </button>
          </div>
        )}
        <footer className="workspace-footer">
          <span>OpenFEA / LOCAL</span>
          <span>Engineering insight starts with explicit assumptions.</span>
          <span>mm · N · MPa</span>
        </footer>
      </main>
      <aside className="astra-panel">
        <div className="astra-heading">
          <span className="astra-orb">
            <Sparkles size={20} />
          </span>
          <div>
            <h2>Astra</h2>
            <span>Your engineering copilot</span>
          </div>
          <span className={"connection-dot " + (aiAvailable ? "online" : "")} />
        </div>
        <div className="astra-context">
          <span className="status-dot" />
          <span>
            {image ? "1 reference" : "Example part"} · {marks.length} notes ·{" "}
            {model ? "3D context" : "awaiting model"}
          </span>
          <Layers3 size={13} />
        </div>
        <div className="chat-messages">
          {messages.map((m, i) => (
            <div key={i} className={"message " + m.role}>
              {m.role === "assistant" && (
                <div className="message-author">
                  <Sparkles size={12} />
                  {m.live ? "ASTRA · LIVE" : "WORKFLOW GUIDE"}
                </div>
              )}
              <div className="message-text">{m.text}</div>
              {!!m.questions?.length && (
                <div className="question-list">
                  {m.questions.map((q, j) => (
                    <div key={j}>
                      <span>{j + 1}</span>
                      <p>{q}</p>
                    </div>
                  ))}
                </div>
              )}
              {m.proposal && (
                <div className="proposal-card">
                  <div>
                    <Box size={16} />
                    <b>Model proposal</b>
                  </div>
                  <strong>{m.proposal.name}</strong>
                  <p>
                    {m.proposal.kind} · {m.proposal.length} × {m.proposal.width}{" "}
                    × {m.proposal.height} mm
                  </p>
                  <details>
                    <summary>Review assumptions & recipe</summary>
                    <ul>
                      {m.proposal.assumptions.map((a, j) => (
                        <li key={j}>{a}</li>
                      ))}
                    </ul>
                    <pre>{JSON.stringify(m.proposal, null, 2)}</pre>
                  </details>
                  <button
                    className="primary small"
                    disabled={!!busy}
                    onClick={() => {
                      setFeatureText("");
                      build(m.proposal!);
                    }}
                  >
                    Apply & build proposal <ArrowRight size={14} />
                  </button>
                </div>
              )}
              {m.simulation_proposal && (
                <SetupProposalCard
                  proposal={m.simulation_proposal}
                  model={model}
                  current={proposalCurrent(m.simulation_proposal)}
                  applied={setupProposalId === m.simulation_proposal.id}
                  busy={!!busy}
                  preview={() => {
                    setSetupPreview(m.simulation_proposal!);
                    setSelected(null);
                    setTab("setup");
                    setField("solid");
                  }}
                  apply={() => applySimulation(m.simulation_proposal!)}
                />
              )}
            </div>
          ))}
          {aiBusy && (
            <div className="message assistant">
              <div className="message-author">
                <Sparkles size={12} /> ASTRA
              </div>
              <div className="thinking">
                <i />
                <i />
                <i />
                <span>Reviewing your design…</span>
              </div>
            </div>
          )}
          <div ref={chatEnd} />
        </div>
        <div className="chat-bottom">
          <div className="quick-prompts">
            <button
              disabled={aiBusy}
              onClick={() =>
                ask(
                  tab === "setup"
                    ? "Help me finish the loading interview for this built part. What material, support, load or operating details are still missing?"
                    : tab === "results" && result
                      ? "Explain the actual simulation results, the assumptions that matter most, and what I should verify next."
                      : image
                        ? "Inspect the reference image. What dimensions and missing details do you need before modelling?"
                        : "Explain the current bracket, its force direction and fixtures. Which assumptions should I review?",
                )
              }
            >
              {tab === "setup"
                ? "Continue load interview"
                : tab === "results" && result
                  ? "Interpret results"
                  : image
                    ? "Inspect reference"
                    : "Review this setup"}{" "}
              <Plus size={12} />
            </button>
            <button
              disabled={aiBusy}
              onClick={() =>
                ask(
                  "What information is still missing for a credible simulation of this part?",
                )
              }
            >
              What’s missing? <Plus size={12} />
            </button>
          </div>
          <form
            className="composer"
            onSubmit={(e) => {
              e.preventDefault();
              ask();
            }}
          >
            <textarea
              aria-label="Message Astra"
              placeholder={
                tab === "setup"
                  ? "How is it held? What forces act on it?"
                  : "Describe your part or ask Astra…"
              }
              maxLength={16000}
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  ask();
                }
              }}
            />
            <div>
              <span>
                <Sparkles size={13} /> GPT-6 Astra
              </span>
              <button
                type="submit"
                aria-label="Send to Astra"
                disabled={aiBusy || !prompt.trim() || !aiAvailable}
              >
                {aiBusy ? (
                  <Loader2 size={15} className="spin" />
                ) : (
                  <ArrowUp size={17} />
                )}
              </button>
            </div>
          </form>
          <p>
            Image, notes and chat are sent to Astra through your signed-in Codex
            account.
          </p>
        </div>
      </aside>
      {toast && (
        <div className="toast" role="status">
          <CheckCircle2 size={17} />
          {toast}
        </div>
      )}
      {library && (
        <div className="modal-backdrop">
          <div className="library-modal">
            <div className="modal-title">
              <h2>Your saved studies</h2>
              <button
                aria-label="Close studies"
                onClick={() => setLibrary(null)}
              >
                <X size={19} />
              </button>
            </div>
            <p>
              Snapshots keep the image, annotations, model, setup and results
              together.
            </p>
            {!library.length && (
              <div className="empty-library">
                No saved snapshots yet. Use “Save study” to create one.
              </div>
            )}
            {library.map((s) => (
              <button
                className="library-row"
                key={s.id}
                onClick={async () => {
                  try {
                    const v = await api<{ state: Saved }>("/studies/" + s.id);
                    await restore(v.state);
                    setLibrary(null);
                    flash("Study restored.");
                  } catch (e) {
                    setError((e as Error).message);
                  }
                }}
              >
                <Box size={20} />
                <span>
                  <b>{s.name}</b>
                  <small>
                    {new Date(s.updated_at * 1000).toLocaleString()}
                  </small>
                </span>
                <ChevronRight size={16} />
              </button>
            ))}
          </div>
        </div>
      )}
      {help && (
        <div className="modal-backdrop">
          <div className="help-modal">
            <div className="modal-title">
              <h2>Built to make engineering inspectable.</h2>
              <button aria-label="Close help" onClick={() => setHelp(false)}>
                <X size={19} />
              </button>
            </div>
            <p>
              OpenFEA is a local prototype for one connected 3D mechanical
              solid. Astra is optional.
            </p>
            <ol>
              <li>
                A first visit opens the example print coupon on this computer’s
                CPU. Confirm is already checked. Click Run simulation.
              </li>
              <li>
                Read what to trust (displacement, residual, mass) and what not
                to treat as printed strength (peak stress, yield ratio).
              </li>
              <li>
                The first print run is pinned. Change infill and run again to
                compare.
              </li>
              <li>
                For your own part, import a watertight STL or STEP. Readiness
                lists what is missing. Use recommended fixture and load, then
                confirm.
              </li>
              <li>
                Agents use GET /api/agent — the same readiness, confirm gate,
                residual &lt; 1e-7, and report hashes. No UI scraping.
              </li>
            </ol>
            <div className="stack-grid">
              <b>OpenCASCADE + Gmsh</b>
              <span>Solid geometry & tetrahedral meshing</span>
              <b>WebGPU + scikit-fem</b>
              <span>Local GPU solve · quadratic 3D finite elements</span>
              <b>React + Three.js</b>
              <span>Interactive review workspace</span>
              <b>GPT-6 Astra</b>
              <span>Proprietary AI via your Codex account</span>
            </div>
            <p>
              Geometry, solving and exports run locally without AI. A single
              photo cannot determine unseen geometry or real-world scale. This
              version does not model contact, assemblies, plasticity, buckling,
              fatigue or explicit infill geometry. Print settings use a
              homogenized equivalent solid. Results require engineering review
              and physical validation.
            </p>
            <p>
              Source license: GPL-3.0-or-later. Reports and CAD exports are your
              project artifacts.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
function NumberInput({
  label,
  unit,
  value,
  onChange,
  step = 1,
}: {
  label: string;
  unit: string;
  value: number;
  onChange: (v: number) => void;
  step?: number;
}) {
  return (
    <label className="number-field">
      <span>{label}</span>
      <div>
        <input
          aria-label={label}
          type="number"
          value={value}
          step={step}
          onChange={(e) => onChange(+e.target.value)}
        />
        <small>{unit}</small>
      </div>
    </label>
  );
}
function Metric({
  title,
  value,
  unit,
  detail,
}: {
  title: string;
  value: string;
  unit: string;
  detail: string;
}) {
  return (
    <div className="metric">
      <span>{title}</span>
      <div>
        {value} <small>{unit}</small>
      </div>
      <p>{detail}</p>
    </div>
  );
}
