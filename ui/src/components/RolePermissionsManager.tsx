'use client';

import { useCallback, useEffect, useState } from 'react';
import { Check, Loader2, Save, ShieldCheck, LayoutDashboard, Newspaper, CandlestickChart, FileText } from 'lucide-react';
import { apiFetchJson } from '@/lib/api';

// ─────────────────────────────────────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────────────────────────────────────

type Role = 'general' | 'admin' | 'owner';
type Permissions = Record<string, Role>;

interface Feature {
  id: string;
  label: string;
  description: string;
  icon: React.ComponentType<{ className?: string }>;
}

const FEATURES: Feature[] = [
  { id: 'dashboard',  label: 'Dashboard',           description: 'Main dashboard, charts, and market overview',    icon: LayoutDashboard },
  { id: 'intel',      label: 'Intel',               description: 'News, research, and market intelligence feeds',  icon: Newspaper },
  { id: 'technical',  label: 'Technical Analysis',  description: 'Elliott wave and technical indicator tools',     icon: CandlestickChart },
  { id: 'notes',      label: 'Reports',             description: 'Investment notes and research reports editor',   icon: FileText },
];

const ROLES: { id: Role; label: string; color: string }[] = [
  { id: 'owner',   label: 'Owner',   color: 'text-amber-400  bg-amber-500/10  border-amber-500/30' },
  { id: 'admin',   label: 'Admin',   color: 'text-sky-400    bg-sky-500/10    border-sky-500/30' },
  { id: 'general', label: 'General', color: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30' },
];

// Role hierarchy: index 0 = highest privilege
const ROLE_ORDER: Role[] = ['owner', 'admin', 'general'];

function roleCanAccess(userRole: Role, minRole: Role): boolean {
  return ROLE_ORDER.indexOf(userRole) <= ROLE_ORDER.indexOf(minRole);
}

// ─────────────────────────────────────────────────────────────────────────────
// Component
// ─────────────────────────────────────────────────────────────────────────────

export default function RolePermissionsManager() {
  const [permissions, setPermissions] = useState<Permissions>({});
  const [original, setOriginal] = useState<Permissions>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saveStatus, setSaveStatus] = useState<'idle' | 'saved' | 'error'>('idle');

  useEffect(() => {
    apiFetchJson<Permissions>('/api/admin/settings/role_permissions')
      .then((data) => {
        setPermissions(data);
        setOriginal(data);
      })
      .catch((err) => console.error('Failed to load role permissions:', err))
      .finally(() => setLoading(false));
  }, []);

  const isDirty = JSON.stringify(permissions) !== JSON.stringify(original);

  const setMinRole = useCallback((featureId: string, role: Role) => {
    setPermissions((prev) => ({ ...prev, [featureId]: role }));
    setSaveStatus('idle');
  }, []);

  const handleSave = useCallback(async () => {
    setSaving(true);
    setSaveStatus('idle');
    try {
      const updated = await apiFetchJson<Permissions>('/api/admin/settings/role_permissions', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ permissions }),
      });
      setPermissions(updated);
      setOriginal(updated);
      setSaveStatus('saved');
      setTimeout(() => setSaveStatus('idle'), 2500);
    } catch {
      setSaveStatus('error');
    } finally {
      setSaving(false);
    }
  }, [permissions]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12 text-muted-foreground">
        <Loader2 className="w-4 h-4 animate-spin mr-2" />
        Loading permissions...
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-border/60 bg-background overflow-hidden">
      {/* Header */}
      <div className="px-5 py-4 border-b border-border/60 flex items-center justify-between gap-3">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-foreground/[0.06] border border-border/60 flex items-center justify-center">
            <ShieldCheck className="w-4 h-4 text-foreground" />
          </div>
          <div>
            <div className="text-sm font-semibold text-foreground">Role Permissions</div>
            <div className="text-[11px] text-muted-foreground">Control which roles can access each feature</div>
          </div>
        </div>
        <button
          onClick={handleSave}
          disabled={!isDirty || saving}
          className="h-7 px-3 rounded-lg border text-[12px] font-medium inline-flex items-center gap-1.5 transition-all disabled:opacity-40 disabled:cursor-not-allowed border-emerald-500/35 bg-emerald-500/10 text-emerald-300 hover:bg-emerald-500/18"
        >
          {saving ? (
            <Loader2 className="w-3 h-3 animate-spin" />
          ) : saveStatus === 'saved' ? (
            <Check className="w-3 h-3" />
          ) : (
            <Save className="w-3 h-3" />
          )}
          {saving ? 'Saving...' : saveStatus === 'saved' ? 'Saved' : 'Save'}
        </button>
      </div>

      {/* Legend */}
      <div className="px-5 py-3 border-b border-border/40 flex items-center gap-4 flex-wrap">
        <span className="text-[11px] text-muted-foreground/60 uppercase tracking-wider font-semibold">Access level</span>
        {ROLES.map((r) => (
          <span key={r.id} className={`inline-flex items-center gap-1.5 text-[11px] px-2 py-0.5 rounded-md border font-medium ${r.color}`}>
            {r.label}
          </span>
        ))}
        <span className="text-[11px] text-muted-foreground/50 ml-1">→ owner always has full access</span>
      </div>

      {/* Feature matrix */}
      <div className="divide-y divide-border/40">
        {FEATURES.map((feature) => {
          const minRole = (permissions[feature.id] as Role) || 'general';
          const Icon = feature.icon;
          return (
            <div key={feature.id} className="px-5 py-4 flex items-center gap-4 flex-wrap sm:flex-nowrap">
              {/* Feature info */}
              <div className="flex items-center gap-3 min-w-[220px] flex-1">
                <div className="w-7 h-7 rounded-lg bg-foreground/[0.06] border border-border/60 flex items-center justify-center shrink-0">
                  <Icon className="w-3.5 h-3.5 text-foreground" />
                </div>
                <div>
                  <div className="text-[13px] font-medium text-foreground">{feature.label}</div>
                  <div className="text-[11px] text-muted-foreground/60">{feature.description}</div>
                </div>
              </div>

              {/* Role access pills */}
              <div className="flex items-center gap-2 flex-wrap">
                {ROLES.map((role) => {
                  const hasAccess = roleCanAccess(role.id, minRole);
                  const isOwner = role.id === 'owner';
                  const isCurrent = role.id === minRole;

                  return (
                    <button
                      key={role.id}
                      type="button"
                      disabled={isOwner}
                      onClick={() => !isOwner && setMinRole(feature.id, role.id as Role)}
                      title={
                        isOwner
                          ? 'Owner always has full access'
                          : isCurrent
                          ? `${role.label} is the current minimum role`
                          : `Set minimum access to ${role.label}`
                      }
                      className={`inline-flex items-center gap-1.5 h-7 px-3 rounded-lg border text-[12px] font-medium transition-all
                        ${isOwner ? 'cursor-default opacity-70' : 'cursor-pointer'}
                        ${hasAccess
                          ? `${role.color} opacity-100`
                          : 'text-muted-foreground/40 bg-background border-border/30 opacity-50'
                        }
                        ${isCurrent && !isOwner ? 'ring-1 ring-inset ring-current/30' : ''}
                        ${!isOwner && !hasAccess ? 'hover:opacity-80' : ''}
                        ${!isOwner && hasAccess && !isCurrent ? 'hover:opacity-75' : ''}
                      `}
                    >
                      {hasAccess && <span className="w-1.5 h-1.5 rounded-full bg-current opacity-70" />}
                      {role.label}
                    </button>
                  );
                })}

                {/* Current min-role label */}
                <span className="text-[11px] text-muted-foreground/50 ml-1">
                  {minRole === 'general' && 'visible to all'}
                  {minRole === 'admin' && 'admin + owner only'}
                  {minRole === 'owner' && 'owner only'}
                </span>
              </div>
            </div>
          );
        })}
      </div>

      {saveStatus === 'error' && (
        <div className="px-5 py-3 border-t border-border/40 text-[12px] text-rose-400">
          Failed to save permissions. Please try again.
        </div>
      )}
    </div>
  );
}
