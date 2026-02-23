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
    <div className="space-y-4">
      <div className="rounded-2xl border border-border/60 bg-card/70 backdrop-blur-sm p-4 md:p-5">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3">
          <div>
            <h1 className="text-2xl font-bold text-foreground tracking-tight flex items-center gap-2">
              <Users className="w-6 h-6 text-indigo-400" /> User Manager
            </h1>
            <p className="text-xs text-muted-foreground font-mono tracking-wider uppercase">
              Admin Panel • Roles, Access, and Account Status
            </p>
          </div>
          <button
            onClick={() => setShowCreate((p) => !p)}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-indigo-600/90 hover:bg-indigo-500 text-white text-xs font-semibold"
          >
            <Plus className="w-4 h-4" /> {showCreate ? 'Close' : 'New User'}
          </button>
        </div>

        <div className="mt-4 grid grid-cols-1 sm:grid-cols-3 gap-2">
          <div className="rounded-lg border border-border/60 bg-background/40 px-3 py-2 text-xs text-muted-foreground">
            Total Users: <span className="font-bold text-foreground">{totals.all}</span>
          </div>
          <div className="rounded-lg border border-emerald-500/30 bg-emerald-500/10 px-3 py-2 text-xs text-emerald-700 dark:text-emerald-300">
            Admin/Owner: <span className="font-bold text-emerald-800 dark:text-emerald-200">{totals.admins}</span>
          </div>
          <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs text-amber-700 dark:text-amber-300">
            Disabled: <span className="font-bold text-amber-800 dark:text-amber-200">{totals.disabled}</span>
          </div>
        </div>
      </div>

      {showCreate && (
        <div className="rounded-2xl border border-border/60 bg-card/70 backdrop-blur-sm p-4 md:p-5 space-y-3">
          <h2 className="text-sm font-semibold text-foreground uppercase tracking-wider">Create User</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <Field label="Email" value={form.email} onChange={(v) => setForm({ ...form, email: v })} />
            <Field label="Password" type="password" value={form.password} onChange={(v) => setForm({ ...form, password: v })} />
            <Field label="First Name" value={form.first_name} onChange={(v) => setForm({ ...form, first_name: v })} />
            <Field label="Last Name" value={form.last_name} onChange={(v) => setForm({ ...form, last_name: v })} />
          </div>
          <div className="flex flex-wrap items-end gap-4">
            <label className="text-xs text-muted-foreground">
              <div className="mb-1">Role</div>
              <select
                value={form.role}
                onChange={(e) => setForm({ ...form, role: e.target.value as CreateUserForm['role'] })}
                className="px-3 py-2 rounded-lg bg-background/60 border border-border text-sm text-foreground outline-none focus:border-indigo-500/40"
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
          <div className="flex items-center gap-2">
            <button
              onClick={handleCreate}
              disabled={createUserMutation.isPending}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-emerald-600/90 hover:bg-emerald-500 text-white text-xs font-semibold disabled:opacity-50"
            >
              {createUserMutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
              Create
            </button>
            <button
              onClick={() => {
                setShowCreate(false);
                setForm(EMPTY_FORM);
              }}
              className="px-4 py-2 rounded-lg border border-border/60 bg-background/40 hover:bg-accent/40 text-xs text-foreground"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      <div className="rounded-2xl border border-border/60 bg-card/70 backdrop-blur-sm p-4 md:p-5">
        <div className="mb-3 relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by email or name..."
            className="w-full pl-9 pr-3 py-2 rounded-lg bg-background/60 border border-border text-sm text-foreground placeholder:text-muted-foreground outline-none focus:border-indigo-500/40"
          />
        </div>

        {flash && (
          <div
            className={`mb-3 rounded-lg px-3 py-2 text-xs ${
              flash.type === 'success'
                ? 'bg-emerald-500/10 text-emerald-300 border border-emerald-500/20'
                : 'bg-rose-500/10 text-rose-300 border border-rose-500/20'
            }`}
          >
            {flash.text}
          </div>
        )}

        {isLoading ? (
          <div className="py-16 text-center">
            <Loader2 className="w-6 h-6 animate-spin text-indigo-400 mx-auto mb-2" />
            <p className="text-xs text-muted-foreground">Loading users...</p>
          </div>
        ) : isError ? (
          <div className="py-16 text-center text-xs text-rose-700 dark:text-rose-300">
            {(error as Error)?.message || 'Failed to load users.'}
          </div>
        ) : (
          <div className="overflow-x-auto border border-border/70 rounded-xl bg-background/40">
            <table className="w-full min-w-[880px] text-left">
              <thead className="bg-muted/20 border-b border-border text-[11px] uppercase tracking-wider text-muted-foreground">
                <tr>
                  <th className="px-3 py-2">Name</th>
                  <th className="px-3 py-2">Email</th>
                  <th className="px-3 py-2">Role</th>
                  <th className="px-3 py-2">Status</th>
                  <th className="px-3 py-2">Created</th>
                  <th className="px-3 py-2">Actions</th>
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
                    <tr key={u.id} className="border-b border-border/40 text-sm text-foreground hover:bg-accent/10 transition-colors">
                      <td className="px-3 py-2">
                        <div className="font-medium">
                          {[u.first_name, u.last_name].filter(Boolean).join(' ') || '—'}
                        </div>
                        {isSelf && <div className="text-[10px] text-indigo-500 dark:text-indigo-300 font-mono">You</div>}
                      </td>
                      <td className="px-3 py-2 font-mono text-xs text-muted-foreground">{u.email}</td>
                      <td className="px-3 py-2">
                        {role === 'owner' ? (
                          <span className="inline-flex items-center gap-1 px-2 py-1 rounded-md text-[10px] bg-amber-500/10 text-amber-700 dark:text-amber-300 border border-amber-500/30">
                            <Crown className="w-3 h-3" /> Owner
                          </span>
                        ) : role === 'admin' ? (
                          <span className="inline-flex items-center gap-1 px-2 py-1 rounded-md text-[10px] bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border border-emerald-500/30">
                            <Shield className="w-3 h-3" /> Admin
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 px-2 py-1 rounded-md text-[10px] bg-muted text-muted-foreground border border-border/70">
                            <ShieldOff className="w-3 h-3" /> General
                          </span>
                        )}
                      </td>
                      <td className="px-3 py-2">
                        {u.disabled ? (
                          <span className="inline-flex items-center gap-1 px-2 py-1 rounded-md text-[10px] bg-amber-500/10 text-amber-700 dark:text-amber-300 border border-amber-500/30">
                            <UserX className="w-3 h-3" /> Disabled
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 px-2 py-1 rounded-md text-[10px] bg-sky-500/10 text-sky-700 dark:text-sky-300 border border-sky-500/30">
                            <UserCheck className="w-3 h-3" /> Active
                          </span>
                        )}
                      </td>
                      <td className="px-3 py-2 text-xs text-muted-foreground font-mono">
                        {u.created_at ? new Date(u.created_at).toLocaleDateString() : '—'}
                      </td>
                      <td className="px-3 py-2">
                        <div className="flex flex-wrap items-center gap-1.5">
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
                            className="px-2 py-1 text-[10px] rounded-md border border-border/70 text-foreground hover:bg-accent/30 disabled:opacity-40"
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
                            className="px-2 py-1 text-[10px] rounded-md border border-amber-500/40 text-amber-700 dark:text-amber-300 hover:bg-amber-500/10 disabled:opacity-40 inline-flex items-center gap-1"
                          >
                            <Crown className="w-3 h-3" /> Make Owner
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
                            className="px-2 py-1 text-[10px] rounded-md border border-border/70 text-foreground hover:bg-accent/30 disabled:opacity-40"
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
                            className="px-2 py-1 text-[10px] rounded-md border border-indigo-500/40 text-indigo-700 dark:text-indigo-300 hover:bg-indigo-500/10 disabled:opacity-40 inline-flex items-center gap-1"
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
                            className="px-2 py-1 text-[10px] rounded-md border border-rose-500/40 text-rose-700 dark:text-rose-300 hover:bg-rose-500/10 disabled:opacity-40 inline-flex items-center gap-1"
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
          <div className="mt-2 text-[10px] text-muted-foreground font-mono">Refreshing user list...</div>
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
      <div className="mb-1">{label}</div>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full px-3 py-2 rounded-lg bg-background/60 border border-border text-sm text-foreground outline-none focus:border-indigo-500/40"
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
    <label className="inline-flex items-center gap-2 text-xs text-foreground cursor-pointer">
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        className="rounded border-input bg-background text-indigo-500 focus:ring-indigo-500/40"
      />
      {label}
    </label>
  );
}
