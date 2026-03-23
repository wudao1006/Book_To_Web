import { useState, useEffect } from 'react';
import { DynamicComponent, type DynamicLoaderError } from '../renderer/DynamicLoader';
import { AlertTriangle, Shield, Sparkles, Eye, Code } from 'lucide-react';

interface Chapter {
  index: number;
  title: string;
  content?: string;
}

interface ContentViewProps {
  bookId?: string;
  chapter?: Chapter;
  allowUnsafeExecution: boolean;
  onAllowUnsafeChange: (allow: boolean) => void;
  versionMode: 'latest' | 'stable';
}

export function ContentView({
  bookId,
  chapter,
  allowUnsafeExecution,
  onAllowUnsafeChange,
  versionMode,
}: ContentViewProps) {
  const [viewMode, setViewMode] = useState<'content' | 'component'>('content');
  const [loaderError, setLoaderError] = useState<DynamicLoaderError | null>(null);

  if (!bookId || !chapter) {
    return <EmptyState />;
  }

  return (
    <div className="h-full flex flex-col">
      {/* View Toggle Bar */}
      <div className="flex items-center justify-center py-4">
        <div className="inline-flex items-center gap-1 p-1 bg-warm-100 rounded-xl">
          <ToggleButton
            active={viewMode === 'content'}
            onClick={() => setViewMode('content')}
            icon={<Eye className="w-4 h-4" />}
            label="原文"
          />
          <ToggleButton
            active={viewMode === 'component'}
            onClick={() => setViewMode('component')}
            icon={<Sparkles className="w-4 h-4" />}
            label="交互组件"
          />
        </div>
      </div>

      {/* Content Area */}
      <div className="flex-1 overflow-y-auto px-6 pb-8">
        <div className="max-w-3xl mx-auto">
          {viewMode === 'content' ? (
            <ContentViewMode chapter={chapter} />
          ) : (
            <ComponentViewMode
              bookId={bookId}
              chapterIndex={chapter.index}
              allowUnsafeExecution={allowUnsafeExecution}
              onAllowUnsafeChange={onAllowUnsafeChange}
              versionMode={versionMode}
              onErrorChange={setLoaderError}
              error={loaderError}
            />
          )}
        </div>
      </div>
    </div>
  );
}

interface ToggleButtonProps {
  active: boolean;
  onClick: () => void;
  icon: React.ReactNode;
  label: string;
}

function ToggleButton({ active, onClick, icon, label }: ToggleButtonProps) {
  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium
        transition-all duration-200
        ${active
          ? 'bg-cream text-ink shadow-soft'
          : 'text-muted hover:text-ink hover:bg-warm-200/50'
        }`}
    >
      {icon}
      <span>{label}</span>
    </button>
  );
}

function ContentViewMode({ chapter }: { chapter: Chapter }) {
  return (
    <article className="prose prose-amber max-w-none">
      <header className="mb-8 pb-6 border-b border-warm-200">
        <span className="text-xs text-muted uppercase tracking-widest">
          章节 {chapter.index + 1}
        </span>
        <h1 className="font-display text-3xl sm:text-4xl text-ink mt-2 leading-tight">
          {chapter.title || `章节 ${chapter.index + 1}`}
        </h1>
      </header>

      {chapter.content ? (
        <div className="text-ink leading-relaxed whitespace-pre-wrap">
          {chapter.content}
        </div>
      ) : (
        <div className="text-center py-12 text-muted">
          <p>此章节暂无内容</p>
        </div>
      )}
    </article>
  );
}

interface ComponentViewModeProps {
  bookId: string;
  chapterIndex: number;
  allowUnsafeExecution: boolean;
  onAllowUnsafeChange: (allow: boolean) => void;
  versionMode: 'latest' | 'stable';
  onErrorChange: (error: DynamicLoaderError | null) => void;
  error: DynamicLoaderError | null;
}

function ComponentViewMode({
  bookId,
  chapterIndex,
  allowUnsafeExecution,
  onAllowUnsafeChange,
  versionMode,
  onErrorChange,
  error,
}: ComponentViewModeProps) {
  return (
    <div className="space-y-6">
      {/* Safety Toggle */}
      {!allowUnsafeExecution && (
        <div className="bg-warm-100 border border-warm-200 rounded-2xl p-4">
          <div className="flex items-start gap-4">
            <div className="w-10 h-10 rounded-xl bg-amber-100 flex items-center justify-center flex-shrink-0">
              <Shield className="w-5 h-5 text-warm-500" />
            </div>
            <div className="flex-1">
              <h3 className="font-medium text-ink">安全模式已开启</h3>
              <p className="text-sm text-muted mt-1">
                交互组件包含 AI 生成的代码。请确认信任此内容后再启用执行。
              </p>
              <button
                onClick={() => onAllowUnsafeChange(true)}
                className="mt-3 flex items-center gap-2 px-4 py-2 rounded-xl
                  bg-warm-300 hover:bg-warm-400 text-white text-sm font-medium
                  transition-all duration-200 hover:shadow-glow"
              >
                <AlertTriangle className="w-4 h-4" />
                <span>我了解风险，允许执行</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Component Renderer */}
      <div className="bg-cream rounded-3xl p-6 paper-shadow-lg">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-warm-400" />
            <span className="text-sm font-medium text-ink">交互组件</span>
          </div>
          {allowUnsafeExecution && (
            <button
              onClick={() => onAllowUnsafeChange(false)}
              className="text-xs text-muted hover:text-ink transition-colors"
            >
              禁用执行
            </button>
          )}
        </div>

        {error ? (
          <ErrorDisplay error={error} />
        ) : (
          <DynamicComponent
            bookId={bookId}
            chapterIndex={chapterIndex}
            allowUnsafeExecution={allowUnsafeExecution}
            version={versionMode}
            onErrorChange={onErrorChange}
          />
        )}
      </div>
    </div>
  );
}

function ErrorDisplay({ error }: { error: DynamicLoaderError }) {
  return (
    <div className="bg-brick/10 border border-brick/20 rounded-2xl p-6">
      <div className="flex items-start gap-4">
        <div className="w-10 h-10 rounded-xl bg-brick/20 flex items-center justify-center">
          <AlertTriangle className="w-5 h-5 text-brick" />
        </div>
        <div>
          <h3 className="font-medium text-brick">组件加载失败</h3>
          <p className="text-sm text-brick/80 mt-1">{error.message}</p>
          {error.traceId && (
            <p className="text-xs text-muted mt-2">trace_id: {error.traceId}</p>
          )}
        </div>
      </div>
    </div>
  );
}

function EmptyState() {
  return (
    <div className="h-full flex items-center justify-center">
      <div className="text-center">
        <div className="w-20 h-20 rounded-3xl bg-warm-100 flex items-center justify-center mx-auto mb-6">
          <Code className="w-8 h-8 text-warm-400" />
        </div>
        <h2 className="font-display text-2xl text-ink mb-2">欢迎使用 BTW</h2>
        <p className="text-muted max-w-sm mx-auto">
          将书籍转化为沉浸式交互 Web 体验。
          <br />
          从左侧书籍列表中选择一本书开始阅读。
        </p>
      </div>
    </div>
  );
}
