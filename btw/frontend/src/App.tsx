import { useState } from "react";
import { DynamicComponent } from "./renderer/DynamicLoader";

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

function App() {
  const [bookId, setBookId] = useState("");
  const [chapterIndex, setChapterIndex] = useState(0);
  const [useApi, setUseApi] = useState(false);
  const [allowUnsafeExecution, setAllowUnsafeExecution] = useState(false);

  return (
    <div className="min-h-screen text-ink">
      <main className="mx-auto flex min-h-screen max-w-6xl flex-col gap-8 px-4 py-8 sm:px-6 lg:px-8">
        <section className="overflow-hidden rounded-[2rem] border border-white/50 bg-white/65 shadow-panel backdrop-blur">
          <div className="grid gap-8 p-8 lg:grid-cols-[1.2fr_0.8fr] lg:p-12">
            <div>
              <p className="text-xs uppercase tracking-[0.35em] text-ember">Book To Web</p>
              <h1 className="mt-4 max-w-3xl font-display text-4xl leading-tight text-ink sm:text-5xl">
                A minimal shell for AI-generated chapters that can render before the API exists.
              </h1>
              <p className="mt-6 max-w-2xl text-base leading-8 text-slate-700">
                This frontend keeps two modes alive: local demo rendering for development and API
                component loading for the eventual Director pipeline.
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
                <p className="text-sm leading-6 text-slate-600">
                  With API mode off, the page renders local JSX immediately. With it on, the
                  loader fetches `/api/books/:bookId/chapters/:chapterIndex/component`.
                </p>
              </div>
            </aside>
          </div>
        </section>

        <section className="grid gap-6 lg:grid-cols-[0.72fr_1fr]">
          <article className="rounded-[2rem] border border-white/50 bg-white/65 p-6 shadow-panel backdrop-blur">
            <p className="text-xs uppercase tracking-[0.3em] text-ember">Status</p>
            <ul className="mt-5 space-y-4 text-sm leading-7 text-slate-700">
              <li>Vite + React + TypeScript skeleton is in place.</li>
              <li>Babel-based runtime compilation supports raw JSX strings.</li>
              <li>The renderer can work in demo mode without waiting for backend availability.</li>
            </ul>
          </article>

          <section className="space-y-4">
            <p className="text-xs uppercase tracking-[0.3em] text-pine">Renderer preview</p>
            <DynamicComponent
              allowUnsafeExecution={allowUnsafeExecution}
              bookId={useApi ? bookId : undefined}
              chapterIndex={chapterIndex}
              inlineCode={useApi ? undefined : sampleChapterCode}
            />
          </section>
        </section>
      </main>
    </div>
  );
}

export default App;
