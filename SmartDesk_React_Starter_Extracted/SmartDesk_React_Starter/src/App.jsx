import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { DashboardPage } from './pages/dashboard/DashboardPage';
import { TicketsPage } from './pages/tickets/TicketsPage';
import { AIAnalysisPage } from './pages/ai-analysis/AIAnalysisPage';
import { WorkforcePage } from './pages/workforce/WorkforcePage';
import { AnalyticsPage } from './pages/analytics/AnalyticsPage';
import { SettingsPage } from './pages/settings/SettingsPage';
import { LoginPage } from './pages/auth/LoginPage';
import { AuthProvider } from './context/AuthContext';
import { useAuth } from './context/AuthContext';

function RequireSession({ children }) {
  const { user, loading, authError, refresh } = useAuth();
  if (loading) return <div className="grid min-h-screen place-items-center bg-[#0a0e16] text-sm text-slate-300">Checking your SmartDesk session…</div>;
  if (authError) return <div className="grid min-h-screen place-items-center bg-[#0a0e16] p-6 text-center text-sm text-rose-200"><div><p role="alert">{authError}</p><button className="mt-4 rounded bg-blue-600 px-4 py-2 text-white" onClick={() => refresh().catch(() => {})}>Retry</button></div></div>;
  if (!user) return <Navigate to="/login" replace />;
  return children;
}

function Protected({ children }) {
  return <RequireSession>{children}</RequireSession>;
}

export default function App() {
  return (
    <AuthProvider><BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <Routes>
        <Route path="/" element={<Protected><DashboardPage /></Protected>} />
        <Route path="/tickets" element={<Protected><TicketsPage /></Protected>} />
        <Route path="/ai-analysis" element={<Protected><AIAnalysisPage /></Protected>} />
        <Route path="/workforce" element={<Protected><WorkforcePage /></Protected>} />
        <Route path="/analytics" element={<Protected><AnalyticsPage /></Protected>} />
        <Route path="/settings" element={<Protected><SettingsPage /></Protected>} />
        <Route path="/login" element={<LoginPage />} />
      </Routes>
    </BrowserRouter></AuthProvider>
  );
}
