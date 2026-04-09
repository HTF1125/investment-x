'use client';

import React, { useEffect, useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiFetchJson } from '@/lib/api';
import { useAuth } from '@/context/AuthContext';
import { useTheme } from '@/context/ThemeContext';
import {
  Loader2, Search, Plus, Crown, Shield, ShieldOff,
  UserX, UserCheck, Trash2, KeyRound, X, Check, AlertCircle,
} from 'lucide-react';

interface AdminUser {
  id: string;
  email: string;
  first_name?: string | null;
  last_name?: string | null;
  role: 'owner' | 'admin' | 'general' | string;
  is_admin: boolean;
  disabled: boolean;
  created_at?: string | null;
}

interface CreateUserForm {
  email: string;
  password: string;
  first_name: string;
  last_name: string;
  role: 'owner' | 'admin' | 'general';
  disabled: boolean;
}

const EMPTY_FORM: CreateUserForm = {
  email: '', password: '', first_name: '', last_name: '', role: 'general', disabled: false,
};

// ── Helpers ──

function RoleBadge({ role }: { role: string }) {
  const r = role.toLowerCase();
  if (r === 'owner') return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-[var(--radius)] text-[11.5px] font-mono font-semibold bg-warning/[0.08] text-warning border border-warning/20">
      <Crown className="w-3 h-3" />OWNER
    </span>
  );
  if (r === 'admin') return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-[var(--radius)] text-[11.5px] font-mono font-semibold bg-success/[0.08] text-success border border-success/20">
      <Shield className="w-3 h-3" />ADMIN
    </span>
  );
  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-[var(--radius)] text-[11.5px] font-mono font-semibold text-muted-foreground/60 border border-border/30">
      <ShieldOff className="w-3 h-3" />GENERAL
    </span>
  );
}

function StatusBadge({ disabled }: { disabled: boolean }) {
  if (disabled) return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-[var(--radius)] text-[11.5px] font-mono font-semibold bg-destructive/[0.08] text-destructive border border-destructive/20">
      <UserX className="w-3 h-3" />OFF
    </span>
  );
  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-[var(--radius)] text-[11.5px] font-mono font-semibold bg-primary/[0.06] text-primary border border-primary/20">
      <UserCheck className="w-3 h-3" />ON
    </span>
  );
}

// ── Main ──

export default function UserManager() {
  const { user: currentUser } = useAuth();
  const { theme } = useTheme();
  const queryClient = useQueryClient();

  const [search, setSearch] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState<CreateUserForm>(EMPTY_FORM);
  const [busyUserId, setBusyUserId] = useState<string | null>(null);
  const [flash, setFlash] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  useEffect(() => {
    const t = setTimeout(() => setDebouncedSearch(search.trim()), 250);
    return () => clearTimeout(t);
  }, [search]);

  // Auto-clear flash
  useEffect(() => {
    if (!flash) return;
    const t = setTimeout(() => setFlash(null), 4000);
    return () => clearTimeout(t);
  }, [flash]);

  const { data: users = [], isLoading, isFetching, isError, error } = useQuery<AdminUser[]>({
    queryKey: ['admin-users', debouncedSearch],
    queryFn: () => apiFetchJson<AdminUser[]>(`/api/admin/users?limit=500&offset=0&search=${encodeURIComponent(debouncedSearch)}`),
    staleTime: 30_000,
  });

  const createUserMutation = useMutation({
    mutationFn: async (payload: CreateUserForm) =>
      apiFetchJson<AdminUser>('/api/admin/users', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      }),
    onSuccess: () => {
      setFlash({ type: 'success', text: 'User created.' });
      setForm(EMPTY_FORM);
      setShowCreate(false);
      queryClient.invalidateQueries({ queryKey: ['admin-users'] });
    },
    onError: (e: any) => setFlash({ type: 'error', text: e?.message || 'Failed to create user.' }),
  });

  const updateUserMutation = useMutation({
    mutationFn: async ({ id, payload }: { id: string; payload: Record<string, any> }) =>
      apiFetchJson<AdminUser>(`/api/admin/users/${id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['admin-users'] }),
  });

  const deleteUserMutation = useMutation({
    mutationFn: async (id: string) =>
      apiFetchJson<{ message: string }>(`/api/admin/users/${id}`, { method: 'DELETE' }),
    onSuccess: () => {
      setFlash({ type: 'success', text: 'User deleted.' });
      queryClient.invalidateQueries({ queryKey: ['admin-users'] });
    },
  });

  const totals = useMemo(() => {
    const all = users.length;
    const admins = users.filter(u => ['owner', 'admin'].includes((u.role || '').toLowerCase())).length;
    const disabled = users.filter(u => u.disabled).length;
    return { all, admins, disabled };
  }, [users]);

  const runUserAction = async (target: AdminUser, action: () => Promise<any>, successMessage: string) => {
    setFlash(null);
    setBusyUserId(target.id);
    try {
      await action();
      setFlash({ type: 'success', text: successMessage });
    } catch (e: any) {
      setFlash({ type: 'error', text: e?.message || 'Action failed.' });
    } finally {
      setBusyUserId(null);
    }
  };

  const handleCreate = () => {
    if (!form.email.trim()) { setFlash({ type: 'error', text: 'Email is required.' }); return; }
    if (!form.password.trim() || form.password.trim().length < 6) { setFlash({ type: 'error', text: 'Password must be at least 6 characters.' }); return; }
    createUserMutation.mutate({ ...form, email: form.email.trim(), password: form.password.trim(), first_name: form.first_name.trim(), last_name: form.last_name.trim() });
  };

  const formStyle = { colorScheme: theme === 'light' ? 'light' as const : 'dark' as const, backgroundColor: 'rgb(var(--background))', color: 'rgb(var(--foreground))' };

  return (
    <div className="space-y-3">

      {/* ── Toolbar: stats + search + add ── */}
      <div className="flex items-center gap-2 sm:gap-3 flex-wrap">
        {/* Stats */}
        <div className="flex items-center gap-2">
          <span className="text-[11.5px] font-mono text-muted-foreground/40 tabular-nums">{totals.all} users</span>
          <span className="w-px h-3 bg-border/30" />
          <span className="text-[11.5px] font-mono text-success/60 tabular-nums">{totals.admins} admin</span>
          {totals.disabled > 0 && (
            <>
              <span className="w-px h-3 bg-border/30" />
              <span className="text-[11.5px] font-mono text-destructive/60 tabular-nums">{totals.disabled} disabled</span>
            </>
          )}
        </div>

        <div className="flex-1 min-w-[8px]" />

        {/* Search */}
        <div className="relative order-last sm:order-none w-full sm:w-auto">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3 h-3 text-muted-foreground/40" />
          <input
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Search..."
            className="h-7 w-full sm:w-48 pl-7 pr-2.5 text-[12.5px] border border-border/40 rounded-[var(--radius)] bg-background text-foreground placeholder:text-muted-foreground/30 focus:outline-none focus:border-primary/50 transition-colors"
            style={formStyle}
          />
          {search && (
            <button onClick={() => setSearch('')} className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground/30 hover:text-foreground">
              <X className="w-3 h-3" />
            </button>
          )}
        </div>

        {/* Add user button */}
        <button onClick={() => setShowCreate(p => !p)} className="btn-toolbar gap-1">
          {showCreate ? <X className="w-3 h-3" /> : <Plus className="w-3 h-3" />}
          <span className="text-[11.5px] font-semibold">{showCreate ? 'Cancel' : 'Add User'}</span>
        </button>
      </div>

      {/* ── Flash message ── */}
      {flash && (
        <div className={`flex items-center gap-2 px-3 py-1.5 rounded-[var(--radius)] text-[12.5px] font-medium ${
          flash.type === 'success'
            ? 'bg-success/[0.06] border border-success/20 text-success'
            : 'bg-destructive/[0.06] border border-destructive/20 text-destructive'
        }`}>
          {flash.type === 'success' ? <Check className="w-3 h-3 shrink-0" /> : <AlertCircle className="w-3 h-3 shrink-0" />}
          {flash.text}
          <button onClick={() => setFlash(null)} className="ml-auto opacity-50 hover:opacity-100"><X className="w-3 h-3" /></button>
        </div>
      )}

      {/* ── Create user form ── */}
      {showCreate && (
        <div className="panel-card p-3 sm:p-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3 mb-3">
            <div>
              <label className="stat-label block mb-1">Email</label>
              <input value={form.email} onChange={e => setForm({ ...form, email: e.target.value })}
                className="w-full h-7 px-2.5 text-[12.5px] border border-border/50 rounded-[var(--radius)] bg-background text-foreground focus:outline-none focus:border-primary/50"
                style={formStyle} />
            </div>
            <div>
              <label className="stat-label block mb-1">Password</label>
              <input type="password" value={form.password} onChange={e => setForm({ ...form, password: e.target.value })}
                className="w-full h-7 px-2.5 text-[12.5px] border border-border/50 rounded-[var(--radius)] bg-background text-foreground focus:outline-none focus:border-primary/50"
                style={formStyle} />
            </div>
            <div>
              <label className="stat-label block mb-1">First Name</label>
              <input value={form.first_name} onChange={e => setForm({ ...form, first_name: e.target.value })}
                className="w-full h-7 px-2.5 text-[12.5px] border border-border/50 rounded-[var(--radius)] bg-background text-foreground focus:outline-none focus:border-primary/50"
                style={formStyle} />
            </div>
            <div>
              <label className="stat-label block mb-1">Last Name</label>
              <input value={form.last_name} onChange={e => setForm({ ...form, last_name: e.target.value })}
                className="w-full h-7 px-2.5 text-[12.5px] border border-border/50 rounded-[var(--radius)] bg-background text-foreground focus:outline-none focus:border-primary/50"
                style={formStyle} />
            </div>
          </div>
          <div className="flex items-center gap-3">
            <select value={form.role} onChange={e => setForm({ ...form, role: e.target.value as CreateUserForm['role'] })}
              className="h-7 px-2.5 text-[12.5px] border border-border/50 rounded-[var(--radius)] bg-background text-foreground focus:outline-none focus:border-primary/50 cursor-pointer"
              style={formStyle}>
              <option value="general">General</option>
              <option value="admin">Admin</option>
              <option value="owner">Owner</option>
            </select>
            <button onClick={handleCreate} disabled={createUserMutation.isPending} className="btn-primary">
              {createUserMutation.isPending ? <Loader2 className="w-3 h-3 animate-spin" /> : <Plus className="w-3 h-3" />}
              Create
            </button>
          </div>
        </div>
      )}

      {/* ── User list ── */}
      {isLoading ? (
        <div className="flex items-center justify-center py-16">
          <Loader2 className="w-4 h-4 animate-spin text-muted-foreground/30" />
        </div>
      ) : isError ? (
        <div className="flex items-center justify-center py-16">
          <span className="text-[12.5px] text-destructive flex items-center gap-1.5">
            <AlertCircle className="w-3 h-3" />{(error as Error)?.message || 'Failed to load users.'}
          </span>
        </div>
      ) : (
        <>
          {/* ── Desktop table (md+) ── */}
          <div className="hidden md:block overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-border/30">
                  <th className="stat-label text-left px-3 py-2">User</th>
                  <th className="stat-label text-left px-3 py-2">Role</th>
                  <th className="stat-label text-left px-3 py-2">Status</th>
                  <th className="stat-label text-left px-3 py-2">Created</th>
                  <th className="stat-label text-right px-3 py-2">Actions</th>
                </tr>
              </thead>
              <tbody>
                {users.map(u => {
                  const role = (u.role || 'general').toLowerCase();
                  const isSelf = currentUser?.id === u.id;
                  const rowBusy = busyUserId === u.id;
                  const name = [u.first_name, u.last_name].filter(Boolean).join(' ');
                  return (
                    <tr key={u.id} className="border-b border-border/10 hover:bg-foreground/[0.02] transition-colors group">
                      <td className="px-3 py-2">
                        <div className="flex items-center gap-2.5">
                          <div className="w-7 h-7 rounded-full bg-foreground/[0.06] border border-border/30 flex items-center justify-center text-[11.5px] font-mono font-bold text-muted-foreground/50 uppercase shrink-0">
                            {(u.first_name?.[0] || u.email[0])}
                          </div>
                          <div className="min-w-0">
                            <div className="text-[13px] font-semibold text-foreground truncate">
                              {name || u.email.split('@')[0]}
                              {isSelf && <span className="ml-1.5 text-[11px] font-mono text-primary/60">you</span>}
                            </div>
                            <div className="text-[11.5px] font-mono text-muted-foreground/40 truncate">{u.email}</div>
                          </div>
                        </div>
                      </td>
                      <td className="px-3 py-2"><RoleBadge role={role} /></td>
                      <td className="px-3 py-2"><StatusBadge disabled={u.disabled} /></td>
                      <td className="px-3 py-2 text-[11.5px] font-mono text-muted-foreground/40 tabular-nums">
                        {u.created_at ? new Date(u.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: '2-digit' }) : '—'}
                      </td>
                      <td className="px-3 py-2">
                        <UserActions user={u} role={role} isSelf={isSelf} rowBusy={rowBusy}
                          onRoleToggle={() => runUserAction(u,
                            () => updateUserMutation.mutateAsync({ id: u.id, payload: { role: role === 'general' ? 'admin' : role === 'admin' ? 'general' : 'admin' } }),
                            role === 'general' ? 'Admin granted.' : 'Set to general.'
                          )}
                          onOwner={() => runUserAction(u,
                            () => updateUserMutation.mutateAsync({ id: u.id, payload: { role: 'owner' } }),
                            'Promoted to owner.'
                          )}
                          onToggleDisabled={() => runUserAction(u,
                            () => updateUserMutation.mutateAsync({ id: u.id, payload: { disabled: !u.disabled } }),
                            u.disabled ? 'Enabled.' : 'Disabled.'
                          )}
                          onPassword={async () => {
                            const pw = window.prompt(`New password for ${u.email} (min 6 chars):`);
                            if (!pw) return;
                            if (pw.trim().length < 6) { setFlash({ type: 'error', text: 'Min 6 characters.' }); return; }
                            await runUserAction(u,
                              () => updateUserMutation.mutateAsync({ id: u.id, payload: { password: pw.trim() } }),
                              'Password updated.'
                            );
                          }}
                          onDelete={async () => {
                            if (!window.confirm(`Delete ${u.email}?`)) return;
                            await runUserAction(u, () => deleteUserMutation.mutateAsync(u.id), 'Deleted.');
                          }}
                          className="justify-end opacity-0 group-hover:opacity-100 transition-opacity"
                        />
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* ── Mobile card list (<md) ── */}
          <div className="md:hidden space-y-2">
            {users.map(u => {
              const role = (u.role || 'general').toLowerCase();
              const isSelf = currentUser?.id === u.id;
              const rowBusy = busyUserId === u.id;
              const name = [u.first_name, u.last_name].filter(Boolean).join(' ');
              return (
                <div key={u.id} className="panel-card p-3">
                  <div className="flex items-center gap-2.5 mb-2">
                    <div className="w-8 h-8 rounded-full bg-foreground/[0.06] border border-border/30 flex items-center justify-center text-[12.5px] font-mono font-bold text-muted-foreground/50 uppercase shrink-0">
                      {(u.first_name?.[0] || u.email[0])}
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="text-[13px] font-semibold text-foreground truncate">
                        {name || u.email.split('@')[0]}
                        {isSelf && <span className="ml-1.5 text-[11px] font-mono text-primary/60">you</span>}
                      </div>
                      <div className="text-[11.5px] font-mono text-muted-foreground/40 truncate">{u.email}</div>
                    </div>
                    <div className="flex items-center gap-1.5 shrink-0">
                      <RoleBadge role={role} />
                      <StatusBadge disabled={u.disabled} />
                    </div>
                  </div>
                  <UserActions user={u} role={role} isSelf={isSelf} rowBusy={rowBusy}
                    onRoleToggle={() => runUserAction(u,
                      () => updateUserMutation.mutateAsync({ id: u.id, payload: { role: role === 'general' ? 'admin' : role === 'admin' ? 'general' : 'admin' } }),
                      role === 'general' ? 'Admin granted.' : 'Set to general.'
                    )}
                    onOwner={() => runUserAction(u,
                      () => updateUserMutation.mutateAsync({ id: u.id, payload: { role: 'owner' } }),
                      'Promoted to owner.'
                    )}
                    onToggleDisabled={() => runUserAction(u,
                      () => updateUserMutation.mutateAsync({ id: u.id, payload: { disabled: !u.disabled } }),
                      u.disabled ? 'Enabled.' : 'Disabled.'
                    )}
                    onPassword={async () => {
                      const pw = window.prompt(`New password for ${u.email} (min 6 chars):`);
                      if (!pw) return;
                      if (pw.trim().length < 6) { setFlash({ type: 'error', text: 'Min 6 characters.' }); return; }
                      await runUserAction(u,
                        () => updateUserMutation.mutateAsync({ id: u.id, payload: { password: pw.trim() } }),
                        'Password updated.'
                      );
                    }}
                    onDelete={async () => {
                      if (!window.confirm(`Delete ${u.email}?`)) return;
                      await runUserAction(u, () => deleteUserMutation.mutateAsync(u.id), 'Deleted.');
                    }}
                    className="justify-start"
                  />
                </div>
              );
            })}
          </div>
        </>
      )}

      {/* Refreshing indicator */}
      {isFetching && !isLoading && (
        <div className="flex items-center gap-1.5 text-[11.5px] font-mono text-muted-foreground/30">
          <Loader2 className="w-3 h-3 animate-spin" />Refreshing...
        </div>
      )}
    </div>
  );
}

// ── Action buttons (shared between table and card views) ──

const actionBtn = "h-6 px-2 text-[11px] font-mono font-semibold rounded-[calc(var(--radius)-2px)] disabled:opacity-30 transition-all";

function UserActions({ user, role, isSelf, rowBusy, onRoleToggle, onOwner, onToggleDisabled, onPassword, onDelete, className = '' }: {
  user: AdminUser; role: string; isSelf: boolean; rowBusy: boolean;
  onRoleToggle: () => void; onOwner: () => void; onToggleDisabled: () => void;
  onPassword: () => void; onDelete: () => void; className?: string;
}) {
  return (
    <div className={`flex items-center flex-wrap gap-0.5 ${className}`}>
      <button disabled={rowBusy || isSelf} onClick={onRoleToggle}
        className={`${actionBtn} border border-border/30 text-muted-foreground/60 hover:text-foreground hover:bg-foreground/[0.06]`}>
        {role === 'general' ? 'ADMIN' : role === 'admin' ? 'GENERAL' : 'ADMIN'}
      </button>
      <button disabled={rowBusy || isSelf || role === 'owner'} onClick={onOwner} title="Promote to owner"
        className={`${actionBtn} border border-warning/20 text-warning/60 hover:text-warning hover:bg-warning/[0.06]`}>
        <Crown className="w-3 h-3" />
      </button>
      <button disabled={rowBusy || isSelf} onClick={onToggleDisabled}
        className={`${actionBtn} border border-border/30 text-muted-foreground/60 hover:text-foreground hover:bg-foreground/[0.06]`}>
        {user.disabled ? 'ON' : 'OFF'}
      </button>
      <button disabled={rowBusy} onClick={onPassword} title="Reset password"
        className={`${actionBtn} border border-primary/20 text-primary/60 hover:text-primary hover:bg-primary/[0.06]`}>
        <KeyRound className="w-3 h-3" />
      </button>
      <button disabled={rowBusy || isSelf} onClick={onDelete} title="Delete user"
        className={`${actionBtn} border border-destructive/20 text-destructive/60 hover:text-destructive hover:bg-destructive/[0.06]`}>
        <Trash2 className="w-3 h-3" />
      </button>
    </div>
  );
}
