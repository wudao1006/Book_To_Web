import { Suspense, useEffect, useState } from "react";
import type { ComponentType } from "react";
import * as React from "react";
import { compileJSX } from "./BabelCompiler";

type ComponentPayload = {
  type: "js" | "jsx";
  code: string;
};

type DynamicComponentProps = {
  bookId?: string;
  chapterIndex?: number;
  inlineCode?: string;
};

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

function FallbackCard({ text }: { text: string }) {
  return (
    <div className={fallbackClassName}>
      <p>{text}</p>
    </div>
  );
}

async function readRemoteComponent(bookId: string, chapterIndex: number): Promise<ComponentPayload> {
  const response = await fetch(`/api/books/${bookId}/chapters/${chapterIndex}/component`);

  if (!response.ok) {
    if (response.status === 404) {
      throw new Error("Component not generated yet.");
    }

    throw new Error(`Failed to load component: ${response.status}`);
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

export function DynamicComponent({
  bookId,
  chapterIndex = 0,
  inlineCode
}: DynamicComponentProps) {
  const [component, setComponent] = useState<ComponentType | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let disposed = false;

    async function load() {
      setLoading(true);
      setError(null);

      try {
        const payload =
          inlineCode != null
            ? { type: "jsx" as const, code: inlineCode }
            : bookId
              ? await readRemoteComponent(bookId, chapterIndex)
              : { type: "jsx" as const, code: demoComponentCode };

        const resolvedComponent = await instantiateComponent(payload.code, payload.type);

        if (!disposed) {
          setComponent(() => resolvedComponent);
        }
      } catch (loadError) {
        const message =
          loadError instanceof Error ? loadError.message : "Unknown component loading error";

        if (!disposed) {
          setComponent(null);
          setError(message);
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
  }, [bookId, chapterIndex, inlineCode]);

  if (loading) {
    return <FallbackCard text="Loading interactive component..." />;
  }

  if (error) {
    return <FallbackCard text={error} />;
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
