'use client';

import React, { useEffect, useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiFetchJson } from '@/lib/api';
import { useAuth } from '@/context/AuthContext';
import {
  Loader2,
  Search,
  Plus,
  Crown,
  Shield,
  ShieldOff,
  UserX,
  UserCheck,
  Trash2,
  KeyRound,
  Users,
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
  email: '',
  password: '',
  first_name: '',
  last_name: '',
  role: 'general',
  disabled: false,
};

export default function UserManager() {
  const { user: currentUser } = useAuth();
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

  const { data: users = [], isLoading, isFetching, isError, error } = useQuery<AdminUser[]>({
    queryKey: ['admin-users', debouncedSearch],
    queryFn: () =>
      apiFetchJson<AdminUser[]>(
        `/api/admin/users?limit=500&offset=0&search=${encodeURIComponent(debouncedSearch)}`
      ),
    staleTime: 1000 * 30,
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
    onError: (e: any) => {
      setFlash({ type: 'error', text: e?.message || 'Failed to create user.' });
    },
  });

  const updateUserMutation = useMutation({
    mutationFn: async ({ id, payload }: { id: string; payload: Record<string, any> }) =>
      apiFetchJson<AdminUser>(`/api/admin/users/${id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-users'] });
    },
  });

  const deleteUserMutation = useMutation({
    mutationFn: async (id: string) =>
      apiFetchJson<{ message: string }>(`/api/admin/users/${id}`, {
        method: 'DELETE',
      }),
    onSuccess: () => {
      setFlash({ type: 'success', text: 'User deleted.' });
      queryClient.invalidateQueries({ queryKey: ['admin-users'] });
    },
  });

  const totals = useMemo(() => {
    const all = users.length;
    const owners = users.filter((u) => (u.role || '').toLowerCase() === 'owner').length;
    const admins = users.filter((u) => ['owner', 'admin'].includes((u.role || '').toLowerCase())).length;
    const disabled = users.filter((u) => u.disabled).length;
    return { all, owners, admins, disabled };
  }, [users]);

  const runUserAction = async (
    target: AdminUser,
    action: () => Promise<any>,
    successMessage: string
  ) => {
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
    if (!form.email.trim()) {
      setFlash({ type: 'error', text: 'Email is required.' });
      return;
    }
    if (!form.password.trim() || form.password.trim().length < 6) {
      setFlash({ type: 'error', text: 'Password must be at least 6 characters.' });
      return;
    }
    createUserMutation.mutate({
      ...form,
      email: form.email.trim(),
      password: form.password.trim(),
      first_name: form.first_name.trim(),
      last_name: form.last_name.trim(),
    });
  };

  return (
    <div className="space-y-6">
      {/* Header Card */}
      <div className="rounded-3xl border border-border/50 bg-gradient-to-br from-card/80 via-card/60 to-card/40 backdrop-blur-xl p-6 md:p-8 shadow-xl">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-6">
          <div>
            <h2 className="text-2xl font-bold text-foreground tracking-tight flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center shadow-lg shadow-indigo-500/20">
                <Users className="w-5 h-5 text-white" />
              </div>
              User Management
            </h2>
            <p className="text-xs text-muted-foreground font-mono tracking-wider uppercase mt-1">
              Roles • Permissions • Account Control
            </p>
          </div>
          <button
            onClick={() => setShowCreate((p) => !p)}
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-indigo-500 to-violet-500 hover:from-indigo-400 hover:to-violet-400 text-white text-sm font-semibold shadow-lg shadow-indigo-500/20 transition-all"
          >
            <Plus className="w-4 h-4" /> {showCreate ? 'Close Form' : 'New User'}
          </button>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <div className="rounded-xl border border-border/50 bg-gradient-to-br from-background/60 to-background/40 backdrop-blur-sm px-4 py-3">
            <div className="text-[10px] font-mono text-muted-foreground uppercase tracking-wider mb-1">Total Users</div>
            <div className="text-2xl font-bold text-foreground">{totals.all}</div>
          </div>
          <div className="rounded-xl border border-emerald-500/30 bg-gradient-to-br from-emerald-500/10 to-emerald-500/5 backdrop-blur-sm px-4 py-3">
            <div className="text-[10px] font-mono text-emerald-600 dark:text-emerald-400 uppercase tracking-wider mb-1">Admin/Owner</div>
            <div className="text-2xl font-bold text-emerald-700 dark:text-emerald-300">{totals.admins}</div>
          </div>
          <div className="rounded-xl border border-amber-500/30 bg-gradient-to-br from-amber-500/10 to-amber-500/5 backdrop-blur-sm px-4 py-3">
            <div className="text-[10px] font-mono text-amber-600 dark:text-amber-400 uppercase tracking-wider mb-1">Disabled</div>
            <div className="text-2xl font-bold text-amber-700 dark:text-amber-300">{totals.disabled}</div>
          </div>
        </div>
      </div>

      {showCreate && (
        <div className="rounded-3xl border border-border/50 bg-gradient-to-br from-card/80 via-card/60 to-card/40 backdrop-blur-xl p-6 md:p-8 shadow-xl">
          <h3 className="text-lg font-bold text-foreground uppercase tracking-wider mb-6 flex items-center gap-2">
            <Plus className="w-5 h-5 text-indigo-500" />
            Create New User
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
            <Field label="Email" value={form.email} onChange={(v) => setForm({ ...form, email: v })} />
            <Field label="Password" type="password" value={form.password} onChange={(v) => setForm({ ...form, password: v })} />
            <Field label="First Name" value={form.first_name} onChange={(v) => setForm({ ...form, first_name: v })} />
            <Field label="Last Name" value={form.last_name} onChange={(v) => setForm({ ...form, last_name: v })} />
          </div>
          <div className="flex flex-wrap items-end gap-4 mb-6">
            <label className="text-xs text-muted-foreground">
              <div className="mb-2 font-semibold uppercase tracking-wider">Role</div>
              <select
                value={form.role}
                onChange={(e) => setForm({ ...form, role: e.target.value as CreateUserForm['role'] })}
                className="px-4 py-2.5 rounded-xl bg-background/60 border border-border text-sm text-foreground outline-none focus:border-indigo-500/40 focus:ring-2 focus:ring-indigo-500/20 transition-all"
              >
                <option value="general">General</option>
                <option value="admin">Admin</option>
                <option value="owner">Owner</option>
              </select>
            </label>
            <Toggle
              label="Disabled"
              checked={form.disabled}
              onChange={(checked) => setForm({ ...form, disabled: checked })}
            />
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={handleCreate}
              disabled={createUserMutation.isPending}
              className="inline-flex items-center gap-2 px-6 py-2.5 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-400 hover:to-teal-400 text-white text-sm font-semibold shadow-lg shadow-emerald-500/20 disabled:opacity-50 transition-all"
            >
              {createUserMutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
              Create User
            </button>
            <button
              onClick={() => {
                setShowCreate(false);
                setForm(EMPTY_FORM);
              }}
              className="px-6 py-2.5 rounded-xl border border-border/60 bg-background/40 hover:bg-accent/40 text-sm text-foreground font-semibold transition-all"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      <div className="rounded-3xl border border-border/50 bg-gradient-to-br from-card/80 via-card/60 to-card/40 backdrop-blur-xl p-6 md:p-8 shadow-xl">
        <div className="mb-4 relative">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by email or name..."
            className="w-full pl-12 pr-4 py-3 rounded-xl bg-background/60 border border-border text-sm text-foreground placeholder:text-muted-foreground outline-none focus:border-indigo-500/40 focus:ring-2 focus:ring-indigo-500/20 transition-all"
          />
        </div>

        {flash && (
          <div
            className={`mb-4 rounded-xl px-4 py-3 text-sm font-medium flex items-center gap-2 ${
              flash.type === 'success'
                ? 'bg-emerald-500/10 text-emerald-300 border border-emerald-500/20'
                : 'bg-rose-500/10 text-rose-300 border border-rose-500/20'
            }`}
          >
            {flash.type === 'success' ? '✓' : '⚠'} {flash.text}
          </div>
        )}

        {isLoading ? (
          <div className="py-20 text-center">
            <Loader2 className="w-8 h-8 animate-spin text-indigo-400 mx-auto mb-3" />
            <p className="text-sm text-muted-foreground">Loading users...</p>
          </div>
        ) : isError ? (
          <div className="py-20 text-center">
            <div className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-rose-500/10 border border-rose-500/20 text-sm text-rose-300">
              ⚠ {(error as Error)?.message || 'Failed to load users.'}
            </div>
          </div>
        ) : (
          <div className="overflow-x-auto border border-border/50 rounded-2xl bg-background/40 backdrop-blur-sm">
            <table className="w-full min-w-[880px] text-left">
              <thead className="bg-gradient-to-r from-muted/30 to-muted/20 border-b border-border text-[11px] uppercase tracking-wider text-muted-foreground">
                <tr>
                  <th className="px-4 py-3 font-bold">Name</th>
                  <th className="px-4 py-3 font-bold">Email</th>
                  <th className="px-4 py-3 font-bold">Role</th>
                  <th className="px-4 py-3 font-bold">Status</th>
                  <th className="px-4 py-3 font-bold">Created</th>
                  <th className="px-4 py-3 font-bold">Actions</th>
                </tr>
              </thead>
              <tbody>
                {users.map((u) => {
                  const role = (u.role || 'general').toLowerCase();
                  const isSelf = currentUser?.id === u.id;
                  const rowBusy =
                    busyUserId === u.id ||
                    updateUserMutation.isPending ||
                    deleteUserMutation.isPending;
                  return (
                    <tr key={u.id} className="border-b border-border/30 text-sm text-foreground hover:bg-accent/10 transition-colors group">
                      <td className="px-4 py-3">
                        <div className="font-semibold">
                          {[u.first_name, u.last_name].filter(Boolean).join(' ') || '—'}
                        </div>
                        {isSelf && <div className="text-[10px] text-indigo-500 dark:text-indigo-300 font-mono mt-0.5">You</div>}
                      </td>
                      <td className="px-4 py-3 font-mono text-xs text-muted-foreground">{u.email}</td>
                      <td className="px-4 py-3">
                        {role === 'owner' ? (
                          <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-semibold bg-gradient-to-r from-amber-500/15 to-orange-500/15 text-amber-700 dark:text-amber-300 border border-amber-500/30">
                            <Crown className="w-3.5 h-3.5" /> Owner
                          </span>
                        ) : role === 'admin' ? (
                          <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-semibold bg-gradient-to-r from-emerald-500/15 to-teal-500/15 text-emerald-700 dark:text-emerald-300 border border-emerald-500/30">
                            <Shield className="w-3.5 h-3.5" /> Admin
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-semibold bg-muted/50 text-muted-foreground border border-border/70">
                            <ShieldOff className="w-3.5 h-3.5" /> General
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        {u.disabled ? (
                          <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-semibold bg-rose-500/10 text-rose-700 dark:text-rose-300 border border-rose-500/30">
                            <UserX className="w-3.5 h-3.5" /> Disabled
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-semibold bg-sky-500/10 text-sky-700 dark:text-sky-300 border border-sky-500/30">
                            <UserCheck className="w-3.5 h-3.5" /> Active
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-xs text-muted-foreground font-mono">
                        {u.created_at ? new Date(u.created_at).toLocaleDateString() : '—'}
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex flex-wrap items-center gap-1.5 opacity-100 md:opacity-0 md:group-hover:opacity-100 transition-opacity">
                          <button
                            disabled={rowBusy || isSelf}
                            onClick={() =>
                              runUserAction(
                                u,
                                () =>
                                  updateUserMutation.mutateAsync({
                                    id: u.id,
                                    payload: {
                                      role:
                                        role === 'general'
                                          ? 'admin'
                                          : role === 'admin'
                                            ? 'general'
                                            : 'admin',
                                    },
                                  }),
                                role === 'general'
                                  ? 'Admin role granted.'
                                  : role === 'admin'
                                    ? 'Role changed to general.'
                                    : 'Owner role changed to admin.'
                              )
                            }
                            className="px-2.5 py-1.5 text-[10px] font-semibold rounded-lg border border-border/70 text-foreground hover:bg-accent/30 disabled:opacity-40 transition-all"
                          >
                            {role === 'general' ? 'Make Admin' : role === 'admin' ? 'Make General' : 'Set Admin'}
                          </button>
                          <button
                            disabled={rowBusy || isSelf || role === 'owner'}
                            onClick={() =>
                              runUserAction(
                                u,
                                () =>
                                  updateUserMutation.mutateAsync({
                                    id: u.id,
                                    payload: { role: 'owner' },
                                  }),
                                'User promoted to owner.'
                              )
                            }
                            className="px-2.5 py-1.5 text-[10px] font-semibold rounded-lg border border-amber-500/40 text-amber-700 dark:text-amber-300 hover:bg-amber-500/10 disabled:opacity-40 inline-flex items-center gap-1 transition-all"
                          >
                            <Crown className="w-3 h-3" /> Owner
                          </button>
                          <button
                            disabled={rowBusy || isSelf}
                            onClick={() =>
                              runUserAction(
                                u,
                                () =>
                                  updateUserMutation.mutateAsync({
                                    id: u.id,
                                    payload: { disabled: !u.disabled },
                                  }),
                                u.disabled ? 'User enabled.' : 'User disabled.'
                              )
                            }
                            className="px-2.5 py-1.5 text-[10px] font-semibold rounded-lg border border-border/70 text-foreground hover:bg-accent/30 disabled:opacity-40 transition-all"
                          >
                            {u.disabled ? 'Enable' : 'Disable'}
                          </button>
                          <button
                            disabled={rowBusy}
                            onClick={async () => {
                              const pw = window.prompt(`Set a new password for ${u.email} (min 6 chars):`);
                              if (!pw) return;
                              if (pw.trim().length < 6) {
                                setFlash({ type: 'error', text: 'Password must be at least 6 characters.' });
                                return;
                              }
                              await runUserAction(
                                u,
                                () =>
                                  updateUserMutation.mutateAsync({
                                    id: u.id,
                                    payload: { password: pw.trim() },
                                  }),
                                'Password updated.'
                              );
                            }}
                            className="px-2.5 py-1.5 text-[10px] font-semibold rounded-lg border border-indigo-500/40 text-indigo-700 dark:text-indigo-300 hover:bg-indigo-500/10 disabled:opacity-40 inline-flex items-center gap-1 transition-all"
                          >
                            <KeyRound className="w-3 h-3" /> Password
                          </button>
                          <button
                            disabled={rowBusy || isSelf}
                            onClick={async () => {
                              const ok = window.confirm(`Delete user ${u.email}? This cannot be undone.`);
                              if (!ok) return;
                              await runUserAction(
                                u,
                                () => deleteUserMutation.mutateAsync(u.id),
                                'User deleted.'
                              );
                            }}
                            className="px-2.5 py-1.5 text-[10px] font-semibold rounded-lg border border-rose-500/40 text-rose-700 dark:text-rose-300 hover:bg-rose-500/10 disabled:opacity-40 inline-flex items-center gap-1 transition-all"
                          >
                            <Trash2 className="w-3 h-3" /> Delete
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
        {isFetching && !isLoading && (
          <div className="mt-3 text-[10px] text-muted-foreground font-mono flex items-center gap-2">
            <Loader2 className="w-3 h-3 animate-spin" />
            Refreshing user list...
          </div>
        )}
      </div>
    </div>
  );
}

function Field({
  label,
  value,
  onChange,
  type = 'text',
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  type?: string;
}) {
  return (
    <label className="text-xs text-muted-foreground">
      <div className="mb-2 font-semibold uppercase tracking-wider">{label}</div>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full px-4 py-2.5 rounded-xl bg-background/60 border border-border text-sm text-foreground outline-none focus:border-indigo-500/40 focus:ring-2 focus:ring-indigo-500/20 transition-all"
      />
    </label>
  );
}

function Toggle({
  label,
  checked,
  onChange,
}: {
  label: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
}) {
  return (
    <label className="inline-flex items-center gap-3 text-sm text-foreground cursor-pointer">
      <div className="relative">
        <input
          type="checkbox"
          checked={checked}
          onChange={(e) => onChange(e.target.checked)}
          className="sr-only peer"
        />
        <div className="w-11 h-6 bg-muted rounded-full peer peer-checked:bg-indigo-500 transition-colors" />
        <div className="absolute left-1 top-1 w-4 h-4 bg-white rounded-full transition-transform peer-checked:translate-x-5" />
      </div>
      <span className="font-medium">{label}</span>
    </label>
  );
}
