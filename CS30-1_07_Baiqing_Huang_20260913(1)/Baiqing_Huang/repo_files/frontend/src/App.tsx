import { useCallback, useEffect, useRef, useState, type FormEvent } from 'react';
import { Archive, BookOpen, ChevronDown, FlaskConical, LogOut, MessageSquare, PanelLeftClose, PanelLeftOpen, Plus, Settings, Shield, UserRound } from 'lucide-react';
import { api, clearAccount, getToken, post, saveToken } from './api';
import { Button, ErrorNotice, IconButton, Loading, Modal } from './components';
import { Chat } from './Chat';
import { ProfilePage, AccountPage } from './Settings';
import { CorpusPage, ExperimentsPage, FeedbackReviewPage } from './admin';
import { ModelsPage } from './Models';
import { AccountsPage } from './Accounts';
import { FailuresPage } from './Failures';
import type { Capabilities, Profile, Session, User } from './types';

export function navigate(path: string, replace = false) { if (location.pathname !== path) { history[replace ? 'replaceState' : 'pushState']({}, '', path); window.dispatchEvent(new PopStateEvent('popstate')); } }
function usePath() { const [path, setPath] = useState(location.pathname); useEffect(() => { const changed = () => setPath(location.pathname); window.addEventListener('popstate', changed); return () => window.removeEventListener('popstate', changed); }, []); return path; }

export function App() {
  const path = usePath();
  const [user, setUser] = useState<User | null>(null);
  const [booting, setBooting] = useState(!!getToken());
  const [authError, setAuthError] = useState<unknown>(null);
  useEffect(() => {
    if (getToken()) api.me().then(setUser).catch(error => { setAuthError(error); clearAccount(); }).finally(() => setBooting(false));
    const expired = () => { setUser(null); setAuthError(new Error('Your session has expired. Sign in to continue your conversation.')); sessionStorage.removeItem('cs30.access-token'); };
    window.addEventListener('cs30:session-expired', expired); return () => window.removeEventListener('cs30:session-expired', expired);
  }, []);
  const logout = useCallback(() => { clearAccount(); setUser(null); setAuthError(null); navigate('/login'); }, []);
  if (booting) return <div className="boot"><Loading>Opening your learning space…</Loading></div>;
  if (!user) return <Login initialError={authError} onLogin={value => { setUser(value); setAuthError(null); if (path === '/login' || path === '/') navigate('/chat', true); }} />;
  return <Workspace key={user.id} user={user} setUser={setUser} logout={logout} path={path} />;
}

function Login({ initialError, onLogin }: { initialError: unknown; onLogin: (user: User) => void }) {
  const [email, setEmail] = useState(''); const [password, setPassword] = useState(''); const [busy, setBusy] = useState(false); const [error, setError] = useState<unknown>(initialError);
  useEffect(() => setError(initialError), [initialError]);
  const submit = async (event: FormEvent) => { event.preventDefault(); if (busy) return; setBusy(true); setError(null); try { const data = await post<{ access_token: string }>('/auth/login', { email: email.trim(), password }); saveToken(data.access_token); onLogin(await api.me()); } catch (caught) { setError(caught); } finally { setBusy(false); } };
  return <main className="login-page"><a className="brand login-brand" href="/chat"><BookOpen size={23} /><span>Learning Assistant</span></a><section className="login-content"><span className="eyebrow">A little curiosity goes a long way</span><h1>Welcome to your<br />learning space.</h1><p className="secondary">Ask freely. Explore ideas. See the sources.</p><form onSubmit={submit} className="stack"><label>Email<input type="email" autoComplete="username" required value={email} onChange={e => setEmail(e.target.value)} placeholder="you@example.com" /></label><label>Password<input type="password" autoComplete="current-password" required value={password} onChange={e => setPassword(e.target.value)} /></label><ErrorNotice error={error} /><Button type="submit" className="primary" disabled={busy}>{busy ? 'Signing in…' : 'Sign in'}</Button></form><p className="login-note">Use the account provided by your administrator.</p></section><footer className="login-footer">CS-30-1 · A source-grounded learning assistant</footer></main>;
}

function Workspace({ user, setUser, logout, path }: { user: User; setUser: (user: User) => void; logout: () => void; path: string }) {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [archived, setArchived] = useState(false);
  const [sessionsError, setSessionsError] = useState<unknown>(null);
  const [profile, setProfile] = useState<Profile | null>(null);
  const [capabilities, setCapabilities] = useState<Capabilities | null>(null);
  const [configError, setConfigError] = useState<unknown>(null);
  const [capabilitiesError, setCapabilitiesError] = useState<unknown>(null);
  const capabilitiesRequest = useRef(0);
  const refreshCapabilities = useCallback(() => {
    const requestId = ++capabilitiesRequest.current;
    return api.capabilities().then(value => { if (requestId === capabilitiesRequest.current) { setCapabilities(value); setCapabilitiesError(null); } }).catch(error => { if (requestId === capabilitiesRequest.current) { setCapabilities(null); setCapabilitiesError(error); } });
  }, []);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [desktopCollapsed, setDesktopCollapsed] = useState(false);
  const [newBusy, setNewBusy] = useState(false);
  const [overlayOpen, setOverlayOpen] = useState(false);
  const sessionId = path.startsWith('/chat/') ? path.split('/')[2] : undefined;
  const chatRoute = path === '/chat' || path.startsWith('/chat/') || path === '/' || path === '/login';
  const activeSession = sessions.find(item => item.id === sessionId);
  const refreshSessions = useCallback(async () => { try { setSessions(await api.sessions(archived ? 'archived' : 'active')); setSessionsError(null); } catch (error) { setSessionsError(error); } }, [archived]);
  useEffect(() => { void refreshSessions(); }, [refreshSessions]);
  useEffect(() => { api.profile().then(setProfile).catch(setConfigError); }, []);
  useEffect(() => { void refreshCapabilities(); }, [path, refreshCapabilities]);
  useEffect(() => { const refresh = () => { if (document.visibilityState === 'visible') void refreshCapabilities(); }; window.addEventListener('focus', refresh); document.addEventListener('visibilitychange', refresh); return () => { window.removeEventListener('focus', refresh); document.removeEventListener('visibilitychange', refresh); }; }, [refreshCapabilities]);
  useEffect(() => { if (path === '/' || path === '/login' || path.startsWith('/sessions')) navigate('/chat', true); }, [path]);
  useEffect(() => { const wide = window.matchMedia('(min-width: 1024px)'); const change = () => { if (wide.matches) setSidebarOpen(false); }; wide.addEventListener('change', change); return () => wide.removeEventListener('change', change); }, []);
  const go = (next: string) => { navigate(next); setSidebarOpen(false); };
  const create = async () => { if (newBusy) return; setNewBusy(true); try { const item = await post<Session>('/sessions', { title: 'New chat' }); setArchived(false); await refreshSessions(); go(`/chat/${item.id}`); } catch (error) { setSessionsError(error); } finally { setNewBusy(false); } };
  const openSidebar = () => { if (window.matchMedia('(min-width: 1024px)').matches) setDesktopCollapsed(!desktopCollapsed); else if (!overlayOpen) setSidebarOpen(true); };
  const sidebar = <><div className="sidebar-top"><a className="brand" href="/chat" onClick={e => { e.preventDefault(); go('/chat'); }}><BookOpen size={22} /><span>Learning Assistant</span></a><IconButton label="Close sidebar" onClick={() => { setSidebarOpen(false); setDesktopCollapsed(true); }}><PanelLeftClose size={19} /></IconButton></div><Button className="new-chat" onClick={create} disabled={newBusy}><Plus size={19} />{newBusy ? 'Creating chat…' : 'New chat'}</Button><div className="history-heading"><span>{archived ? 'Archived conversations' : 'Your conversations'}</span><IconButton label={archived ? 'Show active conversations' : 'Show archived conversations'} onClick={() => setArchived(!archived)}><Archive size={16} /></IconButton></div><nav className="session-list" aria-label="Conversations">{sessions.map(item => <button key={item.id} className={`session-link ${sessionId === item.id ? 'selected' : ''}`} title={item.title} aria-current={sessionId === item.id ? 'page' : undefined} onClick={() => go(`/chat/${item.id}`)}><MessageSquare size={16} /><span>{item.title}</span></button>)}{sessions.length === 0 && !sessionsError && <p className="sidebar-empty">{archived ? 'No archived conversations.' : 'Your conversations will appear here.'}</p>}<ErrorNotice error={sessionsError} action={<Button onClick={refreshSessions}>Try again</Button>} /></nav><nav className="account-nav" aria-label="Account and settings"><Button onClick={() => go('/profile')}><Settings size={18} />Learning preferences</Button>{user.role === 'admin' && <Button onClick={() => go('/admin/models')}><Shield size={18} />Administration</Button>}<div className="account-row"><Button onClick={() => go('/account')} className="account-button"><span className="avatar">{(user.full_name || user.email).slice(0, 1).toUpperCase()}</span><span>{user.full_name || user.email}<small>{user.role === 'admin' ? 'Administrator' : 'Learner'}</small></span><ChevronDown size={14} /></Button><IconButton label="Sign out" onClick={logout}><LogOut size={17} /></IconButton></div></nav></>;
  return <div className={`app-shell ${desktopCollapsed ? 'sidebar-collapsed' : ''}`}><a href="#main-content" className="skip-link">Skip to content</a><aside className="desktop-sidebar">{sidebar}</aside>{sidebarOpen && <Modal title="Navigation" kind="sidebar-modal" onClose={() => setSidebarOpen(false)}>{sidebar}</Modal>}<div className="main-shell"><header className="topbar"><div className="topbar-title"><IconButton label={desktopCollapsed ? 'Open sidebar' : 'Toggle sidebar'} onClick={openSidebar} disabled={overlayOpen}><PanelLeftOpen size={21} /></IconButton><div><span className="product-title">Learning Assistant</span><span className="topbar-subtitle">{chatRoute ? activeSession?.title || 'A space to understand' : path === '/profile' ? 'Learning preferences' : path.startsWith('/admin') ? 'Administration' : 'Your account'}</span></div></div><span className={`mode-badge ${capabilities?.model_mode === 'mock' ? 'mock' : ''}`} title={capabilities?.model_mode === 'mock' ? 'Responses use a deterministic mock model. They demonstrate application behavior, not live model quality.' : undefined}><span className="mode-dot" />{capabilities ? capabilities.model_mode === 'mock' ? 'Demo (mock model)' : 'Live model' : capabilitiesError ? 'Model status unavailable' : 'Checking model…'}</span></header><main id="main-content" className={chatRoute ? 'chat-main' : 'page-scroll'}><ErrorNotice error={configError} /><ErrorNotice error={capabilitiesError} />{path.startsWith('/admin') && user.role === 'admin' && <nav className="admin-navigation" aria-label="Administration">{[['/admin/models', 'Models'], ['/admin/accounts', 'Accounts'], ['/admin/failures', 'Diagnostics'], ['/admin/corpus', 'Corpus'], ['/admin/experiments', 'Experiments'], ['/admin/feedback', 'Feedback']].map(([route, label]) => <a key={route} className="button" href={route} aria-current={path === route ? 'page' : undefined} onClick={event => { event.preventDefault(); go(route); }}>{label}</a>)}</nav>}{chatRoute ? <Chat key={sessionId || 'empty'} sessionId={sessionId} navigating={newBusy} userId={user.id} profile={profile} capabilities={capabilities} onCreated={id => { void refreshSessions(); go(`/chat/${id}`); }} refreshSessions={refreshSessions} onOverlay={setOverlayOpen} /> : path === '/profile' ? <ProfilePage profile={profile} onSaved={setProfile} /> : path === '/account' ? <AccountPage user={user} onSaved={setUser} onPasswordChanged={logout} /> : path.startsWith('/admin') && user.role !== 'admin' ? <div className="content-page"><h1>Administrator access required</h1><p>This page is available to administrators.</p><Button onClick={() => go('/chat')}>Back to chat</Button></div> : path === '/admin/models' || path === '/admin' ? <ModelsPage onActivated={() => { setCapabilities(null); void refreshCapabilities(); }} /> : path === '/admin/accounts' ? <AccountsPage currentUserId={user.id} /> : path === '/admin/failures' ? <FailuresPage /> : path === '/admin/corpus' ? <CorpusPage /> : path === '/admin/experiments' ? <ExperimentsPage /> : path === '/admin/feedback' ? <FeedbackReviewPage /> : <div className="content-page"><h1>Page not found</h1><Button onClick={() => go('/chat')}>Back to chat</Button></div>}</main></div></div>;
}
