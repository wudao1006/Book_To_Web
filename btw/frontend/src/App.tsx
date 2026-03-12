import { useEffect, useMemo, useState } from "react";
import { DynamicComponent, type DynamicLoaderError } from "./renderer/DynamicLoader";

type TaskPayload = {
  id: string;
  status: string;
  error_code?: string | null;
  error_message?: string | null;
};

type TaskStep = {
  stage: string;
  status: string;
  error_code?: string | null;
  error_message?: string | null;
};

type VersionInfo = {
  version_num: number;
  is_latest: boolean;
  is_stable: boolean;
  bundle_size: number;
  created_at: string;
};

type VersionsResponse = {
  latest: VersionInfo | null;
  stable: VersionInfo | null;
  versions: VersionInfo[];
};

type ApiErrorPayload = {
  code: string;
  message: string;
  stage: string;
  retriable: boolean;
  trace_id: string;
};

const sampleChapterCode = `
export default function InlineNarrative() {
  const [focus, setFocus] = React.useState("reader");

  return (
    <article className="rounded-3xl border border-emerald-200 bg-white p-6 shadow-panel">
      <div className="flex flex-wrap items-center gap-3">
        {["reader", "planner", "creator"].map((item) => (
          <button
            key={item}
            className={
              "rounded-full px-3 py-1 text-sm " +
              (focus === item ? "bg-emerald-700 text-white" : "bg-emerald-100 text-emerald-900")
            }
            onClick={() => setFocus(item)}
          >
            {item}
          </button>
        ))}
      </div>
      <p className="mt-5 text-sm leading-7 text-slate-700">
        Current focus: <span className="font-semibold text-slate-900">{focus}</span>. This preview
        shows how a chapter can become a small interactive reading artifact before the backend is
        online.
      </p>
    </article>
  );
}
`;

function isApiErrorPayload(payload: unknown): payload is ApiErrorPayload {
  if (typeof payload !== "object" || payload === null) {
    return false;
  }
  const record = payload as Record<string, unknown>;
  return (
    typeof record.code === "string" &&
    typeof record.message === "string" &&
    typeof record.stage === "string" &&
    typeof record.retriable === "boolean" &&
    typeof record.trace_id === "string"
  );
}

function App() {
  const [bookId, setBookId] = useState("");
  const [chapterIndex, setChapterIndex] = useState(0);
  const [useApi, setUseApi] = useState(false);
  const [allowUnsafeExecution, setAllowUnsafeExecution] = useState(false);

  const [taskId, setTaskId] = useState<string | null>(null);
  const [taskStatus, setTaskStatus] = useState<string>("idle");
  const [taskSteps, setTaskSteps] = useState<TaskStep[]>([]);
  const [taskMessage, setTaskMessage] = useState<string>("No active generation task.");

  const [versions, setVersions] = useState<VersionInfo[]>([]);
  const [latestVersion, setLatestVersion] = useState<VersionInfo | null>(null);
  const [stableVersion, setStableVersion] = useState<VersionInfo | null>(null);
  const [versionMode, setVersionMode] = useState<"latest" | "stable">("latest");

  const [apiError, setApiError] = useState<string | null>(null);
  const [loaderError, setLoaderError] = useState<DynamicLoaderError | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [rendererNonce, setRendererNonce] = useState(0);

  const hasApiTarget = useApi && bookId.trim().length > 0;

  const stageOrder = useMemo(
    () => ["create", "critic", "validate", "compile", "render"],
    []
  );

  const stepMap = useMemo(() => {
    const map = new Map<string, TaskStep>();
    for (const step of taskSteps) {
      map.set(step.stage, step);
    }
    return map;
  }, [taskSteps]);

  async function loadVersions(targetBookId: string, targetChapterIndex: number) {
    const response = await fetch(
      `/api/books/${targetBookId}/chapters/${targetChapterIndex}/versions`
    );
    if (!response.ok) {
      setVersions([]);
      setLatestVersion(null);
      setStableVersion(null);
      return;
    }
    const payload = (await response.json()) as VersionsResponse;
    setVersions(payload.versions || []);
    setLatestVersion(payload.latest || null);
    setStableVersion(payload.stable || null);
  }

  async function loadTaskState(currentTaskId: string) {
    const [taskResponse, stepsResponse] = await Promise.all([
      fetch(`/api/tasks/${currentTaskId}`),
      fetch(`/api/tasks/${currentTaskId}/steps`)
    ]);

    if (taskResponse.ok) {
      const task = (await taskResponse.json()) as TaskPayload;
      setTaskStatus(task.status);
      if (task.status === "failed") {
        setTaskMessage(task.error_message || task.error_code || "Task failed.");
      } else if (task.status === "succeeded") {
        setTaskMessage("Task completed.");
      }
    }

    if (stepsResponse.ok) {
      const payload = (await stepsResponse.json()) as { steps: TaskStep[] };
      setTaskSteps(payload.steps || []);
    }
  }

  async function handleGenerate() {
    if (!hasApiTarget) {
      setApiError("Book ID is required in API mode.");
      return;
    }

    setApiError(null);
    setTaskMessage("Generation started.");
    setIsGenerating(true);

    try {
      const response = await fetch(
        `/api/books/${bookId}/chapters/${chapterIndex}/generate`,
        {
          method: "POST"
        }
      );

      if (!response.ok) {
        let payload: unknown = null;
        try {
          payload = await response.json();
        } catch {
          payload = null;
        }
        if (isApiErrorPayload(payload)) {
          setApiError(
            `${payload.message} (stage=${payload.stage}, retriable=${String(payload.retriable)})`
          );
          setTaskMessage(`Generation failed: ${payload.message}`);
          return;
        }
        setApiError(`Generation failed with status ${response.status}`);
        return;
      }

      const payload = (await response.json()) as { task_id: string; success: boolean };
      setTaskId(payload.task_id);
      setTaskStatus("running");
      setTaskMessage("Generation task queued.");
      await loadTaskState(payload.task_id);
      await loadVersions(bookId, chapterIndex);
      setRendererNonce((value) => value + 1);
    } finally {
      setIsGenerating(false);
    }
  }

  async function handleRollback() {
    if (!hasApiTarget) {
      return;
    }

    setApiError(null);
    const response = await fetch(
      `/api/books/${bookId}/chapters/${chapterIndex}/rollback`,
      {
        method: "POST"
      }
    );

    if (!response.ok) {
      let payload: unknown = null;
      try {
        payload = await response.json();
      } catch {
        payload = null;
      }
      if (isApiErrorPayload(payload)) {
        setApiError(payload.message);
      } else {
        setApiError(`Rollback failed with status ${response.status}`);
      }
      return;
    }

    setVersionMode("latest");
    await loadVersions(bookId, chapterIndex);
    setRendererNonce((value) => value + 1);
    setTaskMessage("Rollback completed. Latest now points to stable.");
  }

  useEffect(() => {
    if (!hasApiTarget) {
      setVersions([]);
      setLatestVersion(null);
      setStableVersion(null);
      setTaskId(null);
      setTaskStatus("idle");
      setTaskSteps([]);
      return;
    }

    void loadVersions(bookId, chapterIndex);
  }, [hasApiTarget, bookId, chapterIndex]);

  useEffect(() => {
    if (!taskId) {
      return;
    }

    let timer: number | null = null;
    let cancelled = false;

    const poll = async () => {
      if (cancelled) {
        return;
      }
      await loadTaskState(taskId);
      if (!cancelled && (taskStatus === "running" || taskStatus === "queued" || taskStatus === "retrying")) {
        timer = window.setTimeout(poll, 1000);
      }
    };

    void poll();

    return () => {
      cancelled = true;
      if (timer != null) {
        window.clearTimeout(timer);
      }
    };
  }, [taskId, taskStatus]);

  return (
    <div className="min-h-screen text-ink">
      <main className="mx-auto flex min-h-screen max-w-6xl flex-col gap-8 px-4 py-8 sm:px-6 lg:px-8">
        <section className="overflow-hidden rounded-[2rem] border border-white/50 bg-white/65 shadow-panel backdrop-blur">
          <div className="grid gap-8 p-8 lg:grid-cols-[1.2fr_0.8fr] lg:p-12">
            <div>
              <p className="text-xs uppercase tracking-[0.35em] text-ember">Book To Web</p>
              <h1 className="mt-4 max-w-3xl font-display text-4xl leading-tight text-ink sm:text-5xl">
                A minimal shell for AI-generated chapters with observable generation states.
              </h1>
              <p className="mt-6 max-w-2xl text-base leading-8 text-slate-700">
                API mode now exposes stage progress, version selection, and rollback so failures are
                visible and recoverable.
              </p>
            </div>

            <aside className="rounded-[1.5rem] border border-slate-200 bg-mist/80 p-6">
              <p className="text-xs uppercase tracking-[0.3em] text-pine">Loader controls</p>
              <div className="mt-6 space-y-4">
                <label className="block text-sm font-medium text-slate-700">
                  <span className="mb-2 block">Book ID</span>
                  <input
                    className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 outline-none transition focus:border-pine"
                    onChange={(event) => setBookId(event.target.value)}
                    placeholder="book-001"
                    value={bookId}
                  />
                </label>
                <label className="block text-sm font-medium text-slate-700">
                  <span className="mb-2 block">Chapter Index</span>
                  <input
                    className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 outline-none transition focus:border-pine"
                    min={0}
                    onChange={(event) => setChapterIndex(Number(event.target.value) || 0)}
                    type="number"
                    value={chapterIndex}
                  />
                </label>
                <label className="flex items-center justify-between rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-700">
                  <span>Use backend API</span>
                  <input
                    checked={useApi}
                    className="h-4 w-4 accent-pine"
                    onChange={(event) => setUseApi(event.target.checked)}
                    type="checkbox"
                  />
                </label>
                <label className="flex items-center justify-between rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-slate-700">
                  <span>Allow unsafe code execution</span>
                  <input
                    checked={allowUnsafeExecution}
                    className="h-4 w-4 accent-amber-700"
                    onChange={(event) => setAllowUnsafeExecution(event.target.checked)}
                    type="checkbox"
                  />
                </label>
                <button
                  className="w-full rounded-2xl bg-pine px-4 py-3 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:bg-slate-400"
                  disabled={!hasApiTarget || isGenerating}
                  onClick={() => void handleGenerate()}
                  type="button"
                >
                  {isGenerating ? "Generating..." : "Generate Component"}
                </button>
                <div className="rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-700">
                  <p className="text-xs uppercase tracking-[0.25em] text-pine">Version Mode</p>
                  <div className="mt-2 flex items-center gap-4">
                    <label className="flex items-center gap-2">
                      <input
                        checked={versionMode === "latest"}
                        className="h-4 w-4 accent-pine"
                        onChange={() => setVersionMode("latest")}
                        type="radio"
                      />
                      latest
                    </label>
                    <label className="flex items-center gap-2">
                      <input
                        checked={versionMode === "stable"}
                        className="h-4 w-4 accent-pine"
                        onChange={() => setVersionMode("stable")}
                        type="radio"
                      />
                      stable
                    </label>
                  </div>
                  <button
                    className="mt-3 rounded-full border border-slate-300 px-3 py-1 text-xs font-semibold text-slate-700 disabled:cursor-not-allowed disabled:opacity-50"
                    disabled={!stableVersion || !latestVersion || latestVersion.version_num === stableVersion.version_num}
                    onClick={() => void handleRollback()}
                    type="button"
                  >
                    Rollback to stable
                  </button>
                </div>
                {apiError ? (
                  <p className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
                    {apiError}
                  </p>
                ) : null}
              </div>
            </aside>
          </div>
        </section>

        <section className="grid gap-6 lg:grid-cols-[0.72fr_1fr]">
          <article className="rounded-[2rem] border border-white/50 bg-white/65 p-6 shadow-panel backdrop-blur">
            <p className="text-xs uppercase tracking-[0.3em] text-ember">Stage Progress</p>
            <p className="mt-3 text-sm text-slate-600">Task status: {taskStatus}</p>
            <p className="mt-1 text-sm text-slate-600">{taskMessage}</p>
            {taskId ? <p className="mt-1 text-xs text-slate-500">task_id: {taskId}</p> : null}

            <ul className="mt-5 space-y-2 text-sm leading-6 text-slate-700">
              {stageOrder.map((stage) => {
                const step = stepMap.get(stage);
                const status = step?.status || "pending";
                return (
                  <li
                    className="flex items-center justify-between rounded-xl border border-slate-200 bg-white px-3 py-2"
                    key={stage}
                  >
                    <span className="font-medium">{stage}</span>
                    <span className="text-xs uppercase tracking-wide text-slate-500">{status}</span>
                  </li>
                );
              })}
            </ul>

            <div className="mt-5 rounded-2xl border border-slate-200 bg-white p-3">
              <p className="text-xs uppercase tracking-[0.25em] text-pine">Versions</p>
              <ul className="mt-2 space-y-1 text-xs text-slate-600">
                {versions.length === 0 ? <li>No generated versions yet.</li> : null}
                {versions.map((version) => (
                  <li className="flex items-center justify-between" key={version.version_num}>
                    <span>v{version.version_num}</span>
                    <span>
                      {version.is_latest ? "latest" : ""}
                      {version.is_latest && version.is_stable ? " / " : ""}
                      {version.is_stable ? "stable" : ""}
                    </span>
                  </li>
                ))}
              </ul>
            </div>

            {loaderError && versionMode === "latest" && stableVersion ? (
              <button
                className="mt-4 rounded-full border border-amber-300 bg-amber-50 px-3 py-2 text-xs font-semibold text-amber-800"
                onClick={() => setVersionMode("stable")}
                type="button"
              >
                Latest failed at {loaderError.stage || "render"}, switch to stable
              </button>
            ) : null}
          </article>

          <section className="space-y-4">
            <p className="text-xs uppercase tracking-[0.3em] text-pine">Renderer preview</p>
            <DynamicComponent
              allowUnsafeExecution={allowUnsafeExecution}
              bookId={useApi ? bookId : undefined}
              chapterIndex={chapterIndex}
              inlineCode={useApi ? undefined : sampleChapterCode}
              onErrorChange={setLoaderError}
              version={versionMode}
              key={`${bookId}-${chapterIndex}-${versionMode}-${rendererNonce}-${useApi ? "api" : "inline"}`}
            />
          </section>
        </section>
      </main>
    </div>
  );
}

export default App;
