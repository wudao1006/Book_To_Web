import { useState, useEffect, useRef } from 'react';
import { X, FileText, Activity, GitBranch, ChevronRight, RotateCcw, Loader2, Circle, CheckCircle2, AlertCircle } from 'lucide-react';

interface Chapter {
  index: number;
  title: string;
  status: 'pending' | 'running' | 'succeeded' | 'failed' | 'retrying';
}

interface Version {
  version_num: number;
  is_latest: boolean;
  is_stable: boolean;
  created_at: string;
}

interface SidePanelProps {
  isOpen: boolean;
  onClose: () => void;
  chapters: Chapter[];
  versions: Version[];
  currentChapterIndex?: number;
  onSelectChapter: (index: number) => void;
  onGenerate: (index: number) => void;
  onRollback: () => void;
  isGenerating: boolean;
  activeTab?: 'chapters' | 'status' | 'versions';
}

export function SidePanel({
  isOpen,
  onClose,
  chapters,
  versions,
  currentChapterIndex,
  onSelectChapter,
  onGenerate,
  onRollback,
  isGenerating,
  activeTab = 'chapters',
}: SidePanelProps) {
  const [currentTab, setCurrentTab] = useState<'chapters' | 'status' | 'versions'>(activeTab);

  useEffect(() => {
    function handleEscape(e: KeyboardEvent) {
      if (e.key === 'Escape') onClose();
    }
    if (isOpen) {
      document.addEventListener('keydown', handleEscape);
      document.body.style.overflow = 'hidden';
    }
    return () => {
      document.removeEventListener('keydown', handleEscape);
      document.body.style.overflow = '';
    };
  }, [isOpen]);

  return (
    <>
      {/* Backdrop */}
      <div
        className={`fixed inset-0 bg-ink/20 backdrop-blur-sm z-40 transition-opacity duration-300
          ${isOpen ? 'opacity-100' : 'opacity-0 pointer-events-none'}`}
        onClick={onClose}
      />

      {/* Panel */}
      <div
        className={`fixed top-0 right-0 h-full w-80 bg-warm-100 z-50
          transform transition-transform duration-300 ease-out
          flex flex-col
          ${isOpen ? 'translate-x-0' : 'translate-x-full'}`}
        style={{ boxShadow: isOpen ? '-4px 0 24px rgba(44, 36, 22, 0.15)' : 'none' }}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-5 border-b border-warm-200">
          <div className="flex items-center gap-2">
            <span className="font-display text-lg font-semibold text-ink">章节管理</span>
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 rounded-lg bg-cream/50 flex items-center justify-center
              hover:bg-cream transition-colors duration-200"
            aria-label="关闭"
          >
            <X className="w-4 h-4 text-muted" />
          </button>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-warm-200">
          <TabButton
            active={currentTab === 'chapters'}
            onClick={() => setCurrentTab('chapters')}
            icon={<FileText className="w-4 h-4" />}
            label="章节"
          />
          <TabButton
            active={currentTab === 'status'}
            onClick={() => setCurrentTab('status')}
            icon={<Activity className="w-4 h-4" />}
            label="状态"
          />
          <TabButton
            active={currentTab === 'versions'}
            onClick={() => setCurrentTab('versions')}
            icon={<GitBranch className="w-4 h-4" />}
            label="版本"
          />
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto">
          {currentTab === 'chapters' && (
            <ChaptersTab
              chapters={chapters}
              currentIndex={currentChapterIndex}
              onSelect={onSelectChapter}
            />
          )}
          {currentTab === 'status' && (
            <StatusTab
              chapters={chapters}
              currentIndex={currentChapterIndex}
              onGenerate={onGenerate}
              isGenerating={isGenerating}
            />
          )}
          {currentTab === 'versions' && (
            <VersionsTab
              versions={versions}
              onRollback={onRollback}
            />
          )}
        </div>
      </div>
    </>
  );
}

interface TabButtonProps {
  active: boolean;
  onClick: () => void;
  icon: React.ReactNode;
  label: string;
}

function TabButton({ active, onClick, icon, label }: TabButtonProps) {
  return (
    <button
      onClick={onClick}
      className={`flex-1 flex items-center justify-center gap-2 py-3 text-sm font-medium
        transition-colors duration-200
        ${active
          ? 'text-warm-500 bg-warm-300/20 border-b-2 border-warm-300'
          : 'text-muted hover:text-ink hover:bg-warm-200/50'
        }`}
    >
      {icon}
      <span>{label}</span>
    </button>
  );
}

interface ChaptersTabProps {
  chapters: Chapter[];
  currentIndex?: number;
  onSelect: (index: number) => void;
}

function ChaptersTab({ chapters, currentIndex, onSelect }: ChaptersTabProps) {
  return (
    <div className="p-3 space-y-1">
      {chapters.length === 0 ? (
        <EmptyState message="暂无章节" subMessage="请先上传书籍" />
      ) : (
        chapters.map((chapter) => (
          <ChapterListItem
            key={chapter.index}
            chapter={chapter}
            isSelected={chapter.index === currentIndex}
            onClick={() => onSelect(chapter.index)}
          />
        ))
      )}
    </div>
  );
}

interface ChapterListItemProps {
  chapter: Chapter;
  isSelected: boolean;
  onClick: () => void;
}

function ChapterListItem({ chapter, isSelected, onClick }: ChapterListItemProps) {
  return (
    <button
      onClick={onClick}
      className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl
        text-left transition-all duration-200 group
        ${isSelected
          ? 'bg-warm-300/20 border-l-4 border-warm-300'
          : 'bg-cream/50 hover:bg-cream border-l-4 border-transparent hover:border-warm-200'
        }`}
    >
      <span className="text-sm text-muted-light font-mono w-6">
        {chapter.index + 1}
      </span>
      <span className={`flex-1 truncate text-sm ${isSelected ? 'font-medium text-ink' : 'text-ink'}`}>
        {chapter.title || `章节 ${chapter.index + 1}`}
      </span>
      <StatusIcon status={chapter.status} />
    </button>
  );
}

function StatusIcon({ status }: { status: Chapter['status'] }) {
  switch (status) {
    case 'succeeded':
      return <CheckCircle2 className="w-4 h-4 text-moss flex-shrink-0" />;
    case 'failed':
      return <AlertCircle className="w-4 h-4 text-brick flex-shrink-0" />;
    case 'running':
    case 'retrying':
      return <Loader2 className="w-4 h-4 text-warm-400 flex-shrink-0 animate-spin" />;
    default:
      return <Circle className="w-4 h-4 text-warm-200 flex-shrink-0" />;
  }
}

interface StatusTabProps {
  chapters: Chapter[];
  currentIndex?: number;
  onGenerate: (index: number) => void;
  isGenerating: boolean;
}

function StatusTab({ chapters, currentIndex, onGenerate, isGenerating }: StatusTabProps) {
  const currentChapter = currentIndex !== undefined ? chapters.find(c => c.index === currentIndex) : undefined;

  return (
    <div className="p-4 space-y-4">
      {currentChapter ? (
        <>
          <div className="bg-cream/50 rounded-2xl p-4">
            <p className="text-xs text-muted uppercase tracking-wider mb-2">当前章节</p>
            <p className="font-display text-lg text-ink">{currentChapter.title || `章节 ${currentChapter.index + 1}`}</p>
          </div>

          <div className="bg-cream/50 rounded-2xl p-4">
            <p className="text-xs text-muted uppercase tracking-wider mb-3">生成状态</p>
            <div className="flex items-center gap-3">
              <div className={`w-10 h-10 rounded-xl flex items-center justify-center
                ${currentChapter.status === 'succeeded' ? 'bg-moss/20' :
                  currentChapter.status === 'failed' ? 'bg-brick/20' :
                  currentChapter.status === 'running' ? 'bg-warm-300/20' :
                  'bg-warm-200'}`}>
                <StatusIcon status={currentChapter.status} />
              </div>
              <div>
                <p className="text-sm font-medium text-ink">
                  {currentChapter.status === 'pending' && '待生成'}
                  {currentChapter.status === 'running' && '生成中...'}
                  {currentChapter.status === 'succeeded' && '已完成'}
                  {currentChapter.status === 'failed' && '生成失败'}
                  {currentChapter.status === 'retrying' && '重试中...'}
                </p>
                <p className="text-xs text-muted">
                  {currentChapter.status === 'succeeded' ? '交互组件已就绪' : '点击生成交互组件'}
                </p>
              </div>
            </div>
          </div>

          <button
            onClick={() => onGenerate(currentChapter.index)}
            disabled={isGenerating || currentChapter.status === 'running'}
            className="w-full flex items-center justify-center gap-2
              py-3 px-4 rounded-xl
              bg-warm-300 hover:bg-warm-400 disabled:bg-warm-200
              text-white font-medium
              transition-all duration-200
              hover:shadow-glow active:scale-[0.98] disabled:hover:shadow-none disabled:active:scale-100"
          >
            {isGenerating || currentChapter.status === 'running' ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>生成中...</span>
              </>
            ) : currentChapter.status === 'succeeded' ? (
              <>
                <RotateCcw className="w-4 h-4" />
                <span>重新生成</span>
              </>
            ) : (
              <>
                <Activity className="w-4 h-4" />
                <span>生成交互组件</span>
              </>
            )}
          </button>
        </>
      ) : (
        <EmptyState message="请选择章节" subMessage="从章节列表中选择要处理的章节" />
      )}
    </div>
  );
}

interface VersionsTabProps {
  versions: Version[];
  onRollback: () => void;
}

function VersionsTab({ versions, onRollback }: VersionsTabProps) {
  const latest = versions.find(v => v.is_latest);
  const stable = versions.find(v => v.is_stable);

  return (
    <div className="p-4 space-y-4">
      {versions.length === 0 ? (
        <EmptyState message="暂无版本" subMessage="生成组件后将创建版本" />
      ) : (
        <>
          <div className="space-y-3">
            {versions.map((version) => (
              <div
                key={version.version_num}
                className={`p-4 rounded-xl border transition-all duration-200
                  ${version.is_latest
                    ? 'bg-warm-300/20 border-warm-300'
                    : 'bg-cream/50 border-transparent hover:bg-cream'
                  }`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="font-display text-lg">v{version.version_num}</span>
                    <div className="flex gap-1">
                      {version.is_latest && (
                        <span className="px-2 py-0.5 rounded-full bg-warm-300 text-white text-xs">
                          latest
                        </span>
                      )}
                      {version.is_stable && (
                        <span className="px-2 py-0.5 rounded-full bg-moss text-white text-xs">
                          stable
                        </span>
                      )}
                    </div>
                  </div>
                  <span className="text-xs text-muted">
                    {new Date(version.created_at).toLocaleDateString()}
                  </span>
                </div>
              </div>
            ))}
          </div>

          {latest && stable && latest.version_num !== stable.version_num && (
            <button
              onClick={onRollback}
              className="w-full flex items-center justify-center gap-2
                py-3 px-4 rounded-xl
                border-2 border-warm-300 text-warm-500
                hover:bg-warm-300 hover:text-white
                font-medium transition-all duration-200"
            >
              <RotateCcw className="w-4 h-4" />
              <span>回滚到稳定版本</span>
            </button>
          )}
        </>
      )}
    </div>
  );
}

function EmptyState({ message, subMessage }: { message: string; subMessage: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-12 text-center px-6">
      <div className="w-12 h-12 rounded-2xl bg-warm-200/50 flex items-center justify-center mb-3">
        <FileText className="w-6 h-6 text-warm-400" />
      </div>
      <p className="text-muted text-sm">{message}</p>
      <p className="text-muted-light text-xs mt-1">{subMessage}</p>
    </div>
  );
}
