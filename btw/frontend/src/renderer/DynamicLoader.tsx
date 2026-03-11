import { Suspense, useEffect, useRef, useState } from "react";
import type { ComponentType } from "react";
import * as React from "react";
import reactDomRuntime from "../../node_modules/react-dom/umd/react-dom.production.min.js?raw";
import reactRuntime from "../../node_modules/react/umd/react.production.min.js?raw";
import { compileJSX } from "./BabelCompiler";

type ApiErrorPayload = {
  code: string;
  message: string;
  stage: string;
  retriable: boolean;
  trace_id: string;
};

type ComponentPayload = {
  type: "js" | "jsx";
  code: string;
};

type DynamicComponentProps = {
  bookId?: string;
  chapterIndex?: number;
  inlineCode?: string;
  allowUnsafeExecution?: boolean;
};

type LoaderError = {
  message: string;
  retriable: boolean;
  traceId?: string;
};

type SandboxMessage =
  | { frameId: string; type: "btw-sandbox-height"; height: number }
  | { frameId: string; type: "btw-sandbox-error"; message: string };

const fallbackClassName =
  "rounded-3xl border border-white/60 bg-white/70 p-6 text-sm text-slate-600 shadow-panel backdrop-blur";

const demoComponentCode = `
export default function DemoChapter() {
  const [value, setValue] = React.useState(42);

  return (
    <section className="space-y-4 rounded-3xl border border-amber-200 bg-amber-50/80 p-6">
      <div>
        <p className="text-xs uppercase tracking-[0.3em] text-amber-700">Demo Component</p>
        <h3 className="mt-2 font-display text-2xl text-slate-900">Supply reacts to pressure</h3>
      </div>
      <p className="text-sm leading-7 text-slate-700">
        This local demo path keeps the renderer usable before the backend exists.
      </p>
      <label className="block text-sm font-medium text-slate-700">
        Market pressure: <span className="font-semibold">{value}</span>
      </label>
      <input
        className="w-full accent-amber-700"
        min="0"
        max="100"
        type="range"
        value={value}
        onChange={(event) => setValue(Number(event.target.value))}
      />
      <div className="h-3 rounded-full bg-slate-200">
        <div
          className="h-3 rounded-full bg-gradient-to-r from-amber-600 to-emerald-700"
          style={{ width: value + "%" }}
        />
      </div>
    </section>
  );
}
`;

function FallbackCard({
  text,
  retriable = false,
  traceId,
  onRetry
}: {
  text: string;
  retriable?: boolean;
  traceId?: string;
  onRetry?: () => void;
}) {
  return (
    <div className={fallbackClassName}>
      <p>{text}</p>
      {traceId ? (
        <p className="mt-2 text-xs text-slate-500">trace_id: {traceId}</p>
      ) : null}
      {retriable && onRetry ? (
        <button
          className="mt-4 rounded-full border border-slate-300 px-3 py-1 text-xs font-semibold text-slate-700 hover:bg-white"
          onClick={onRetry}
          type="button"
        >
          Retry
        </button>
      ) : null}
    </div>
  );
}

class RemoteComponentError extends Error {
  readonly retriable: boolean;
  readonly traceId?: string;

  constructor(message: string, retriable: boolean, traceId?: string) {
    super(message);
    this.retriable = retriable;
    this.traceId = traceId;
  }
}

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

function isSandboxMessage(payload: unknown): payload is SandboxMessage {
  if (typeof payload !== "object" || payload === null) {
    return false;
  }
  const record = payload as Record<string, unknown>;
  return typeof record.type === "string" && typeof record.frameId === "string";
}

function escapeInlineScript(source: string): string {
  return source.replace(/<\/script/gi, "<\\/script");
}

async function readRemoteComponent(bookId: string, chapterIndex: number): Promise<ComponentPayload> {
  const response = await fetch(`/api/books/${bookId}/chapters/${chapterIndex}/component`);

  if (!response.ok) {
    const traceId = response.headers.get("x-trace-id") ?? undefined;
    let body: unknown = null;
    try {
      body = await response.json();
    } catch {
      body = null;
    }
    if (isApiErrorPayload(body)) {
      throw new RemoteComponentError(body.message, body.retriable, body.trace_id || traceId);
    }

    if (response.status === 404) {
      throw new RemoteComponentError("Component not generated yet.", true, traceId);
    }
    throw new RemoteComponentError(`Failed to load component: ${response.status}`, true, traceId);
  }

  return (await response.json()) as ComponentPayload;
}

async function instantiateComponent(
  sourceCode: string,
  sourceType: ComponentPayload["type"]
): Promise<ComponentType> {
  const compiledCode =
    sourceType === "js" ? sourceCode : await compileJSX(sourceCode);
  const exportsObject: { default?: ComponentType } = {};
  const moduleObject = { exports: exportsObject };
  const factory = new Function(
    "React",
    "exports",
    "module",
    `${compiledCode}\nreturn module.exports.default || exports.default;`
  );
  const exported = factory(React, exportsObject, moduleObject) as ComponentType | undefined;

  if (!exported) {
    throw new Error("Component module has no default export");
  }

  return exported;
}

function buildSandboxDocument(frameId: string, compiledCode: string): string {
  const serializedFrameId = JSON.stringify(frameId);
  const safeCompiledCode = escapeInlineScript(compiledCode);
  const safeReactRuntime = escapeInlineScript(reactRuntime);
  const safeReactDomRuntime = escapeInlineScript(reactDomRuntime);

  return `<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta
      http-equiv="Content-Security-Policy"
      content="default-src 'none'; script-src https://cdn.jsdelivr.net 'unsafe-inline'; style-src 'unsafe-inline'; img-src data: https:;"
    />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <style>
      html, body, #root {
        margin: 0;
        min-height: 100%;
      }

      body {
        font-family: ui-sans-serif, system-ui, sans-serif;
        background: transparent;
      }
    </style>
  </head>
  <body>
    <div id="root"></div>
    <script>${safeReactRuntime}</script>
    <script>${safeReactDomRuntime}</script>
    <script>
      const frameId = ${serializedFrameId};

      const notify = (payload) => {
        window.parent.postMessage({ frameId, ...payload }, "*");
      };

      const reportHeight = () => {
        const height = Math.max(
          document.documentElement.scrollHeight,
          document.body.scrollHeight,
          240
        );
        notify({ type: "btw-sandbox-height", height });
      };

      try {
        const require = (name) => {
          if (name === "react") {
            return window.React;
          }
          throw new Error("Unsupported module: " + name);
        };
        const exports = {};
        const module = { exports };
        ${safeCompiledCode}
        const ResolvedComponent = module.exports.default || exports.default;
        if (!ResolvedComponent) {
          throw new Error("Component module has no default export");
        }
        const root = window.ReactDOM.createRoot(document.getElementById("root"));
        root.render(window.React.createElement(ResolvedComponent));
        requestAnimationFrame(reportHeight);
        if (window.ResizeObserver) {
          new ResizeObserver(reportHeight).observe(document.body);
        }
      } catch (error) {
        const message = error instanceof Error ? error.message : String(error);
        notify({ type: "btw-sandbox-error", message });
      }
    </script>
  </body>
</html>`;
}

function SandboxedRemoteComponent({
  bookId,
  chapterIndex,
  allowUnsafeExecution
}: {
  bookId: string;
  chapterIndex: number;
  allowUnsafeExecution: boolean;
}) {
  const [frameMarkup, setFrameMarkup] = useState<string | null>(null);
  const [error, setError] = useState<LoaderError | null>(null);
  const [loading, setLoading] = useState(true);
  const [reloadNonce, setReloadNonce] = useState(0);
  const [frameHeight, setFrameHeight] = useState(320);
  const frameId = `btw-frame-${bookId}-${chapterIndex}-${reloadNonce}`;
  const iframeRef = useRef<HTMLIFrameElement | null>(null);

  useEffect(() => {
    function handleMessage(event: MessageEvent) {
      if (!isSandboxMessage(event.data) || event.data.frameId !== frameId) {
        return;
      }
      if (event.source !== iframeRef.current?.contentWindow) {
        return;
      }

      if (event.data.type === "btw-sandbox-height") {
        setFrameHeight(Math.max(240, event.data.height));
        return;
      }

      if (event.data.type === "btw-sandbox-error") {
        setError({
          message: `Sandbox render failed: ${event.data.message}`,
          retriable: false
        });
        setLoading(false);
      }
    }

    window.addEventListener("message", handleMessage);
    return () => {
      window.removeEventListener("message", handleMessage);
    };
  }, [frameId]);

  useEffect(() => {
    let disposed = false;

    async function load() {
      setLoading(true);
      setError(null);
      setFrameMarkup(null);

      try {
        if (!allowUnsafeExecution) {
          throw new RemoteComponentError(
            "Remote generated code execution is blocked by policy. Enable unsafe execution to continue.",
            false
          );
        }

        const payload = await readRemoteComponent(bookId, chapterIndex);
        const compiledCode =
          payload.type === "js" ? payload.code : await compileJSX(payload.code);

        if (!disposed) {
          setFrameMarkup(buildSandboxDocument(frameId, compiledCode));
          setFrameHeight(320);
        }
      } catch (loadError) {
        const fallbackMessage =
          loadError instanceof Error ? loadError.message : "Unknown component loading error";
        const resolvedError =
          loadError instanceof RemoteComponentError
            ? {
                message: loadError.message,
                retriable: loadError.retriable,
                traceId: loadError.traceId
              }
            : { message: fallbackMessage, retriable: false };

        if (!disposed) {
          setError(resolvedError);
          setFrameMarkup(null);
        }
      } finally {
        if (!disposed) {
          setLoading(false);
        }
      }
    }

    void load();

    return () => {
      disposed = true;
    };
  }, [allowUnsafeExecution, bookId, chapterIndex, frameId]);

  if (loading) {
    return <FallbackCard text="Loading interactive component..." />;
  }

  if (error) {
    return (
      <FallbackCard
        onRetry={error.retriable ? () => setReloadNonce((value) => value + 1) : undefined}
        retriable={error.retriable}
        text={error.message}
        traceId={error.traceId}
      />
    );
  }

  if (!frameMarkup) {
    return <FallbackCard text="No component available." />;
  }

  return (
    <iframe
      className="w-full rounded-3xl border border-white/60 bg-white shadow-panel"
      ref={iframeRef}
      sandbox="allow-scripts"
      srcDoc={frameMarkup}
      style={{ minHeight: frameHeight }}
      title={`Sandboxed component ${bookId}-${chapterIndex}`}
    />
  );
}

export function DynamicComponent({
  bookId,
  chapterIndex = 0,
  inlineCode,
  allowUnsafeExecution = false
}: DynamicComponentProps) {
  if (bookId && inlineCode == null) {
    return (
      <SandboxedRemoteComponent
        allowUnsafeExecution={allowUnsafeExecution}
        bookId={bookId}
        chapterIndex={chapterIndex}
      />
    );
  }

  return <LocalDynamicComponent inlineCode={inlineCode} />;
}

function LocalDynamicComponent({ inlineCode }: { inlineCode?: string }) {
  const [component, setComponent] = useState<ComponentType | null>(null);
  const [error, setError] = useState<LoaderError | null>(null);
  const [loading, setLoading] = useState(true);
  const [reloadNonce, setReloadNonce] = useState(0);

  useEffect(() => {
    let disposed = false;

    async function load() {
      setLoading(true);
      setError(null);
      setComponent(null);

      try {
        const payload =
          inlineCode != null
            ? { type: "jsx" as const, code: inlineCode }
            : { type: "jsx" as const, code: demoComponentCode };

        const resolvedComponent = await instantiateComponent(payload.code, payload.type);

        if (!disposed) {
          setComponent(() => resolvedComponent);
        }
      } catch (loadError) {
        const fallbackMessage =
          loadError instanceof Error ? loadError.message : "Unknown component loading error";

        if (!disposed) {
          setComponent(null);
          setError({ message: fallbackMessage, retriable: false });
        }
      } finally {
        if (!disposed) {
          setLoading(false);
        }
      }
    }

    void load();

    return () => {
      disposed = true;
    };
  }, [inlineCode, reloadNonce]);

  if (loading) {
    return <FallbackCard text="Loading interactive component..." />;
  }

  if (error) {
    return (
      <FallbackCard
        onRetry={error.retriable ? () => setReloadNonce((value) => value + 1) : undefined}
        retriable={error.retriable}
        text={error.message}
        traceId={error.traceId}
      />
    );
  }

  if (!component) {
    return <FallbackCard text="No component available." />;
  }

  const ResolvedComponent = component;

  return (
    <Suspense fallback={<FallbackCard text="Rendering interactive component..." />}>
      <ResolvedComponent />
    </Suspense>
  );
}
