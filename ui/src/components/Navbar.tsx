'use client';

import React, { useRef, useEffect, useState } from 'react';
import Link from 'next/link';
import Image from 'next/image';
import { usePathname } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import {
  LogOut, LogIn,
  Menu, X, ChevronDown,
  Sun, Moon, Users, Search,
} from 'lucide-react';
import TaskNotifications from '@/components/TaskNotifications';
import { useTheme } from '@/context/ThemeContext';
import { AnimatePresence, motion } from 'framer-motion';

function NavLink({ href, children }: { href: string; children: React.ReactNode }) {
  const pathname = usePathname();
  const isActive = href === '/' ? pathname === '/' : pathname.startsWith(href);

  return (
    <Link
      href={href}
      aria-current={isActive ? 'page' : undefined}
      className={`relative px-2.5 py-1.5 text-[11.5px] font-medium tracking-[0.01em] rounded-[var(--radius)] transition-all duration-150 focus:outline-none focus:ring-2 focus:ring-primary/25 focus:ring-offset-1 focus:ring-offset-background ${
        isActive
          ? 'text-primary'
          : 'text-muted-foreground hover:text-foreground'
      }`}
    >
      {children}
      {isActive && (
        <span className="absolute left-1 right-1 -bottom-[9px] h-[2px] rounded-full bg-primary" />
      )}
    </Link>
  );
}

function LiveBadge() {
  const [time, setTime] = useState('');
  const [tz, setTz] = useState('');
  useEffect(() => {
    const fmt = () => new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: false });
    setTime(fmt());
    setTz(Intl.DateTimeFormat().resolvedOptions().timeZone.split('/').pop()?.replace(/_/g, ' ') ?? '');
    const id = setInterval(() => setTime(fmt()), 30000);
    return () => clearInterval(id);
  }, []);

  return (
    <div className="hidden xl:flex items-center gap-2.5 text-[10px]" role="status" aria-label="Live data active">
      <div className="flex items-center gap-1.5">
        <div className="w-1.5 h-1.5 rounded-full bg-success animate-pulse" aria-hidden="true" />
        <span className="text-success font-semibold uppercase tracking-wider">Live</span>
      </div>
      <span className="w-px h-3 bg-border/40" />
      {tz && <span className="text-muted-foreground/50 tracking-wide font-mono text-[9px]">{tz}</span>}
      {time && (
        <span className="text-foreground font-mono text-[10px] tabular-nums">{time}</span>
      )}
    </div>
  );
}

function SearchTrigger({ onClick }: { onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="hidden sm:flex items-center gap-2 h-7 pl-2.5 pr-2 rounded-[var(--radius)] border border-primary/15 bg-primary/[0.06] hover:bg-primary/[0.10] hover:border-primary/25 text-muted-foreground/60 transition-all duration-150 group focus:outline-none focus:ring-2 focus:ring-primary/25 focus:ring-offset-1 focus:ring-offset-background"
      aria-label="Search (Ctrl+K)"
    >
      <Search className="w-3.5 h-3.5" />
      <span className="text-[11px] font-medium">Search</span>
      <kbd className="ml-1 px-1 py-0.5 rounded border border-border/30 text-[8px] font-mono text-muted-foreground/30 group-hover:text-muted-foreground/50 transition-colors">
        Ctrl K
      </kbd>
    </button>
  );
}

function UserMenu() {
  const { user, logout, viewAsUser } = useAuth();
  const isRealAdmin = !!user && (user.role === 'owner' || user.role === 'admin' || user.is_admin);
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handle(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener('mousedown', handle);
    return () => document.removeEventListener('mousedown', handle);
  }, []);

  const initials = [user?.first_name?.[0], user?.last_name?.[0]]
    .filter(Boolean).join('').toUpperCase() || user?.email?.[0]?.toUpperCase() || 'U';

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen(v => !v)}
        aria-label="User menu"
        aria-haspopup="true"
        aria-expanded={open}
        className={`flex items-center gap-1.5 h-8 pl-1 pr-2 rounded-[var(--radius)] transition-colors duration-150 ${
          open ? 'bg-primary/10' : 'hover:bg-primary/[0.06]'
        }`}
      >
        <div className="w-5 h-5 rounded-[calc(var(--radius)-2px)] bg-primary/15 text-primary flex items-center justify-center text-[9px] font-bold shrink-0">
          {initials}
        </div>
        <span className="hidden sm:block text-[11px] font-medium text-foreground leading-none">
          {user?.first_name || 'User'}
        </span>
        <ChevronDown className={`hidden sm:block w-3 h-3 text-muted-foreground/50 transition-transform duration-200 ${open ? 'rotate-180' : ''}`} />
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: 4, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 4, scale: 0.98 }}
            transition={{ duration: 0.1, ease: 'easeOut' }}
            className="absolute right-0 top-full mt-2 w-56 bg-card border border-border/50 rounded-[var(--radius)] shadow-lg shadow-black/20 z-[200] overflow-hidden"
          >
            <div className="px-3 py-2.5 border-b border-border/25">
              <div className="flex items-center gap-2.5">
                <div className="w-7 h-7 rounded-[calc(var(--radius)-2px)] bg-primary/15 text-primary flex items-center justify-center text-[10px] font-bold shrink-0">
                  {initials}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-[12px] font-semibold text-foreground truncate">
                    {user?.first_name} {user?.last_name}
                  </div>
                  <div className="text-[10px] text-muted-foreground/50 truncate">{user?.email}</div>
                </div>
                {isRealAdmin && !viewAsUser && (
                  <span className="text-[8px] font-bold uppercase tracking-wider px-1.5 py-0.5 bg-primary/10 text-primary border border-primary/20 rounded-[calc(var(--radius)-2px)] shrink-0">
                    Admin
                  </span>
                )}
                {isRealAdmin && viewAsUser && (
                  <span className="text-[8px] font-bold uppercase tracking-wider px-1.5 py-0.5 bg-primary/15 text-muted-foreground border border-border/40 rounded-[calc(var(--radius)-2px)] shrink-0">
                    User
                  </span>
                )}
              </div>
            </div>
            <div className="p-1">
              <button
                onClick={() => { setOpen(false); logout(); }}
                className="w-full flex items-center gap-2 px-2.5 py-1.5 rounded-[calc(var(--radius)-2px)] text-[11px] font-medium text-muted-foreground hover:text-destructive hover:bg-destructive/[0.06] transition-all duration-150"
              >
                <LogOut className="w-3.5 h-3.5" />
                Sign out
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
  if (!mounted) return <div className="w-7 h-7" />;

  return (
    <button
      onClick={toggleTheme}
      className="btn-icon"
      title={`Switch to ${theme === 'dark' ? 'Light' : 'Dark'} Mode`}
      aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
    >
      {theme === 'dark' ? <Sun className="w-3.5 h-3.5" /> : <Moon className="w-3.5 h-3.5" />}
    </button>
  );
}

export default function Navbar({ onOpenSearch }: { onOpenSearch?: () => void }) {
  const { user, logout, isAuthenticated, viewAsUser, toggleViewAsUser } = useAuth();
  const { theme } = useTheme();
  const isRealAdmin = !!user && (user.role === 'owner' || user.role === 'admin' || user.is_admin);
  const [menuOpen, setMenuOpen] = React.useState(false);
  const pathname = usePathname();

  React.useEffect(() => { setMenuOpen(false); }, [pathname]);

  React.useEffect(() => {
    if (!menuOpen) return;
    const handleKey = (e: KeyboardEvent) => { if (e.key === 'Escape') setMenuOpen(false); };
    document.addEventListener('keydown', handleKey);
    return () => document.removeEventListener('keydown', handleKey);
  }, [menuOpen]);

  return (
    <nav aria-label="Main navigation" className="fixed top-0 left-0 right-0 z-[100] h-[48px] bg-background/80 backdrop-blur-xl border-b border-border/20">
      <div className="max-w-[1440px] mx-auto px-4 sm:px-5 h-full flex items-center gap-3 sm:gap-4">

        {/* Logo */}
        <Link href="/" className="shrink-0 mr-1 sm:mr-4">
          <Image
            src={theme === 'dark' ? '/investment-x-logo-light.svg' : '/investment-x-logo-dark.svg'}
            alt="Investment-X"
            width={160}
            height={16}
            className="h-[13px] w-auto"
            priority
            unoptimized
          />
        </Link>

        {/* Desktop nav links */}
        <div className="hidden md:flex items-center gap-0.5 shrink-0">
          <NavLink href="/">Dashboard</NavLink>
          <NavLink href="/chartpack">ChartPack</NavLink>
          <NavLink href="/intel">Intel</NavLink>
          <NavLink href="/macro">Macro</NavLink>
          <NavLink href="/whiteboard">Whiteboard</NavLink>
          {isRealAdmin && !viewAsUser && (
            <NavLink href="/admin/timeseries">System</NavLink>
          )}
        </div>

        {/* Center: search trigger */}
        <div className="hidden lg:flex flex-1 justify-center min-w-0 overflow-hidden">
          {onOpenSearch && <SearchTrigger onClick={onOpenSearch} />}
        </div>

        {/* Right side: live + actions */}
        <div className="flex items-center gap-1.5 ml-auto shrink-0">
          <LiveBadge />

          <div className="hidden xl:block w-px h-3.5 bg-border/25 mx-1" />

          <ThemeToggle />
          {isRealAdmin && (
            <button
              onClick={toggleViewAsUser}
              className={`btn-icon ${
                viewAsUser
                  ? 'text-primary bg-primary/10'
                  : ''
              }`}
              title={viewAsUser ? 'Exit user view' : 'View as user'}
              aria-label={viewAsUser ? 'Exit user view' : 'View as user'}
              aria-pressed={viewAsUser}
            >
              <Users className="w-3.5 h-3.5" />
            </button>
          )}
          {isAuthenticated && <TaskNotifications />}

          <div className="w-px h-3.5 bg-border/25 mx-1 hidden sm:block" />

          {isAuthenticated ? (
            <UserMenu />
          ) : (
            <Link
              href="/login"
              className="h-8 px-3.5 bg-primary text-primary-foreground rounded-[var(--radius)] text-[11px] font-semibold inline-flex items-center hover:opacity-90 transition-opacity duration-150"
            >
              Sign in
            </Link>
          )}

          {/* Mobile menu button */}
          <button
            className="md:hidden btn-icon ml-1"
            onClick={() => setMenuOpen(!menuOpen)}
            aria-label="Menu"
            aria-expanded={menuOpen}
          >
            {menuOpen ? <X className="w-4 h-4" /> : <Menu className="w-4 h-4" />}
          </button>
        </div>
      </div>

      {/* Mobile menu */}
      <AnimatePresence>
        {menuOpen && (
          <motion.div
            initial={{ opacity: 0, y: -6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -6 }}
            transition={{ duration: 0.12 }}
            role="navigation"
            aria-label="Mobile navigation"
            className="md:hidden absolute top-[48px] left-0 right-0 bg-card border-b border-border/25 px-4 py-3 flex flex-col gap-0.5 shadow-lg z-[90]"
          >
            <MobileNavLink href="/">Dashboard</MobileNavLink>
            <MobileNavLink href="/chartpack">ChartPack</MobileNavLink>
            <MobileNavLink href="/intel">Intel</MobileNavLink>
            <MobileNavLink href="/macro">Macro</MobileNavLink>
            <MobileNavLink href="/whiteboard">Whiteboard</MobileNavLink>
            {isRealAdmin && !viewAsUser && (
              <MobileNavLink href="/admin/timeseries">System</MobileNavLink>
            )}
            <div className="mt-2 pt-2 border-t border-border/20">
              {isAuthenticated ? (
                <button
                  onClick={logout}
                  className="flex items-center gap-2 px-3 py-2 rounded-[var(--radius)] text-[11.5px] font-medium text-muted-foreground hover:text-destructive hover:bg-destructive/[0.06] transition-all w-full"
                >
                  <LogOut className="w-4 h-4" />
                  Sign out
                </button>
              ) : (
                <Link
                  href="/login"
                  className="flex items-center justify-center gap-2 w-full py-2.5 bg-primary text-primary-foreground rounded-[var(--radius)] text-[11.5px] font-semibold"
                >
                  <LogIn className="w-4 h-4" />
                  Sign in
                </Link>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </nav>
  );
}

function MobileNavLink({ href, children }: { href: string; children: React.ReactNode }) {
  const pathname = usePathname();
  const isActive = href === '/' ? pathname === '/' : pathname.startsWith(href);

  return (
    <Link
      href={href}
      className={`px-3 py-2 rounded-[var(--radius)] text-[11.5px] font-medium transition-all duration-150 ${
        isActive
          ? 'text-primary bg-primary/[0.08]'
          : 'text-muted-foreground hover:text-foreground hover:bg-primary/[0.06]'
      }`}
    >
      {children}
    </Link>
  );
}
