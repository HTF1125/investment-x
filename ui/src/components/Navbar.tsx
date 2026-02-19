'use client';

import React, { useRef, useEffect, useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { 
  User as UserIcon, LogOut, LogIn, Database, Radio, 
  Menu, X, Layout, Cpu, Hexagon, Bell, ChevronDown,
  Settings, Shield
} from 'lucide-react';
import TaskNotifications from '@/components/TaskNotifications';
import { AnimatePresence, motion } from 'framer-motion';

interface NavLinkProps {
  href: string;
  children: React.ReactNode;
  onClick?: () => void;
  className?: string;
  icon?: React.ReactNode;
}

/**
 * Terminal-style NavLink with hover glow and monospace font.
 */
function NavLink({ href, children, onClick, className = '', icon }: NavLinkProps) {
  const pathname = usePathname();
  const isActive = href === '/' ? pathname === '/' : pathname.startsWith(href);

  return (
    <Link
      href={href}
      onClick={onClick}
      className={`
        px-3 py-1.5 rounded-lg text-xs font-mono font-bold transition-all flex items-center gap-2 group relative
        ${isActive
          ? 'text-white bg-white/10 shadow-[0_0_15px_rgba(255,255,255,0.05)] border border-white/10'
          : 'text-slate-500 hover:text-slate-200 hover:bg-white/5 border border-transparent'
        }
        ${className}
      `}
    >
      {icon && <span className={`${isActive ? 'text-indigo-400' : 'text-slate-600 group-hover:text-slate-400'} transition-colors`}>{icon}</span>}
      {children}
      {isActive && (
        <motion.span 
            layoutId="nav-glow"
            className="absolute -bottom-1 left-3 right-3 h-[1px] bg-gradient-to-r from-transparent via-indigo-500 to-transparent opacity-50"
        />
      )}
    </Link>
  );
}

/**
 * Live status indicators — pipeline, region, time.
 */
function StatusIndicators() {
  const [mounted, setMounted] = useState(false);
  useEffect(() => { setMounted(true); }, []);

  return (
    <div className="hidden xl:flex items-center gap-3 text-[10px] font-mono">
      <div className="flex items-center gap-1.5">
        <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse shadow-[0_0_6px_rgba(16,185,129,0.5)]" />
        <span className="text-emerald-500/80 uppercase">Live</span>
      </div>
      <div className="w-px h-3 bg-white/10" />
      <span className="text-slate-500 uppercase">Seoul</span>
      {mounted && (
        <>
          <div className="w-px h-3 bg-white/10" />
          <span className="text-slate-400 tabular-nums font-semibold">
            {new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: false })}
          </span>
        </>
      )}
    </div>
  );
}

/**
 * User profile dropdown with notifications, settings, and logout.
 */
function UserDropdown() {
  const { user, logout } = useAuth();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  // Close on click outside
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const initials = [user?.first_name?.[0], user?.last_name?.[0]]
    .filter(Boolean)
    .join('')
    .toUpperCase() || user?.email?.[0]?.toUpperCase() || 'U';

  return (
    <div className="relative" ref={ref}>
      {/* Trigger button */}
      <button
        onClick={() => setOpen((v) => !v)}
        className={`
          flex items-center gap-2 px-1.5 py-1 rounded-xl border transition-all
          ${open
            ? 'bg-white/10 border-white/15 shadow-lg shadow-indigo-500/10'
            : 'bg-white/5 border-white/10 hover:bg-white/10 hover:border-white/15'
          }
        `}
      >
        {/* Avatar */}
        <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-indigo-500 to-sky-500 flex items-center justify-center text-white text-[10px] font-bold shadow-inner">
          {initials}
        </div>
        <div className="hidden sm:flex flex-col items-start leading-none pr-1">
          <span className="text-[11px] font-bold text-slate-200">{user?.first_name || 'Operator'}</span>
          <span className="text-[9px] font-mono text-slate-500 uppercase tracking-tighter">{user?.email?.split('@')[0]}</span>
        </div>
        <ChevronDown className={`w-3 h-3 text-slate-500 transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>

      {/* Dropdown */}
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: 8, scale: 0.96 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 8, scale: 0.96 }}
            transition={{ duration: 0.15, ease: 'easeOut' }}
            className="absolute right-0 top-full mt-2 w-80 bg-[#0a0f1e]/95 backdrop-blur-2xl border border-white/10 rounded-2xl shadow-2xl shadow-black/50 z-[200] overflow-hidden"
          >
            {/* User header */}
            <div className="p-4 border-b border-white/[0.06] bg-gradient-to-r from-indigo-500/5 to-sky-500/5">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 to-sky-500 flex items-center justify-center text-white text-sm font-bold shadow-lg shadow-indigo-500/20">
                  {initials}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-bold text-white truncate">
                    {user?.first_name || 'Operator'} {user?.last_name || ''}
                  </div>
                  <div className="text-[11px] text-slate-500 font-mono truncate">{user?.email}</div>
                </div>
                {user?.is_admin && (
                  <span className="px-2 py-0.5 text-[9px] font-bold uppercase tracking-wider bg-amber-500/10 text-amber-400 border border-amber-500/20 rounded-md flex items-center gap-1">
                    <Shield className="w-2.5 h-2.5" /> Admin
                  </span>
                )}
              </div>
            </div>

            {/* Notifications section */}
            <div className="border-b border-white/[0.06]">
              <div className="px-4 pt-3 pb-1.5 flex items-center gap-2">
                <Bell className="w-3.5 h-3.5 text-slate-500" />
                <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider">Notifications</span>
              </div>
              <div className="px-2 pb-2">
                <TaskNotifications embedded />
              </div>
            </div>

            {/* Actions */}
            <div className="p-2">
              <button
                onClick={() => { setOpen(false); logout(); }}
                className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 transition-all group"
              >
                <LogOut className="w-4 h-4 group-hover:text-rose-400 transition-colors" />
                <span className="text-xs font-mono font-bold uppercase tracking-wider">Terminate Session</span>
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export default function Navbar() {
  const { user, logout, isAuthenticated } = useAuth();
  const [menuOpen, setMenuOpen] = React.useState(false);
  const pathname = usePathname();

  React.useEffect(() => {
    setMenuOpen(false);
  }, [pathname]);

  return (
    <nav className="fixed top-0 left-0 right-0 z-[100] h-12 bg-[#05070c]/80 backdrop-blur-2xl border-b border-white/[0.05]">
      <div className="max-w-[1920px] mx-auto px-4 h-full flex items-center justify-between gap-4">
        
        {/* LEFT: Logo + Nav Links */}
        <div className="flex items-center gap-4 shrink-0">
            <Link href="/" className="flex items-center gap-2 group">
                <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-indigo-600 to-sky-600 flex items-center justify-center shadow-lg shadow-indigo-500/20 group-hover:scale-105 transition-transform">
                    <Hexagon className="w-3.5 h-3.5 text-white fill-white/20" />
                </div>
                <div className="hidden sm:flex flex-col leading-none">
                    <span className="text-xs font-black text-white tracking-tighter uppercase">Investment<span className="text-indigo-400">X</span></span>
                    <span className="text-[8px] font-mono text-slate-500 uppercase tracking-[0.2em]">Core.Nexus</span>
                </div>
            </Link>

            {/* Desktop Navigation */}
            <div className="hidden lg:flex items-center gap-1 p-0.5 bg-black/20 rounded-lg border border-white/5">
                <NavLink href="/" icon={<Layout className="w-3 h-3" />}>Dashboard</NavLink>
                <NavLink href="/intel" icon={<Radio className="w-3 h-3" />}>Intel</NavLink>
                {user?.is_admin && (
                  <NavLink href="/admin/timeseries" icon={<Database className="w-3 h-3" />}>System</NavLink>
                )}
            </div>
        </div>

        {/* CENTER: Status */}
        <div className="hidden lg:flex items-center gap-4 flex-1 justify-center">
          <StatusIndicators />
        </div>

        {/* RIGHT: User / Login + Mobile Menu */}
        <div className="flex items-center gap-3 shrink-0">
          {isAuthenticated ? (
            <UserDropdown />
          ) : (
            <Link 
              href="/login"
              className="px-4 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-bold transition-all shadow-lg shadow-indigo-600/20 uppercase tracking-wider"
            >
              Initialize Session
            </Link>
          )}

          {/* Mobile Menu Button */}
          <button 
              className="lg:hidden p-2 text-slate-400 hover:text-white transition-colors"
              onClick={() => setMenuOpen(!menuOpen)}
          >
              {menuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>
      </div>

      {/* Mobile Menu Overlay */}
      <AnimatePresence>
        {menuOpen && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="lg:hidden absolute top-12 left-0 right-0 bg-[#05070c] border-b border-white/10 p-6 flex flex-col gap-4 shadow-2xl z-[90]"
          >
               <div className="flex flex-col gap-2">
                  <MobileNavLink href="/" icon={<Layout className="w-4 h-4" />}>Dashboard</MobileNavLink>
                  <MobileNavLink href="/intel" icon={<Radio className="w-4 h-4" />}>Intel Feed</MobileNavLink>
                  {user?.is_admin && (
                    <MobileNavLink href="/admin/timeseries" icon={<Database className="w-4 h-4" />}>System Admin</MobileNavLink>
                  )}
               </div>

               <div className="flex flex-col gap-4 pt-4 border-t border-white/5">
                  {isAuthenticated ? (
                    <button 
                        onClick={logout}
                        className="flex items-center justify-center gap-2 w-full py-3 text-rose-400 bg-rose-500/10 rounded-xl border border-rose-500/20 font-mono text-xs font-bold uppercase"
                    >
                        <LogOut className="w-4 h-4" /> Terminate Session
                    </button>
                  ) : (
                      <Link 
                        href="/login"
                        className="flex items-center justify-center gap-2 w-full py-3 bg-indigo-600 text-white rounded-xl font-bold text-xs uppercase"
                      >
                        <LogIn className="w-4 h-4" /> Login
                      </Link>
                  )}
               </div>
          </motion.div>
        )}
      </AnimatePresence>
    </nav>
  );
}

function MobileNavLink({ href, children, icon }: { href: string; children: React.ReactNode; icon: React.ReactNode }) {
  const pathname = usePathname();
  const isActive = href === '/' ? pathname === '/' : pathname.startsWith(href);

  return (
    <Link
      href={href}
      className={`
        flex items-center gap-3 px-4 py-3 rounded-xl font-mono text-sm transition-all
        ${isActive
          ? 'bg-indigo-500/10 text-white border border-indigo-500/20'
          : 'text-slate-400 hover:text-slate-200'
        }
      `}
    >
      <span className={isActive ? 'text-indigo-400' : 'text-slate-600'}>{icon}</span>
      {children}
    </Link>
  );
}
