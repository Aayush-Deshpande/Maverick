import React, { useState, useEffect } from 'react';
import { Header } from './components/Header';
import { Footer } from './components/Footer';
import { HomePage } from './pages/HomePage';
import { DocArticlePage } from './pages/DocArticlePage';
import { SearchModal } from './components/SearchModal';
import { ModelViewerModal } from './components/ModelViewerModal';

export const App: React.FC = () => {
  // Hash routing: e.g. #/technical/01-introducing-ps26054 or #/home or #/journey
  const [currentPath, setCurrentPath] = useState<string>(() => {
    const hash = window.location.hash.replace(/^#\/?/, '');
    return hash || 'home';
  });

  const [searchOpen, setSearchOpen] = useState(false);
  const [modelViewerOpen, setModelViewerOpen] = useState(false);

  // Sync hash changes (browser back/forward button)
  useEffect(() => {
    const handleHashChange = () => {
      const hash = window.location.hash.replace(/^#\/?/, '');
      if (hash === '3d') {
        setModelViewerOpen(true);
      } else if (hash === 'search') {
        setSearchOpen(true);
      } else {
        setCurrentPath(hash || 'home');
      }
    };

    handleHashChange();
    window.addEventListener('hashchange', handleHashChange);
    return () => window.removeEventListener('hashchange', handleHashChange);
  }, []);

  // Global keyboard shortcut for search (Cmd+K / Ctrl+K)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setSearchOpen((prev) => !prev);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const navigateTo = (path: string) => {
    setCurrentPath(path);
    window.location.hash = `/${path}`;
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const isDocArticle = currentPath.startsWith('technical/') || currentPath.startsWith('journey');

  return (
    <div className="flex flex-col min-h-screen bg-[#fafaf9] text-[#1c1917]">
      {/* Top Header */}
      <Header
        currentPath={currentPath}
        onNavigate={navigateTo}
        onOpenSearch={() => setSearchOpen(true)}
        onOpenModelViewer={() => setModelViewerOpen(true)}
      />

      {/* Main Content Area */}
      <div className="flex-1">
        {isDocArticle ? (
          <DocArticlePage slug={currentPath} onNavigate={navigateTo} />
        ) : (
          <HomePage
            onNavigate={navigateTo}
            onOpenModelViewer={() => setModelViewerOpen(true)}
          />
        )}
      </div>

      {/* Footer */}
      <Footer onNavigate={navigateTo} />

      {/* Search Modal */}
      <SearchModal
        isOpen={searchOpen}
        onClose={() => setSearchOpen(false)}
        onSelectArticle={navigateTo}
      />

      {/* 3D Model Viewer Modal */}
      <ModelViewerModal
        isOpen={modelViewerOpen}
        onClose={() => setModelViewerOpen(false)}
      />
    </div>
  );
};
export default App;
