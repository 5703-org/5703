import { useCallback, useEffect, useRef, useState, type FormEvent } from 'react';
import { Plus, RefreshCw } from 'lucide-react';
import { patch, post, request } from './api';
import { Button, Empty, ErrorNotice, Loading, Modal, titleCase } from './components';
import type { User } from './types';

export function AccountsPage({ currentUserId }: { currentUserId: string }) {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<unknown>(null);
  const [search, setSearch] = useState('');
  const [create, setCreate] = useState(false);
  const [edit, setEdit] = useState<{ user: User; action: 'password' | 'status' } | null>(null);
  const [notice, setNotice] = useState('');
  const refresh = useCallback(async () => {
    setLoading(true); setError(null);
    try { setUsers(await request<User[]>('/admin/users')); }
    catch (caught) { setError(caught); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { void refresh(); }, [refresh]);
  const saved = (value: User, message: string) => {
    setUsers(previous => previous.some(user => user.id === value.id) ? previous.map(user => user.id === value.id ? value : user) : [...previous, value]);
    setCreate(false); setEdit(null); setNotice(message);
  };
  const shown = users.filter(user => `${user.full_name} ${user.email}`.toLowerCase().includes(search.toLowerCase()));
  return <div className="content-page settings-page">
    <span className="eyebrow">Administration</span><h1>Accounts</h1>
    <p className="page-intro">Create accounts and manage access. Password and access changes end that account’s existing sessions.</p>
    <div className="admin-toolbar"><Button className="primary" onClick={() => { setNotice(''); setCreate(true); }}><Plus size={17} />Create account</Button><Button disabled={loading} onClick={refresh}><RefreshCw size={17} />Refresh</Button></div>
    <label className="admin-search">Find an account<input type="search" value={search} onChange={event => setSearch(event.target.value)} placeholder="Name or email" /></label>
    <ErrorNotice error={error} />{notice && <p role="status" className="saved">{notice}</p>}
    {loading ? <Loading>Loading accounts…</Loading> : <div className="record-list">{shown.map(user => <article className="record" key={user.id}>
      <div className="record-header"><div><h2 className="record-title">{user.full_name || user.email}</h2><p className="secondary">{user.email} · {user.role === 'admin' ? 'Administrator' : 'Learner'} · Version {user.version}</p></div><span className="record-status">{titleCase(user.status)}</span></div>
      {user.id === currentUserId ? <p className="secondary">Your account. Use Your account to change your password.</p> : <div className="record-actions"><Button onClick={() => { setNotice(''); setEdit({ user, action: 'password' }); }}>Reset password</Button><Button onClick={() => { setNotice(''); setEdit({ user, action: 'status' }); }}>{user.status === 'active' ? 'Deactivate' : 'Restore access'}</Button></div>}
    </article>)}</div>}
    {!loading && !error && shown.length === 0 && <Empty title="No matching accounts">Try another name or email.</Empty>}
    {create && <AccountCreate onClose={() => setCreate(false)} onSaved={value => saved(value, 'Account created. Share the password with its owner through your agreed private channel.')} />}
    {edit && <AccountChange user={edit.user} action={edit.action} onClose={() => setEdit(null)} onSaved={value => saved(value, edit.action === 'password' ? 'Password reset. Earlier sessions have been revoked.' : `Access ${value.status === 'active' ? 'restored' : 'deactivated'}. Earlier sessions have been revoked.`)} />}
  </div>;
}

function AccountCreate({ onClose, onSaved }: { onClose: () => void; onSaved: (user: User) => void }) {
  const [name, setName] = useState(''); const [email, setEmail] = useState('');
  const [password, setPassword] = useState(''); const [role, setRole] = useState('student');
  const [busy, setBusy] = useState(false); const pending = useRef(false); const [error, setError] = useState<unknown>(null);
  const submit = async (event: FormEvent) => {
    event.preventDefault(); if (pending.current) return; pending.current = true; setBusy(true); setError(null);
    try { const user = await post<User>('/admin/users', { full_name: name.trim(), email: email.trim(), password, role }); setPassword(''); onSaved(user); }
    catch (caught) { setPassword(''); setError(caught); }
    finally { pending.current = false; setBusy(false); }
  };
  return <Modal title="Create account" onClose={() => { if (!busy) onClose(); }}><form className="stack" onSubmit={submit}><fieldset disabled={busy} className="stack">
    <label>Full name<input required maxLength={120} autoComplete="off" value={name} onChange={event => setName(event.target.value)} /></label>
    <label>Email<input required type="email" autoComplete="off" value={email} onChange={event => setEmail(event.target.value)} /></label>
    <label>Role<select value={role} onChange={event => setRole(event.target.value)}><option value="student">Learner</option><option value="admin">Administrator</option></select></label>
    <label>Initial password<input required type="password" minLength={10} maxLength={128} autoComplete="new-password" value={password} onChange={event => setPassword(event.target.value)} /><small>10–128 characters. Passwords are never shown in the account list.</small></label>
  </fieldset><ErrorNotice error={error} /><Button type="submit" className="primary" disabled={busy}>{busy ? 'Creating…' : 'Create account'}</Button></form></Modal>;
}

function AccountChange({ user, action, onClose, onSaved }: { user: User; action: 'password' | 'status'; onClose: () => void; onSaved: (user: User) => void }) {
  const [password, setPassword] = useState(''); const [confirmation, setConfirmation] = useState('');
  const [busy, setBusy] = useState(false); const pending = useRef(false); const [error, setError] = useState<unknown>(null);
  const nextStatus = user.status === 'active' ? 'deactivated' : 'active';
  const title = action === 'password' ? 'Reset password' : nextStatus === 'active' ? 'Restore access' : 'Deactivate account';
  const submit = async (event: FormEvent) => {
    event.preventDefault(); if (pending.current) return;
    if (action === 'password' && password !== confirmation) { setError(new Error('The passwords do not match.')); return; }
    pending.current = true; setBusy(true); setError(null);
    try { const value = await patch<User>(`/admin/users/${user.id}`, { version: user.version, ...(action === 'password' ? { password } : { status: nextStatus }) }); setPassword(''); setConfirmation(''); onSaved(value); }
    catch (caught) { setPassword(''); setConfirmation(''); setError(caught); }
    finally { pending.current = false; setBusy(false); }
  };
  return <Modal title={title} onClose={() => { if (!busy) onClose(); }}><form className="stack" onSubmit={submit}><p>{user.full_name} · {user.email}</p><p className="secondary">This change revokes existing sessions. Saved conversations remain available when access is active.</p>
    {action === 'password' && <fieldset className="stack" disabled={busy}><label>New password<input required type="password" minLength={10} maxLength={128} autoComplete="new-password" value={password} onChange={event => setPassword(event.target.value)} /></label><label>Confirm new password<input required type="password" minLength={10} maxLength={128} autoComplete="new-password" value={confirmation} onChange={event => setConfirmation(event.target.value)} /></label></fieldset>}
    <ErrorNotice error={error} />{!!error && <p className="secondary">If the account changed elsewhere, close this dialog and refresh the list before trying again.</p>}<div className="form-actions"><Button className="primary" type="submit" disabled={busy}>{busy ? 'Saving…' : title}</Button><Button disabled={busy} onClick={onClose}>Cancel</Button></div>
  </form></Modal>;
}
