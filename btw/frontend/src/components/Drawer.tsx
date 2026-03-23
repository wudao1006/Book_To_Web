import { useEffect, useRef } from 'react';
import { X, BookOpen, Upload, Plus, ChevronRight } from 'lucide-react';

interface Book {
  id: string;
  title: string;
  author?: string;
  status?: 'pending' | 'parsed' | 'ready';
}

interface DrawerProps {
  isOpen: boolean;
  onClose: () => void;
  books: Book[];
  currentBookId?: string;
  onSelectBook: (bookId: string) => void;
  onUploadClick: () => void;
}

export function Drawer({
  isOpen,
  onClose,
  books,
  currentBookId,
  onSelectBook,
  onUploadClick,
}: DrawerProps) {
  const drawerRef = useRef<HTMLDivElement>(null);

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

      {/* Drawer Panel */}
      <div
        ref={drawerRef}
        className={`fixed top-0 left-0 h-full w-80 bg-warm-100 z-50
          transform transition-transform duration-300 ease-out
          flex flex-col
          ${isOpen ? 'translate-x-0' : '-translate-x-full'}`}
        style={{ boxShadow: isOpen ? '4px 0 24px rgba(44, 36, 22, 0.15)' : 'none' }}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-5 border-b border-warm-200">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-warm-300/30 flex items-center justify-center">
              <BookOpen className="w-4 h-4 text-warm-500" />
            </div>
            <span className="font-display text-lg font-semibold text-ink">我的书籍</span>
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

        {/* Book List */}
        <div className="flex-1 overflow-y-auto py-4 px-3">
          {books.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-40 text-center px-6">
              <div className="w-12 h-12 rounded-2xl bg-warm-200/50 flex items-center justify-center mb-3">
                <BookOpen className="w-6 h-6 text-warm-400" />
              </div>
              <p className="text-muted text-sm">
                还没有书籍
              </p>
              <p className="text-muted-light text-xs mt-1">
                点击下方按钮上传
              </p>
            </div>
          ) : (
            <div className="space-y-2">
              {books.map((book) => (
                <BookListItem
                  key={book.id}
                  book={book}
                  isSelected={book.id === currentBookId}
                  onClick={() => {
                    onSelectBook(book.id);
                    onClose();
                  }}
                />
              ))}
            </div>
          )}
        </div>

        {/* Footer - Upload Button */}
        <div className="p-4 border-t border-warm-200">
          <button
            onClick={onUploadClick}
            className="w-full flex items-center justify-center gap-2
              py-3 px-4 rounded-xl
              bg-warm-300 hover:bg-warm-400
              text-white font-medium
              transition-all duration-200
              hover:shadow-glow active:scale-[0.98]"
          >
            <Upload className="w-4 h-4" />
            <span>上传新书</span>
          </button>
        </div>
      </div>
    </>
  );
}

interface BookListItemProps {
  book: Book;
  isSelected: boolean;
  onClick: () => void;
}

function BookListItem({ book, isSelected, onClick }: BookListItemProps) {
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
      <div className={`flex-shrink-0 w-10 h-14 rounded-md shadow-soft flex items-center justify-center
        ${isSelected ? 'bg-warm-300 text-white' : 'bg-warm-200 text-warm-500'}`}>
        <BookOpen className="w-5 h-5" />
      </div>
      <div className="flex-1 min-w-0">
        <p className={`font-medium truncate ${isSelected ? 'text-ink' : 'text-ink'}`}>
          {book.title}
        </p>
        {book.author && (
          <p className="text-xs text-muted truncate">
            {book.author}
          </p>
        )}
      </div>
      <ChevronRight className={`w-4 h-4 flex-shrink-0 transition-colors
        ${isSelected ? 'text-warm-400' : 'text-warm-200 group-hover:text-warm-300'}`} />
    </button>
  );
}
