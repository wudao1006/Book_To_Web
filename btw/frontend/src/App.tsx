import { useEffect, useState, useCallback } from 'react';
import { TopBar } from './components/TopBar';
import { Drawer } from './components/Drawer';
import { SidePanel } from './components/SidePanel';
import { ContentView } from './components/ContentView';

// Types matching the backend API
interface Book {
  id: string;
  title: string;
  author?: string;
  status?: 'pending' | 'parsed' | 'ready';
}

interface Chapter {
  index_num: number;
  title: string;
}

interface VersionInfo {
  version_num: number;
  is_latest: boolean;
  is_stable: boolean;
  bundle_size: number;
  created_at: string;
}

interface TaskStep {
  stage: string;
  status: string;
  error_code?: string | null;
  error_message?: string | null;
}

interface ApiError {
  code: string;
  message: string;
  stage: string;
  retriable: boolean;
  trace_id: string;
}

function App() {
  // UI State
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [isSidePanelOpen, setIsSidePanelOpen] = useState(false);

  // Data State
  const [books, setBooks] = useState<Book[]>([]);
  const [currentBookId, setCurrentBookId] = useState<string | undefined>();
  const [chapters, setChapters] = useState<Chapter[]>([]);
  const [currentChapterIndex, setCurrentChapterIndex] = useState<number>(0);
  const [versions, setVersions] = useState<VersionInfo[]>([]);
  const [currentChapterContent, setCurrentChapterContent] = useState<string | undefined>();

  // Settings
  const [allowUnsafeExecution, setAllowUnsafeExecution] = useState(false);
  const [versionMode, setVersionMode] = useState<'latest' | 'stable'>('latest');

  // Generation State
  const [isGenerating, setIsGenerating] = useState(false);
  const [taskId, setTaskId] = useState<string | null>(null);
  const [taskSteps, setTaskSteps] = useState<TaskStep[]>([]);
  const [taskStatus, setTaskStatus] = useState<string>('idle');
  const [taskMessage, setTaskMessage] = useState<string>('');

  const currentBook = books.find(b => b.id === currentBookId);
  const currentChapter = chapters.find(c => c.index_num === currentChapterIndex);

  // Load books list
  useEffect(() => {
    // In real implementation: fetch('/api/books')
    // For now, we'll keep the UI functional even without backend data
    setBooks([]);
  }, []);

  // Load chapters when book changes
  useEffect(() => {
    if (!currentBookId) {
      setChapters([]);
      setCurrentChapterIndex(0);
      return;
    }

    async function loadChapters() {
      try {
        const response = await fetch(`/api/books/${currentBookId}/chapters`);
        if (!response.ok) throw new Error('Failed to load chapters');
        const data = await response.json();
        setChapters(data.chapters || []);
        setCurrentChapterIndex(0);
      } catch (err) {
        console.error('Failed to load chapters:', err);
        setChapters([]);
      }
    }

    loadChapters();
  }, [currentBookId]);

  // Load chapter content
  useEffect(() => {
    if (!currentBookId || !currentChapter) {
      setCurrentChapterContent(undefined);
      return;
    }
    const chapterIndex = currentChapter.index_num;

    async function loadContent() {
      try {
        const response = await fetch(
          `/api/books/${currentBookId}/chapters/${chapterIndex}/content`
        );
        if (response.ok) {
          const data = await response.json() as { content?: string };
          setCurrentChapterContent(data.content);
          return;
        }
        setCurrentChapterContent(undefined);
      } catch (err) {
        console.error('Failed to load content:', err);
        setCurrentChapterContent(undefined);
      }
    }

    loadContent();
  }, [currentBookId, currentChapter]);

  // Load versions
  const loadVersions = useCallback(async (bookId: string, chapterIndex: number) => {
    try {
      const response = await fetch(`/api/books/${bookId}/chapters/${chapterIndex}/versions`);
      if (!response.ok) throw new Error('Failed to load versions');
      const data = await response.json();
      setVersions(data.versions || []);
    } catch (err) {
      console.error('Failed to load versions:', err);
      setVersions([]);
    }
  }, []);

  // Load versions when book/chapter changes
  useEffect(() => {
    if (currentBookId) {
      loadVersions(currentBookId, currentChapterIndex);
    }
  }, [currentBookId, currentChapterIndex, loadVersions]);

  // Poll task status
  useEffect(() => {
    if (!taskId) return;

    let cancelled = false;
    const terminal = new Set(['succeeded', 'failed', 'cancelled']);

    async function pollTask() {
      const [taskRes, stepsRes] = await Promise.all([
        fetch(`/api/tasks/${taskId}`),
        fetch(`/api/tasks/${taskId}/steps`)
      ]);

      if (!taskRes.ok || !stepsRes.ok) return;

      const [taskData, stepsData] = await Promise.all([
        taskRes.json(),
        stepsRes.json()
      ]);

      if (cancelled) return;

      setTaskStatus(taskData.status);
      setTaskSteps(stepsData.steps || []);
      setTaskMessage(taskData.error_message || '');

      if (taskData.status && terminal.has(taskData.status)) {
        setTaskId(null);
        setIsGenerating(false);
        if (currentBookId) {
          loadVersions(currentBookId, currentChapterIndex);
        }
      }
    }

    pollTask();
    const interval = window.setInterval(pollTask, 1000);

    return () => {
      cancelled = true;
      window.clearInterval(interval);
    };
  }, [taskId, currentBookId, currentChapterIndex, loadVersions]);

  const handleGenerate = useCallback(async (chapterIndex: number) => {
    if (!currentBookId) return;

    setIsGenerating(true);
    setTaskStatus('running');
    setTaskMessage('准备生成...');

    try {
      const response = await fetch(
        `/api/books/${currentBookId}/chapters/${chapterIndex}/generate`,
        { method: 'POST' }
      );

      if (!response.ok) {
        const error = await response.json() as ApiError;
        setTaskStatus('failed');
        setTaskMessage(error.message || '生成失败');
        setIsGenerating(false);
        return;
      }

      const result = await response.json() as { task_id: string };
      setTaskId(result.task_id);
    } catch (err) {
      setTaskStatus('failed');
      setTaskMessage('网络错误或服务器不可用');
      setIsGenerating(false);
    }
  }, [currentBookId]);

  const handleRollback = useCallback(async () => {
    if (!currentBookId) return;

    try {
      const response = await fetch(
        `/api/books/${currentBookId}/chapters/${currentChapterIndex}/rollback`,
        { method: 'POST' }
      );

      if (!response.ok) {
        throw new Error('Rollback failed');
      }

      setVersionMode('latest');
      await loadVersions(currentBookId, currentChapterIndex);
    } catch (err) {
      console.error('Rollback failed:', err);
    }
  }, [currentBookId, currentChapterIndex, loadVersions]);

  const handleUploadClick = useCallback(() => {
    // Create a hidden file input
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.txt,.md,.markdown,.pdf';
    input.onchange = async () => {
      const file = input.files?.[0];
      if (!file) return;

      const formData = new FormData();
      formData.append('file', file);
      formData.append('title', file.name.replace(/\.[^/.]+$/, ''));

      try {
        const response = await fetch('/api/books/upload', {
          method: 'POST',
          body: formData,
        });

        if (!response.ok) throw new Error('Upload failed');

        const result = await response.json() as { book_id: string };
        // Refresh books list and select the new book
        const booksResponse = await fetch('/api/books');
        if (booksResponse.ok) {
          const data = await booksResponse.json();
          setBooks(data.books || []);
          setCurrentBookId(result.book_id);
        }
      } catch (err) {
        console.error('Upload failed:', err);
        alert('上传失败，请重试');
      }
    };
    input.click();
  }, []);

  // Map chapters to include status from task steps
  const chaptersWithStatus = chapters.map(ch => {
    const step = taskSteps.find(s => s.stage === 'compile');
    let status: 'pending' | 'running' | 'succeeded' | 'failed' | 'retrying' = 'pending';
    if (taskStatus === 'running' && currentChapterIndex === ch.index_num) {
      status = step?.status === 'running' ? 'running' : 'pending';
    } else if (ch.index_num === currentChapterIndex && taskStatus === 'succeeded') {
      status = 'succeeded';
    } else if (ch.index_num === currentChapterIndex && taskStatus === 'failed') {
      status = 'failed';
    }
    return { ...ch, index: ch.index_num, status };
  });

  return (
    <div className="min-h-screen bg-cream">
      {/* Top Navigation Bar */}
      <TopBar
        bookTitle={currentBook?.title}
        onOpenDrawer={() => setIsDrawerOpen(true)}
        onOpenPanel={() => setIsSidePanelOpen(true)}
      />

      {/* Left Drawer - Book List */}
      <Drawer
        isOpen={isDrawerOpen}
        onClose={() => setIsDrawerOpen(false)}
        books={books}
        currentBookId={currentBookId}
        onSelectBook={setCurrentBookId}
        onUploadClick={handleUploadClick}
      />

      {/* Right Side Panel - Chapters/Status/Versions */}
      <SidePanel
        isOpen={isSidePanelOpen}
        onClose={() => setIsSidePanelOpen(false)}
        chapters={chaptersWithStatus}
        versions={versions}
        currentChapterIndex={currentChapterIndex}
        onSelectChapter={setCurrentChapterIndex}
        onGenerate={handleGenerate}
        onRollback={handleRollback}
        isGenerating={isGenerating}
      />

      {/* Main Content Area */}
      <main className="pt-16 h-screen">
        <ContentView
          bookId={currentBookId}
          chapter={currentChapter ? {
            index: currentChapter.index_num,
            title: currentChapter.title,
            content: currentChapterContent
          } : undefined}
          allowUnsafeExecution={allowUnsafeExecution}
          onAllowUnsafeChange={setAllowUnsafeExecution}
          versionMode={versionMode}
        />
      </main>
    </div>
  );
}

export default App;
