import React, { useEffect, useState, useMemo } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { ChevronRight, ArrowLeft, ArrowRight, BookOpen, Clock, Layers, ShieldCheck, Check, Copy } from 'lucide-react';
import { DocArticle, technicalNavGroups, journeyNavGroups, articleBySlug, technicalArticles, journeyArticles } from '../lib/content';
import { MermaidDiagram } from '../components/MermaidDiagram';

interface DocArticlePageProps {
  slug: string;
  onNavigate: (slug: string) => void;
}

export const DocArticlePage: React.FC<DocArticlePageProps> = ({ slug, onNavigate }) => {
  const [activeHeadingId, setActiveHeadingId] = useState<string>('');
  const [copiedCodeId, setCopiedCodeId] = useState<string | null>(null);
  const [mobileNavOpen, setMobileNavOpen] = useState<boolean>(false);

  const article = useMemo(() => {
    return articleBySlug.get(slug) || technicalArticles[0];
  }, [slug]);

  const isJourney = slug.startsWith('journey');
  const navGroups = isJourney ? journeyNavGroups : technicalNavGroups;

  // Find previous and next articles in the active track
  const currentList = isJourney ? journeyArticles : technicalArticles;
  const currentIndex = currentList.findIndex((a) => a.slug === article.slug);
  const prevArticle = currentIndex > 0 ? currentList[currentIndex - 1] : null;
  const nextArticle = currentIndex >= 0 && currentIndex < currentList.length - 1 ? currentList[currentIndex + 1] : null;

  // Scroll to top on slug change
  useEffect(() => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
    setMobileNavOpen(false);
  }, [slug]);

  // Track active heading on scroll
  useEffect(() => {
    const handleScroll = () => {
      const headingElements = article.headings
        .map((h) => document.getElementById(h.id))
        .filter(Boolean) as HTMLElement[];

      const scrollPosition = window.scrollY + 120;

      for (let i = headingElements.length - 1; i >= 0; i--) {
        const el = headingElements[i];
        if (el.offsetTop <= scrollPosition) {
          setActiveHeadingId(el.id);
          return;
        }
      }
      if (headingElements.length > 0) {
        setActiveHeadingId(headingElements[0].id);
      }
    };

    window.addEventListener('scroll', handleScroll, { passive: true });
    handleScroll();
    return () => window.removeEventListener('scroll', handleScroll);
  }, [article]);

  // Clean Markdown content for ReactMarkdown: remove the initial # Title line if present since we render our own header
  const markdownBody = useMemo(() => {
    return article.content.replace(/^#\s+[^\n]+\n+/, '');
  }, [article]);

  const handleCopyCode = (code: string, id: string) => {
    navigator.clipboard.writeText(code);
    setCopiedCodeId(id);
    setTimeout(() => setCopiedCodeId(null), 2000);
  };

  const resolveTargetSlug = (href: string): string | null => {
    if (!href) return null;
    if (href.startsWith('http://') || href.startsWith('https://') || href.startsWith('mailto:') || href.startsWith('#')) {
      return null;
    }
    let clean = href.replace(/\.md$/, '').replace(/^\.\//, '');
    while (clean.startsWith('../')) {
      clean = clean.replace(/^\.\.\//, '');
    }
    if (clean.startsWith('technical/') || clean.startsWith('journey/')) {
      return clean;
    }
    const journeyKeywords = ['genesis', 'pitch', 'evaluat', 'audit', 'correct', 'retract', 'defen', 'roadmap', 'prep'];
    if (journeyKeywords.some((k) => clean.toLowerCase().includes(k))) {
      return `journey/${clean}`;
    }
    return isJourney ? `journey/${clean}` : `technical/${clean}`;
  };

  const handleLinkClick = (e: React.MouseEvent, href: string) => {
    if (!href) return;
    if (href.startsWith('#')) {
      e.preventDefault();
      const el = document.getElementById(href.replace(/^#/, ''));
      if (el) {
        el.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
      return;
    }
    const resolved = resolveTargetSlug(href);
    if (resolved) {
      e.preventDefault();
      onNavigate(resolved);
    }
  };

  return (
    <div className="min-h-screen bg-[#f6f5f3] text-[#1c1917] font-sans">
      <div className="max-w-[1280px] mx-auto bg-[#fafaf9] sm:border-x border-stone-200/90 shadow-xs relative">
        {/* Mobile Navigation Drawer Overlay */}
        {mobileNavOpen && (
          <div className="lg:hidden fixed inset-0 z-50 bg-stone-900/40 backdrop-blur-xs flex">
            <div className="w-5/6 max-w-sm bg-white h-full overflow-y-auto p-6 space-y-6 shadow-xl border-r border-stone-200">
              <div className="flex items-center justify-between border-b border-stone-200 pb-3">
                <span className="font-mono text-xs uppercase tracking-wider text-stone-500 font-bold">
                  {isJourney ? 'SIH FIELD NOTEBOOK' : 'TECHNICAL DOCUMENTATION'}
                </span>
                <button
                  onClick={() => setMobileNavOpen(false)}
                  className="btn-extend-tactile py-1 px-2 text-[10px]"
                >
                  ✕
                </button>
              </div>

              <nav className="space-y-6">
                {navGroups.map((group) => (
                  <div key={group.name} className="space-y-2">
                    <h3 className="font-mono text-[11px] font-semibold text-stone-700 uppercase tracking-wider">
                      {group.name}
                    </h3>
                    <ul className="space-y-1">
                      {group.items.map((item) => {
                        const isActive = article.slug === item.slug;
                        return (
                          <li key={item.slug}>
                            <button
                              onClick={() => {
                                onNavigate(item.slug);
                                setMobileNavOpen(false);
                              }}
                              className={`w-full text-left px-2.5 py-1.5 rounded-[2px] text-xs transition-colors flex items-center justify-between ${
                                isActive
                                  ? 'bg-stone-900 text-white font-semibold'
                                  : 'text-stone-600 hover:text-stone-950 hover:bg-stone-100'
                              }`}
                            >
                              <span className="truncate">{item.title}</span>
                              {item.badge && (
                                <span className="font-mono text-[9px] uppercase px-1 py-0.2 bg-stone-100 border border-stone-300 rounded text-stone-600 ml-1">
                                  {item.badge}
                                </span>
                              )}
                            </button>
                          </li>
                        );
                      })}
                    </ul>
                  </div>
                ))}
              </nav>
            </div>
            <div className="flex-1" onClick={() => setMobileNavOpen(false)} />
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 py-8 px-4 sm:px-6 lg:px-8">
          {/* LEFT SIDEBAR NAVIGATION (Desktop) */}
          <aside className="hidden lg:block lg:col-span-3 border-r border-stone-200 pr-6 space-y-8 sticky top-20 self-start max-h-[calc(100vh-6rem)] overflow-y-auto">
            <div className="space-y-1">
              <span className="font-mono text-[10px] uppercase tracking-widest text-stone-400 font-bold block">
                {isJourney ? 'SIH FIELD NOTEBOOK' : 'TECHNICAL DOCUMENTATION'}
              </span>
              <h2 className="font-bold text-sm text-stone-900">
                {isJourney ? 'Chronicle & Defense' : 'System Reference'}
              </h2>
            </div>

            <nav className="space-y-6">
              {navGroups.map((group) => (
                <div key={group.name} className="space-y-2">
                  <h3 className="font-mono text-[11px] font-semibold text-stone-700 uppercase tracking-wider">
                    {group.name}
                  </h3>
                  <ul className="space-y-1">
                    {group.items.map((item) => {
                      const isActive = article.slug === item.slug;
                      return (
                        <li key={item.slug}>
                          <button
                            onClick={() => onNavigate(item.slug)}
                            className={`w-full text-left px-2.5 py-1.5 rounded-[2px] text-xs transition-colors flex items-center justify-between ${
                              isActive
                                ? 'bg-stone-200 text-stone-950 font-semibold'
                                : 'text-stone-600 hover:text-stone-950 hover:bg-stone-100'
                            }`}
                          >
                            <span className="truncate">{item.title}</span>
                            {item.badge && (
                              <span className="font-mono text-[9px] uppercase px-1 py-0.2 bg-stone-100 border border-stone-300 rounded text-stone-600 ml-1">
                                {item.badge}
                              </span>
                            )}
                          </button>
                        </li>
                      );
                    })}
                  </ul>
                </div>
              ))}
            </nav>
          </aside>

          {/* MAIN ARTICLE AREA */}
          <main className="lg:col-span-9 xl:col-span-6 min-w-0 max-w-full overflow-x-clip py-2">
            {/* Mobile Nav Trigger Bar */}
            <div className="lg:hidden flex items-center justify-between p-2.5 mb-6 bg-white border border-stone-200 rounded-[2px] font-mono text-xs">
              <span className="text-stone-600 font-semibold uppercase text-[11px] truncate mr-2">
                {isJourney ? 'SIH Field Notebook' : 'Technical Reference'}
              </span>
              <button
                onClick={() => setMobileNavOpen(true)}
                className="btn-extend-tactile py-1 px-2.5 text-[10px] shrink-0"
              >
                Articles ☰
              </button>
            </div>

            {/* Breadcrumb Trail */}
            <div className="flex items-center gap-1.5 text-xs text-stone-500 font-mono mb-6">
              <button onClick={() => onNavigate('home')} className="hover:text-stone-900">Home</button>
              <ChevronRight size={12} className="text-stone-400" />
              <button
                onClick={() => onNavigate(isJourney ? 'journey' : 'technical/01-introducing-ps26054')}
                className="hover:text-stone-900"
              >
                {isJourney ? 'Our SIH Journey' : 'Technical Docs'}
              </button>
              <ChevronRight size={12} className="text-stone-400" />
              <span className="text-stone-800 font-medium truncate max-w-[200px]">{article.title}</span>
            </div>

            {/* Article Editorial Header */}
            <header className="space-y-4 pb-8 border-b border-stone-200">
              <div className="flex items-center gap-2">
                <span className="font-mono text-[10px] uppercase tracking-widest bg-stone-100 border border-stone-300 text-stone-700 px-2 py-0.5 rounded-[2px] font-semibold">
                  {article.category}
                </span>
                {article.group && article.group !== article.category && (
                  <>
                    <span className="text-stone-300">|</span>
                    <span className="font-mono text-[10px] text-stone-500 uppercase">
                      {article.group}
                    </span>
                  </>
                )}
              </div>

              <h1 className="text-3xl sm:text-4xl font-bold tracking-tight text-stone-950 leading-tight">
                {article.title}
              </h1>

              {/* Short Abstract Block with Interactive Link Routing */}
              {article.abstract && (
                <div className="p-4 rounded-[2px] border-l-2 border-stone-800 bg-stone-100/80 text-stone-800 text-sm leading-relaxed italic">
                  <ReactMarkdown
                    components={{
                      p: ({ children }: any) => <p className="m-0 italic">{children}</p>,
                      a: ({ href, children }: any) => {
                        const resolved = href ? resolveTargetSlug(href) : null;
                        return (
                          <a
                            href={href && href.startsWith('#') ? href : `#/${resolved || href}`}
                            onClick={(e) => handleLinkClick(e, href)}
                            className="text-stone-900 underline decoration-stone-400 hover:decoration-stone-900 font-semibold hover:bg-stone-200/60 px-0.5 rounded transition-colors inline cursor-pointer not-italic"
                          >
                            {children}
                          </a>
                        );
                      }
                    }}
                  >
                    {article.abstract}
                  </ReactMarkdown>
                </div>
              )}

              {/* Technical Metadata Row (Extend Style) */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-2 border-t border-stone-100 font-mono text-[11px]">
                <div className="p-2.5 border border-stone-200 rounded-[2px] bg-stone-50">
                  <span className="block text-[9px] uppercase tracking-wider text-stone-500 font-semibold">Status</span>
                  <span className="font-bold text-stone-900">VERIFIED CODE</span>
                </div>
                <div className="p-2.5 border border-stone-200 rounded-[2px] bg-stone-50">
                  <span className="block text-[9px] uppercase tracking-wider text-stone-500 font-semibold">Architecture</span>
                  <span className="font-bold text-stone-900 truncate block">{article.osacbmLayer}</span>
                </div>
                <div className="p-2.5 border border-stone-200 rounded-[2px] bg-stone-50">
                  <span className="block text-[9px] uppercase tracking-wider text-stone-500 font-semibold">Engine Scope</span>
                  <span className="font-bold text-stone-900 truncate block">{article.engineScope || 'Rotax 912 iS'}</span>
                </div>
                <div className="p-2.5 border border-stone-200 rounded-[2px] bg-stone-50">
                  <span className="block text-[9px] uppercase tracking-wider text-stone-500 font-semibold">Read Time</span>
                  <span className="font-bold text-stone-900">{article.readTime}</span>
                </div>
              </div>
            </header>

            {/* Rendered Prose Content */}
            <article className="prose-technical py-8">
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                  // Custom heading IDs for on-page table of contents
                  h2: ({ children }) => {
                    const text = React.Children.toArray(children).join('');
                    const id = text.toLowerCase().replace(/[^\w\s-]/g, '').replace(/\s+/g, '-');
                    return <h2 id={id}>{children}</h2>;
                  },
                  h3: ({ children }) => {
                    const text = React.Children.toArray(children).join('');
                    const id = text.toLowerCase().replace(/[^\w\s-]/g, '').replace(/\s+/g, '-');
                    return <h3 id={id}>{children}</h3>;
                  },
                  // Code block with Mermaid detection
                  code: ({ node, inline, className, children, ...props }: any) => {
                    const match = /language-(\w+)/.exec(className || '');
                    const codeText = String(children).replace(/\n$/, '');
                    const isMermaid = (!inline && match && match[1] === 'mermaid') ||
                      (!inline && /^\s*(flowchart|graph|sequenceDiagram|classDiagram|stateDiagram|erDiagram|gantt)\b/m.test(codeText));

                    if (isMermaid) {
                      return <MermaidDiagram chart={codeText} />;
                    }

                    if (!inline && match) {
                      const codeId = `code-${Math.random().toString(36).substring(2, 7)}`;
                      return (
                        <div className="relative group/code my-4">
                          <div className="flex items-center justify-between px-3 py-1.5 bg-stone-900 text-stone-400 font-mono text-[10px] uppercase border-b border-stone-800 rounded-t-sm">
                            <span>{match[1]}</span>
                            <button
                              onClick={() => handleCopyCode(codeText, codeId)}
                              className="hover:text-white transition-colors flex items-center gap-1"
                              title="Copy code"
                            >
                              {copiedCodeId === codeId ? (
                                <>
                                  <Check size={12} className="text-emerald-400" />
                                  <span>COPIED</span>
                                </>
                              ) : (
                                <>
                                  <Copy size={12} />
                                  <span>COPY</span>
                                </>
                              )}
                            </button>
                          </div>
                          <pre className="!mt-0 !rounded-t-none">
                            <code className={className} {...props}>
                              {children}
                            </code>
                          </pre>
                        </div>
                      );
                    }

                    return (
                      <code className={className} {...props}>
                        {children}
                      </code>
                    );
                  },
                  // Intercept markdown links and route within the app
                  a: ({ href, children, ...props }: any) => {
                    const resolved = href ? resolveTargetSlug(href) : null;
                    if (resolved || (href && href.startsWith('#'))) {
                      return (
                        <a
                          href={href && href.startsWith('#') ? href : `#/${resolved}`}
                          onClick={(e) => handleLinkClick(e, href)}
                          className="text-stone-900 underline decoration-stone-400 hover:decoration-stone-950 font-medium hover:bg-stone-200/70 px-0.5 rounded transition-colors inline cursor-pointer"
                        >
                          {children}
                        </a>
                      );
                    }
                    return (
                      <a href={href} {...props} target="_blank" rel="noopener noreferrer" className="text-stone-700 underline hover:text-stone-950 transition-colors">
                        {children}
                      </a>
                    );
                  },
                  // Custom Table Component
                  table: ({ children }: any) => (
                    <div className="my-6 w-full max-w-full overflow-x-auto border border-stone-300 rounded-[2px] shadow-xs bg-white">
                      <table className="w-full text-left border-collapse text-xs whitespace-normal table-auto min-w-[620px]">
                        {children}
                      </table>
                    </div>
                  ),
                  // Custom Table Header
                  th: ({ children }: any) => (
                    <th className="p-3 bg-stone-100 font-mono text-[10px] text-stone-800 uppercase tracking-wider font-semibold border-b border-stone-200">
                      {children}
                    </th>
                  ),
                  // Custom Table Cell
                  td: ({ children }: any) => (
                    <td className="p-3 border-b border-stone-100 text-stone-700 font-sans">
                      {children}
                    </td>
                  ),
                  // Images
                  img: ({ src, alt }: any) => (
                    <figure className="my-6 border border-stone-200 bg-white rounded-[2px] overflow-hidden">
                      <img src={src} alt={alt} className="w-full h-auto object-cover max-h-[460px]" />
                      {alt && (
                        <figcaption className="p-2.5 bg-stone-50 border-t border-stone-200 text-xs text-stone-600 font-mono text-center">
                          {alt}
                        </figcaption>
                      )}
                    </figure>
                  ),
                }}
              >
                {markdownBody}
              </ReactMarkdown>
            </article>

            {/* Bottom Next / Previous Article Navigation */}
            <nav className="mt-12 pt-8 border-t border-stone-200 grid grid-cols-1 sm:grid-cols-2 gap-4">
              {prevArticle ? (
                <button
                  onClick={() => onNavigate(prevArticle.slug)}
                  className="p-4 border border-stone-200 rounded-[2px] bg-white hover:border-stone-400 text-left transition-colors group flex flex-col justify-between shadow-xs"
                >
                  <span className="font-mono text-[10px] text-stone-400 uppercase tracking-wider flex items-center gap-1 font-semibold">
                    <ArrowLeft size={12} /> Previous Article
                  </span>
                  <span className="font-semibold text-sm text-stone-900 group-hover:underline mt-1 truncate">
                    {prevArticle.title}
                  </span>
                </button>
              ) : <div />}

              {nextArticle ? (
                <button
                  onClick={() => onNavigate(nextArticle.slug)}
                  className="p-4 border border-stone-200 rounded-[2px] bg-white hover:border-stone-400 text-right transition-colors group flex flex-col justify-between shadow-xs"
                >
                  <span className="font-mono text-[10px] text-stone-400 uppercase tracking-wider flex items-center justify-end gap-1 font-semibold">
                    Next Article <ArrowRight size={12} />
                  </span>
                  <span className="font-semibold text-sm text-stone-900 group-hover:underline mt-1 truncate">
                    {nextArticle.title}
                  </span>
                </button>
              ) : <div />}
            </nav>
          </main>

          {/* RIGHT SIDEBAR "ON THIS PAGE" TABLE OF CONTENTS */}
          <aside className="hidden xl:block xl:col-span-3 pl-4 sticky top-20 self-start max-h-[calc(100vh-6rem)] overflow-y-auto space-y-6 bg-[#fafaf9] z-10">
            <div className="space-y-1">
              <span className="font-mono text-[10px] uppercase tracking-widest text-stone-400 font-bold block">
                TABLE OF CONTENTS
              </span>
              <h3 className="font-bold text-xs text-stone-900 uppercase tracking-wider">
                On this page
              </h3>
            </div>

            <ul className="space-y-1 text-xs border-l border-stone-200 pl-3">
              {article.headings.length === 0 ? (
                <li className="text-stone-400 font-mono text-[11px]">Overview section</li>
              ) : (
                article.headings.map((heading) => {
                  const isActive = activeHeadingId === heading.id;
                  return (
                    <li key={heading.id} className={heading.level === 3 ? 'pl-2.5' : ''}>
                      <a
                        href={`#${heading.id}`}
                        onClick={(e) => {
                          e.preventDefault();
                          const el = document.getElementById(heading.id);
                          if (el) {
                            el.scrollIntoView({ behavior: 'smooth', block: 'start' });
                            setActiveHeadingId(heading.id);
                          }
                        }}
                        className={`block py-1 transition-colors truncate ${
                          isActive
                            ? 'text-stone-950 font-semibold border-l-2 border-stone-950 -ml-[13px] pl-[11px]'
                            : 'text-stone-500 hover:text-stone-900'
                        }`}
                      >
                        {heading.text}
                      </a>
                    </li>
                  );
                })
              )}
            </ul>

            {/* Quick Actions Card */}
            <div className="p-4 border border-stone-200 bg-stone-50 rounded-xs space-y-2">
              <span className="font-mono text-[10px] text-stone-600 uppercase font-semibold block">
                Evidence Discipline
              </span>
              <p className="text-[11px] text-stone-600 leading-normal">
                This article cites only verified repository source files, characterization tests, and manufacturer engine data.
              </p>
              <div className="pt-1">
                <span className="font-mono text-[9px] text-stone-400 uppercase">
                  DRDO PS-26054 · TEAM MIDNIGHT CIPHERS
                </span>
              </div>
            </div>
          </aside>
        </div>
      </div>
    </div>
  );
};
