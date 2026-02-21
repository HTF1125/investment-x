'use client';

import React, { useRef, useEffect, useState } from 'react';
import Link from 'next/link';
import Image from 'next/image';
import { usePathname } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { 
  User as UserIcon, LogOut, LogIn, Database, Radio, 
  Menu, X, Layout, Cpu, Hexagon, Bell, ChevronDown,
  Settings, Shield, Sun, Moon, CandlestickChart
} from 'lucide-react';
import TaskNotifications from '@/components/TaskNotifications';
import { useTheme } from '@/context/ThemeContext';
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
          ? 'text-foreground'
          : 'text-muted-foreground hover:text-foreground hover:bg-accent/10 border border-transparent'
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
      <div className="w-px h-3 bg-border" />
      <span className="text-muted-foreground uppercase">Seoul</span>
      {mounted && (
        <>
          <div className="w-px h-3 bg-border" />
          <span className="text-foreground tabular-nums font-semibold">
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
          flex items-center gap-1 sm:gap-2 px-1 sm:px-1.5 py-1 rounded-lg border transition-all h-8
          ${open
            ? 'bg-accent/10 text-black border-black/30 dark:text-white dark:border-white/30'
            : 'bg-secondary/20 text-black border-black/20 hover:bg-accent/10 dark:text-white dark:border-white/20'
          }
        `}
      >
        {/* Avatar */}
        <div className="w-6 h-6 rounded-md bg-black text-white dark:bg-white dark:text-black flex items-center justify-center text-[10px] font-bold">
          {initials}
        </div>
        <div className="hidden sm:flex flex-col items-start leading-none pr-1">
          <span className="text-[11px] font-bold text-current">{user?.first_name || 'Operator'}</span>
          <span className="text-[9px] font-mono text-black/60 dark:text-white/60 uppercase tracking-tighter">{user?.email?.split('@')[0]}</span>
        </div>
        <ChevronDown className={`hidden sm:block w-3 h-3 text-current/70 transition-transform ${open ? 'rotate-180 text-current' : ''}`} />
      </button>

      {/* Dropdown */}
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: 8, scale: 0.96 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 8, scale: 0.96 }}
            transition={{ duration: 0.15, ease: 'easeOut' }}
            className="absolute right-0 top-full mt-2 w-80 !bg-white dark:!bg-slate-950 border border-border rounded-2xl shadow-2xl z-[200] overflow-hidden !opacity-100"
            style={{ backgroundColor: 'rgb(var(--background))' }}
          >
            {/* User header */}
            <div className="p-4 border-b border-border/50 bg-gradient-to-r from-primary/5 to-secondary/5">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 to-sky-500 flex items-center justify-center text-white text-sm font-bold shadow-lg shadow-indigo-500/20">
                  {initials}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-bold text-foreground truncate">
                    {user?.first_name || 'Operator'} {user?.last_name || ''}
                  </div>
                  <div className="text-[11px] text-muted-foreground font-mono truncate">{user?.email}</div>
                </div>
                {user?.is_admin && (
                  <span className="px-2 py-0.5 text-[9px] font-bold uppercase tracking-wider bg-amber-500/10 text-amber-400 border border-amber-500/20 rounded-md flex items-center gap-1">
                    <Shield className="w-2.5 h-2.5" /> Admin
                  </span>
                )}
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

function ThemeToggle() {
  const { theme, toggleTheme } = useTheme();
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);
  
  if (!mounted) return <div className="w-8 h-8" />; // Placeholder to avoid hydration mismatch

  return (
    <button
      onClick={toggleTheme}
      className="flex items-center justify-center w-8 h-8 rounded-lg border border-border/50 bg-secondary/20 hover:bg-accent/10 hover:border-border transition-all text-muted-foreground hover:text-foreground shadow-sm"
      title={`Switch to ${theme === 'dark' ? 'Light' : 'Dark'} Mode`}
    >
      {theme === 'dark' ? (
        <Sun className="w-4 h-4" />
      ) : (
        <Moon className="w-4 h-4" />
      )}
    </button>
  );
}

export default function Navbar() {
  const { user, logout, isAuthenticated } = useAuth();
  const { theme } = useTheme();
  const [menuOpen, setMenuOpen] = React.useState(false);
  const pathname = usePathname();

  React.useEffect(() => {
    setMenuOpen(false);
  }, [pathname]);

  return (
    <nav className="fixed top-0 left-0 right-0 z-[100] h-12 bg-white dark:bg-black border-b border-border/50">
      <div className="max-w-[1920px] mx-auto px-2 sm:px-4 h-full flex items-center justify-between gap-2 sm:gap-4 min-w-0">
        
        {/* LEFT: Logo + Nav Links */}
        <div className="flex items-center gap-2 sm:gap-4 shrink min-w-0">
            <Link href="/" className="flex items-center group py-1 min-w-0">
                <Image 
                    src={theme === 'dark' ? '/investment-x-logo-light.svg' : '/investment-x-logo-dark.svg'}
                    alt="Investment-X Logo"
                    width={220}
                    height={22}
                    className="h-4 sm:h-5 w-auto max-w-[140px] sm:max-w-[220px] transition-opacity"
                    priority
                    unoptimized
                />
            </Link>

            {/* Desktop Navigation */}
            <div className="hidden md:flex items-center gap-1 p-0.5 rounded-lg">
                <NavLink href="/" icon={<Layout className="w-3 h-3" />}>Dashboard</NavLink>
                <NavLink href="/intel" icon={<Radio className="w-3 h-3" />}>Intel</NavLink>
                <NavLink href="/technical" icon={<CandlestickChart className="w-3 h-3" />}>Technical</NavLink>
                {user?.is_admin && (
                  <NavLink href="/admin/timeseries" icon={<Database className="w-3 h-3" />}>System</NavLink>
                )}
            </div>
        </div>

        {/* CENTER: Status */}
        <div className="hidden md:flex items-center gap-4 flex-1 justify-center">
          <StatusIndicators />
        </div>

        {/* RIGHT: User / Login + Mobile Menu */}
        <div className="flex items-center gap-1.5 sm:gap-3 shrink-0">
          <ThemeToggle />
          {isAuthenticated && <TaskNotifications />}
          
          {isAuthenticated ? (
            <UserDropdown />
          ) : (
            <Link 
              href="/login"
              className="inline-flex items-center px-4 h-8 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-bold transition-all shadow-lg shadow-indigo-600/20 uppercase tracking-wider"
            >
              Initialize Session
            </Link>
          )}

          {/* Mobile Menu Button */}
          <button 
              className="md:hidden flex items-center justify-center w-8 h-8 rounded-lg border border-border/50 bg-secondary/20 hover:bg-accent/10 hover:border-border transition-all text-muted-foreground hover:text-foreground shadow-sm"
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
            className="md:hidden absolute top-12 left-0 right-0 !bg-white dark:!bg-black border-b border-border p-6 flex flex-col gap-4 shadow-3xl z-[90] !opacity-100"
            style={{ backgroundColor: 'rgb(var(--background))' }}
          >
               <div className="flex flex-col gap-2">
                  <MobileNavLink href="/" icon={<Layout className="w-4 h-4" />}>Dashboard</MobileNavLink>
                  <MobileNavLink href="/intel" icon={<Radio className="w-4 h-4" />}>Intel Feed</MobileNavLink>
                  <MobileNavLink href="/technical" icon={<CandlestickChart className="w-4 h-4" />}>Technical</MobileNavLink>
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
          ? 'bg-primary/10 text-foreground border border-primary/20'
          : 'text-muted-foreground hover:text-foreground'
        }
      `}
    >
      <span className={isActive ? 'text-indigo-400' : 'text-slate-600'}>{icon}</span>
      {children}
    </Link>
  );
}
