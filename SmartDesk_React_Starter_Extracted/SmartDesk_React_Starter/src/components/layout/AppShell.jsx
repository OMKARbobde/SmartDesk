import { useEffect, useState } from 'react';
import { Sidebar } from './Sidebar';
import { Header } from './Header';
import { CommandPalette } from './CommandPalette';

export function AppShell({ children, title, breadcrumb }) {
  const [cmdOpen, setCmdOpen] = useState(false);
  useEffect(() => {
    const onShortcut = (event) => { if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') { event.preventDefault(); setCmdOpen(true); } };
    window.addEventListener('keydown', onShortcut);
    return () => window.removeEventListener('keydown', onShortcut);
  }, []);

  return (
    <div className="min-h-screen bg-[#0a0e16] text-slate-200">
      <a href="#main-content" className="sr-only z-[100] rounded bg-blue-600 px-4 py-2 text-white focus:not-sr-only focus:fixed focus:left-3 focus:top-3">Skip to main content</a>
      <Sidebar />
      <div className="md:pl-64 flex flex-col min-h-screen min-w-0">
        <Header
          title={title}
          breadcrumb={breadcrumb}
          onOpenCommandPalette={() => setCmdOpen(true)}
        />
        <main id="main-content" tabIndex={-1} className="flex-1 p-4 pb-20 md:p-6 overflow-y-auto min-w-0 focus:outline-none">
          {children}
        </main>
      </div>
      <CommandPalette isOpen={cmdOpen} onClose={() => setCmdOpen(false)} />
    </div>
  );
}
