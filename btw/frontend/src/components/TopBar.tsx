import { Menu, BookOpen, Layers, User } from 'lucide-react';

interface TopBarProps {
  bookTitle?: string;
  onOpenDrawer: () => void;
  onOpenPanel: () => void;
}

export function TopBar({ bookTitle, onOpenDrawer, onOpenPanel }: TopBarProps) {
  return (
    <header className="fixed top-0 left-0 right-0 h-16 glass border-b border-warm-200 z-40">
      <div className="h-full px-6 flex items-center justify-between max-w-screen-2xl mx-auto">
        {/* Left - Drawer Toggle */}
        <button
          onClick={onOpenDrawer}
          className="flex items-center gap-3 group"
          aria-label="打开书籍列表"
        >
          <div className="w-10 h-10 rounded-xl bg-warm-100 flex items-center justify-center
            group-hover:bg-warm-200 transition-colors duration-200">
            <Menu className="w-5 h-5 text-ink" />
          </div>
          <span className="hidden sm:flex items-center gap-2">
            <span className="font-display text-xl font-semibold text-ink tracking-tight">
              BTW
            </span>
          </span>
        </button>

        {/* Center - Current Book Title */}
        <div className="flex-1 flex justify-center px-4">
          {bookTitle ? (
            <div className="flex items-center gap-2 text-ink">
              <BookOpen className="w-4 h-4 text-warm-400" />
              <span className="font-display text-lg font-medium truncate max-w-[200px] sm:max-w-md">
                {bookTitle}
              </span>
            </div>
          ) : (
            <span className="font-display text-lg text-muted-light italic">
              选择一本书开始
            </span>
          )}
        </div>

        {/* Right - Chapter Panel Toggle */}
        <div className="flex items-center gap-2">
          <button
            onClick={onOpenPanel}
            className="flex items-center gap-2 px-4 py-2 rounded-xl
              bg-warm-100 hover:bg-warm-200
              text-ink text-sm font-medium
              transition-all duration-200
              active:scale-95"
            aria-label="打开章节面板"
          >
            <Layers className="w-4 h-4" />
            <span className="hidden sm:inline">章节</span>
          </button>

          <button
            className="w-10 h-10 rounded-xl bg-warm-100 flex items-center justify-center
              hover:bg-warm-200 transition-colors duration-200 ml-1"
            aria-label="用户设置"
          >
            <User className="w-5 h-5 text-ink" />
          </button>
        </div>
      </div>
    </header>
  );
}
