'use client';

import React, { useRef, useEffect, useState } from 'react';
import Link from 'next/link';
import Image from 'next/image';
import { usePathname } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import {
  LogOut, LogIn, Database, Radio,
  Menu, X, Layout, ChevronDown,
  Shield, Sun, Moon, CandlestickChart, FileText, Users
} from 'lucide-react';
import TaskNotifications from '@/components/TaskNotifications';
import { useTheme } from '@/context/ThemeContext';
import { CHART_STYLE_LABELS, type ChartStyle } from '@/lib/chartTheme';
import { AnimatePresence, motion } from 'framer-motion';

function NavLink({ href, children }: { href: string; children: React.ReactNode }) {
  const pathname = usePathname();
  const isActive = href === '/' ? pathname === '/' : pathname.startsWith(href);

  return (
    <Link
      href={href}
      className={`relative px-2 py-1 rounded-md text-[11px] font-medium transition-all duration-200 after:absolute after:left-2 after:right-2 after:-bottom-[2px] after:h-[1.5px] after:rounded-full after:transition-all after:duration-200 ${
        isActive
          ? 'text-foreground bg-foreground/[0.07] after:bg-sky-400/90'
          : 'text-muted-foreground after:bg-transparent hover:text-foreground hover:bg-foreground/[0.04] hover:after:bg-foreground/30'
      }`}
    >
      {children}
    </Link>
  );
}

function LiveBadge() {
  const [time, setTime] = useState('');
  useEffect(() => {
    const fmt = () => new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: false });
    setTime(fmt());
    const id = setInterval(() => setTime(fmt()), 30000);
    return () => clearInterval(id);
  }, []);

  return (
    <div className="hidden xl:flex items-center gap-2.5 text-[12px] text-muted-foreground">
      <div className="flex items-center gap-1.5">
        <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
        <span className="text-emerald-600 dark:text-emerald-400 font-medium">Live</span>
      </div>
      <span className="text-border/80">·</span>
      <span>Seoul</span>
      {time && (
        <>
          <span className="text-border/80">·</span>
          <span className="text-foreground tabular-nums">{time}</span>
        </>
      )}
    </div>
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
        className={`flex items-center gap-1.5 h-7 pl-1 pr-2 rounded-lg transition-colors ${
          open ? 'bg-foreground/[0.07]' : 'hover:bg-foreground/[0.05]'
        }`}
      >
        <div className="w-5 h-5 rounded-md bg-foreground text-background flex items-center justify-center text-[9px] font-bold shrink-0">
          {initials}
        </div>
        <span className="hidden sm:block text-[12px] font-medium text-foreground leading-none">
          {user?.first_name || 'User'}
        </span>
        <ChevronDown className={`hidden sm:block w-3 h-3 text-muted-foreground transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: 6, scale: 0.97 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 6, scale: 0.97 }}
            transition={{ duration: 0.12, ease: 'easeOut' }}
            className="absolute right-0 top-full mt-1.5 w-60 bg-background border border-border rounded-xl shadow-xl z-[200] overflow-hidden"
          >
            <div className="px-3.5 py-3 border-b border-border/60">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-lg bg-foreground text-background flex items-center justify-center text-xs font-bold shrink-0">
                  {initials}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-[13px] font-semibold text-foreground truncate">
                    {user?.first_name} {user?.last_name}
                  </div>
                  <div className="text-[11px] text-muted-foreground truncate">{user?.email}</div>
                </div>
                {isRealAdmin && !viewAsUser && (
                  <span className="text-[9px] font-bold uppercase tracking-wide px-1.5 py-0.5 bg-amber-500/10 text-amber-500 border border-amber-500/20 rounded shrink-0">
                    Admin
                  </span>
                )}
                {isRealAdmin && viewAsUser && (
                  <span className="text-[9px] font-bold uppercase tracking-wide px-1.5 py-0.5 bg-sky-500/10 text-sky-500 border border-sky-500/20 rounded shrink-0">
                    User
                  </span>
                )}
              </div>
            </div>
            <div className="p-1.5">
              <button
                onClick={() => { setOpen(false); logout(); }}
                className="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-[13px] text-muted-foreground hover:text-rose-500 hover:bg-rose-500/[0.07] transition-all"
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
      className="flex items-center justify-center w-7 h-7 rounded-md text-muted-foreground hover:text-foreground hover:bg-foreground/[0.06] transition-all"
      title={`Switch to ${theme === 'dark' ? 'Light' : 'Dark'} Mode`}
    >
      {theme === 'dark' ? <Sun className="w-3.5 h-3.5" /> : <Moon className="w-3.5 h-3.5" />}
    </button>
  );
}

export default function Navbar() {
  const { user, logout, isAuthenticated, viewAsUser, toggleViewAsUser } = useAuth();
  const { theme } = useTheme();
  const isRealAdmin = !!user && (user.role === 'owner' || user.role === 'admin' || user.is_admin);
  const [menuOpen, setMenuOpen] = React.useState(false);
  const pathname = usePathname();

  React.useEffect(() => { setMenuOpen(false); }, [pathname]);

  return (
    <nav className="fixed top-0 left-0 right-0 z-[100] h-[40px] bg-background border-b border-border/60">
      <div className="max-w-[1920px] mx-auto px-3 sm:px-4 h-full flex items-center gap-1.5 sm:gap-3">

        {/* Logo */}
        <Link href="/" className="shrink-0 mr-1 sm:mr-2">
          <Image
            src={theme === 'dark' ? '/investment-x-logo-light.svg' : '/investment-x-logo-dark.svg'}
            alt="Investment-X"
            width={160}
            height={16}
            className="h-[12px] w-auto"
            priority
            unoptimized
          />
        </Link>

        {/* Separator */}
        <div className="hidden md:block w-px h-3.5 bg-border/70 shrink-0" />

        {/* Desktop nav links */}
        <div className="hidden md:flex items-center gap-2 flex-1 min-w-0 max-w-max">
          <NavLink href="/">Dashboard</NavLink>
          <NavLink href="/wartime">Wartime</NavLink>
          <NavLink href="/intel">Intel</NavLink>
          <NavLink href="/technical">Technical</NavLink>
          <NavLink href="/notes">Reports</NavLink>
          {isRealAdmin && !viewAsUser && (
            <NavLink href="/admin/timeseries">System</NavLink>
          )}
        </div>

        {/* Center: live status */}
        <div className="hidden xl:flex items-center flex-1 justify-center">
          <LiveBadge />
        </div>

        {/* Right actions */}
        <div className="flex items-center gap-0.5 ml-auto shrink-0">
          <ThemeToggle />
          {isRealAdmin && (
            <button
              onClick={toggleViewAsUser}
              className={`flex items-center justify-center w-7 h-7 rounded-md transition-all ${
                viewAsUser
                  ? 'text-sky-500 bg-sky-500/10'
                  : 'text-muted-foreground hover:text-foreground hover:bg-foreground/[0.06]'
              }`}
              title={viewAsUser ? 'Exit user view' : 'View as user'}
            >
              <Users className="w-3.5 h-3.5" />
            </button>
          )}
          {isAuthenticated && <TaskNotifications />}

          <div className="w-px h-4 bg-border/60 mx-1.5 hidden sm:block" />

          {isAuthenticated ? (
            <UserMenu />
          ) : (
            <Link
              href="/login"
              className="h-7 px-3 bg-foreground text-background rounded-md text-[12px] font-medium inline-flex items-center hover:opacity-80 transition-opacity"
            >
              Sign in
            </Link>
          )}

          {/* Mobile menu button */}
          <button
            className="md:hidden flex items-center justify-center w-7 h-7 rounded-md text-muted-foreground hover:text-foreground hover:bg-foreground/[0.06] transition-all ml-1"
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
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.15 }}
            className="md:hidden absolute top-[40px] left-0 right-0 bg-background border-b border-border px-3 py-3 flex flex-col gap-0.5 shadow-lg z-[90]"
          >
            <MobileNavLink href="/">Dashboard</MobileNavLink>
            <MobileNavLink href="/wartime">Wartime</MobileNavLink>
            <MobileNavLink href="/intel">Intel</MobileNavLink>
            <MobileNavLink href="/technical">Technical</MobileNavLink>
            <MobileNavLink href="/notes">Reports</MobileNavLink>
            {isRealAdmin && !viewAsUser && (
              <MobileNavLink href="/admin/timeseries">System</MobileNavLink>
            )}
            <div className="mt-2 pt-2 border-t border-border/60">
              {isAuthenticated ? (
                <button
                  onClick={logout}
                  className="flex items-center gap-2 px-3 py-2 rounded-lg text-[13px] text-muted-foreground hover:text-rose-500 hover:bg-rose-500/[0.07] transition-all w-full"
                >
                  <LogOut className="w-4 h-4" />
                  Sign out
                </button>
              ) : (
                <Link
                  href="/login"
                  className="flex items-center justify-center gap-2 w-full py-2.5 bg-foreground text-background rounded-lg text-[13px] font-medium"
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
      className={`px-3 py-2 rounded-lg text-[13px] font-medium transition-all ${
        isActive
          ? 'text-foreground bg-foreground/[0.06]'
          : 'text-muted-foreground hover:text-foreground hover:bg-foreground/[0.04]'
      }`}
    >
      {children}
    </Link>
  );
}
