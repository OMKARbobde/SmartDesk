import { useEffect, useState } from 'react';
import { Layers, ShieldCheck, ArrowRight, Eye, EyeOff } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';

export function LoginPage() {
  const navigate = useNavigate();
  const { login, isAuthenticated } = useAuth();
  const [showPassword, setShowPassword] = useState(false);
  const [notice, setNotice] = useState('');
  const [identifier, setIdentifier] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  useEffect(() => { if (isAuthenticated) navigate('/', { replace: true }); }, [isAuthenticated, navigate]);

  const submit = async (event) => {
    event.preventDefault();
    setError(''); setNotice(''); setSubmitting(true);
    try { await login(identifier.trim(), password); navigate('/', { replace: true }); }
    catch (loginError) { setError(loginError.message || 'Sign-in failed.'); }
    finally { setSubmitting(false); }
  };

  return (
    <div className="min-h-screen bg-[#0a0e16] flex flex-col items-center justify-center p-4">
      <div className="w-full max-w-md bg-[#0f131c] border border-[#1e2638] rounded-xl p-8 shadow-2xl">
        <div className="flex items-center justify-center gap-2.5 mb-6">
          <div className="w-9 h-9 rounded-lg bg-blue-600 flex items-center justify-center text-white font-bold"><Layers className="w-5 h-5" /></div>
          <span className="font-bold text-xl text-white">SmartDesk</span>
        </div>
        <h2 className="text-center text-base font-semibold text-white mb-1">Enterprise Authentication</h2>
        <p className="text-center text-xs text-slate-400 mb-2">Sign in to your organization's service workspace</p>
        <p className="text-center text-[11px] text-emerald-300 mb-6">Django session sign-in • Username or unique email</p>
        <div className="space-y-3 mb-6">
          <button type="button" onClick={() => setNotice('SSO is unavailable because no identity provider is configured.')} className="w-full py-2.5 px-4 rounded-lg bg-[#181c24] border border-[#1e2638] text-xs font-semibold text-slate-200 hover:bg-[#202634] flex items-center justify-center gap-2 transition-colors">
            <ShieldCheck className="w-4 h-4 text-blue-400" /> Continue with SSO (unavailable)
          </button>
        </div>
        <div className="relative flex py-2 items-center mb-6"><div className="flex-grow border-t border-[#1e2638]" /><span className="flex-shrink mx-4 text-[10px] text-slate-500 uppercase">Or credentials</span><div className="flex-grow border-t border-[#1e2638]" /></div>
        {notice && <p role="status" className="mb-4 rounded border border-amber-700/50 bg-amber-950/30 p-3 text-xs text-amber-300">{notice}</p>}
        {error && <p role="alert" className="mb-4 rounded border border-rose-800/60 bg-rose-950/30 p-3 text-xs text-rose-200">{error}</p>}
        <form onSubmit={submit} className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1" htmlFor="login-identifier">Username or email</label>
            <input id="login-identifier" type="text" required value={identifier} onChange={(event) => setIdentifier(event.target.value)} autoComplete="username" placeholder="Username or you@company.com" aria-label="Username or email" className="w-full px-3 py-2 rounded-lg bg-[#181c24] border border-[#1e2638] text-xs text-white focus:outline-none focus:border-blue-500" />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1" htmlFor="login-password">Password</label>
            <div className="relative"><input id="login-password" type={showPassword ? 'text' : 'password'} required value={password} onChange={(event) => setPassword(event.target.value)} autoComplete="current-password" placeholder="Enter your password" aria-label="Password" className="w-full px-3 py-2 rounded-lg bg-[#181c24] border border-[#1e2638] text-xs text-white focus:outline-none focus:border-blue-500" /><button type="button" aria-label={showPassword ? 'Hide password' : 'Show password'} onClick={() => setShowPassword(!showPassword)} className="absolute right-3 top-2 text-slate-400">{showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}</button></div>
          </div>
          <button type="submit" disabled={submitting} className="w-full py-2.5 px-4 rounded-lg bg-blue-600 hover:bg-blue-500 disabled:opacity-60 text-white text-xs font-semibold flex items-center justify-center gap-2 transition-colors">
            {submitting ? 'Signing in…' : 'Sign in'} <ArrowRight className="w-3.5 h-3.5 ml-1" />
          </button>
        </form>
      </div>
      <p className="text-[11px] text-slate-600 mt-6">© 2025 SmartDesk Inc. SOC 2 Type II • TLS 1.3 • ISO 27001</p>
    </div>
  );
}
