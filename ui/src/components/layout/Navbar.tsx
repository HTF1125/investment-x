'use client';

import React, { useRef, useEffect, useState, useCallback } from 'react';
import Link from 'next/link';
import Image from 'next/image';
import { usePathname } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import {
  LogOut, LogIn,
  Menu, X, ChevronDown,
  Sun, Moon, Search, Settings,
} from 'lucide-react';

import { useTheme } from '@/context/ThemeContext';
import { AnimatePresence, motion } from 'framer-motion';

/* ── Nav items ─────────────────────────────────────────────────────────── */

interface NavItem {
  href: string;
  label: string;
  adminOnly?: boolean;
}

const NAV_ITEMS: NavItem[] = [
  { href: '/', label: 'Dashboard' },
  { href: '/chartpack', label: 'ChartPack' },
  { href: '/research', label: 'Research' },
  { href: '/macro', label: 'Macro' },
  { href: '/whiteboard', label: 'Whiteboard' },
  { href: '/admin', label: 'System', adminOnly: true },
];

/* ── NavLink ───────────────────────────────────────────────────────────── */

function NavLink({ href, children }: { href: string; children: React.ReactNode }) {
  const pathname = usePathname();
  const isActive = href === '/' ? pathname === '/' : pathname.startsWith(href);

  return (
    <Link
      href={href}
      aria-current={isActive ? 'page' : undefined}
      className={`relative px-2.5 py-1 text-[11px] font-mono font-bold tracking-[0.14em] uppercase whitespace-nowrap transition-colors duration-150 focus:outline-none focus-visible:ring-2 focus-visible:ring-accent/40 ${
        isActive
          ? 'text-foreground'
          : 'text-muted-foreground hover:text-foreground'
      }`}
    >
      {children}
      {isActive && (
        <span className="absolute left-2.5 right-2.5 -bottom-[7px] h-[2px] bg-accent" />
      )}
    </Link>
  );
}

/* ── OverflowNav — measures available space, shows "More" for overflow ── */

function OverflowNav({ links }: { links: NavItem[] }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const measureRef = useRef<HTMLDivElement>(null);
  const [visibleCount, setVisibleCount] = useState(links.length);
  const [moreOpen, setMoreOpen] = useState(false);
  const moreRef = useRef<HTMLDivElement>(null);
  const pathname = usePathname();

  // Close on navigation
  useEffect(() => { setMoreOpen(false); }, [pathname]);

  // Close on outside click
  useEffect(() => {
    const handle = (e: MouseEvent) => {
      if (moreRef.current && !moreRef.current.contains(e.target as Node)) setMoreOpen(false);
    };
    document.addEventListener('mousedown', handle);
    return () => document.removeEventListener('mousedown', handle);
  }, []);

  // Close on Escape
  useEffect(() => {
    if (!moreOpen) return;
    const handle = (e: KeyboardEvent) => { if (e.key === 'Escape') setMoreOpen(false); };
    document.addEventListener('keydown', handle);
    return () => document.removeEventListener('keydown', handle);
  }, [moreOpen]);

  // Measure which links fit
  const updateVisibleCount = useCallback(() => {
    const container = containerRef.current;
    const measure = measureRef.current;
    if (!container || !measure) return;

    const available = container.clientWidth;
    const items = Array.from(measure.querySelectorAll('[data-nav-measure]')) as HTMLElement[];
    if (items.length === 0) return;

    const moreButtonWidth = 64;
    const widths = items.map(el => el.offsetWidth);
    const allTotal = widths.reduce((s, w) => s + w, 0);

    // All items fit — no "More" needed
    if (allTotal <= available) {
      setVisibleCount(items.length);
      return;
    }

    // Find how many fit alongside the "More" button
    let total = 0;
    let count = 0;
    for (let i = 0; i < widths.length; i++) {
      if (total + widths[i] + moreButtonWidth > available) break;
      total += widths[i];
      count++;
    }
    setVisibleCount(Math.max(1, count));
  }, []);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    const ro = new ResizeObserver(updateVisibleCount);
    ro.observe(container);
    return () => ro.disconnect();
  }, [updateVisibleCount]);

  // Re-measure when links change (e.g. admin login)
  useEffect(() => { updateVisibleCount(); }, [links.length, updateVisibleCount]);

  const visibleLinks = links.slice(0, visibleCount);
  const overflowLinks = links.slice(visibleCount);
  const hasOverflow = overflowLinks.length > 0;

  const overflowHasActive = overflowLinks.some(link =>
    link.href === '/' ? pathname === '/' : pathname.startsWith(link.href)
  );

  return (
    <div ref={containerRef} className="hidden md:flex items-center flex-1 min-w-0 relative">
      {/* Hidden measurement row — same font/padding as NavLink, renders all items to get natural widths */}
      <div
        ref={measureRef}
        aria-hidden="true"
        className="absolute top-0 left-0 flex items-center pointer-events-none"
        style={{ visibility: 'hidden', zIndex: -1 }}
      >
        {links.map(link => (
          <span
            key={link.href}
            data-nav-measure
            className="px-2.5 py-1 text-[11px] font-mono font-bold tracking-[0.14em] uppercase whitespace-nowrap"
          >
            {link.label}
          </span>
        ))}
      </div>

      {/* Visible links */}
      {visibleLinks.map(link => (
        <NavLink key={link.href} href={link.href}>{link.label}</NavLink>
      ))}

      {/* "More" dropdown for overflow */}
      {hasOverflow && (
        <div className="relative shrink-0" ref={moreRef}>
          <button
            onClick={() => setMoreOpen(v => !v)}
            aria-label="More pages"
            aria-haspopup="true"
            aria-expanded={moreOpen}
            className={`relative flex items-center gap-1 px-2.5 py-1 text-[11px] font-mono font-bold tracking-[0.14em] uppercase transition-colors duration-150 whitespace-nowrap cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-accent/40 ${
              moreOpen || overflowHasActive
                ? 'text-foreground'
                : 'text-muted-foreground hover:text-foreground'
            }`}
          >
            MORE
            <ChevronDown className={`w-3 h-3 transition-transform duration-200 ${moreOpen ? 'rotate-180' : ''}`} />
            {overflowHasActive && !moreOpen && (
              <span className="absolute left-2.5 right-2.5 -bottom-[7px] h-[2px] bg-accent" />
            )}
          </button>

          <AnimatePresence>
            {moreOpen && (
              <motion.div
                initial={{ opacity: 0, y: 4, scale: 0.98 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: 4, scale: 0.98 }}
                transition={{ duration: 0.1, ease: 'easeOut' }}
                className="absolute left-0 top-full mt-2 w-48 bg-card border border-border/40 rounded-[var(--radius)] shadow-md shadow-black/25 z-[200] overflow-hidden p-1"
              >
                {overflowLinks.map(link => {
                  const isActive = link.href === '/' ? pathname === '/' : pathname.startsWith(link.href);
                  return (
                    <Link
                      key={link.href}
                      href={link.href}
                      className={`block px-3 py-2 rounded-[calc(var(--radius)-2px)] text-[11px] font-mono font-bold uppercase tracking-[0.14em] transition-colors duration-150 focus:outline-none focus-visible:ring-2 focus-visible:ring-accent/40 ${
                        isActive
                          ? 'text-foreground bg-foreground/[0.07]'
                          : 'text-muted-foreground hover:text-foreground hover:bg-foreground/[0.04]'
                      }`}
                    >
                      {link.label}
                    </Link>
                  );
                })}
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      )}
    </div>
  );
}

/* ── LiveBadge ─────────────────────────────────────────────────────────── */

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
    <div className="hidden xl:flex items-center gap-2 px-2.5 h-7 border border-border/40" role="status" aria-label="Live data active">
      <div className="flex items-center gap-1.5">
        <div className="w-1.5 h-1.5 rounded-full bg-success" aria-hidden="true" />
        <span className="text-success text-[10px] font-mono font-bold uppercase tracking-[0.12em]">LIVE</span>
      </div>
      <span className="page-header-divider" />
      {tz && <span className="text-muted-foreground text-[10px] font-mono uppercase tracking-[0.08em]">{tz}</span>}
      {time && (
        <span className="text-foreground text-[11px] font-mono tabular-nums">{time}</span>
      )}
    </div>
  );
}

/* ── SearchTrigger ─────────────────────────────────────────────────────── */

function SearchTrigger({ onClick, className = '' }: { onClick: () => void; className?: string }) {
  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-2 h-7 pl-2.5 pr-2 border border-border/40 hover:border-border hover:bg-foreground/[0.03] text-muted-foreground hover:text-foreground transition-colors duration-150 group focus:outline-none focus-visible:ring-2 focus-visible:ring-accent/40 ${className}`}
      aria-label="Search (Ctrl+K)"
    >
      <Search className="w-3 h-3" />
      <span className="text-[10px] font-mono font-semibold uppercase tracking-[0.10em]">SEARCH</span>
      <kbd className="ml-0.5 px-1.5 h-4 inline-flex items-center border border-border/60 text-[9.5px] font-mono text-muted-foreground group-hover:text-foreground transition-colors">
        ⌘K
      </kbd>
    </button>
  );
}

/* ── UserMenu ──────────────────────────────────────────────────────────── */

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
        className={`flex items-center gap-1.5 h-7 pl-1 pr-2 rounded-[var(--radius)] border transition-all duration-150 focus:outline-none focus:ring-2 focus:ring-primary/25 focus:ring-offset-1 focus:ring-offset-background ${
          open ? 'bg-foreground/[0.06] border-border/40' : 'border-transparent hover:bg-foreground/[0.04] hover:border-border/25'
        }`}
      >
        <div className="w-5 h-5 rounded-[calc(var(--radius)-2px)] bg-primary/20 text-primary flex items-center justify-center text-[11px] font-bold shrink-0 border border-primary/20">
          {initials}
        </div>
        <span className="hidden sm:block text-[10px] font-mono font-semibold uppercase tracking-[0.10em] text-foreground leading-none">
          {user?.first_name || 'USER'}
        </span>
        <ChevronDown className={`hidden sm:block w-3 h-3 text-muted-foreground/40 transition-transform duration-200 ${open ? 'rotate-180' : ''}`} />
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: 4, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 4, scale: 0.98 }}
            transition={{ duration: 0.1, ease: 'easeOut' }}
            className="absolute right-0 top-full mt-1.5 w-56 bg-card border border-border/40 rounded-[var(--radius)] shadow-md shadow-black/25 z-[200] overflow-hidden"
          >
            <div className="px-3 py-3 border-b border-border/20">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-[calc(var(--radius)-1px)] bg-primary/15 text-primary flex items-center justify-center text-[12.5px] font-bold shrink-0 border border-primary/20">
                  {initials}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-[13px] font-semibold text-foreground truncate leading-tight">
                    {user?.first_name} {user?.last_name}
                  </div>
                  <div className="text-[11.5px] text-muted-foreground/40 truncate mt-0.5 font-mono">{user?.email}</div>
                </div>
                {isRealAdmin && !viewAsUser && (
                  <span className="text-[9.5px] font-bold uppercase tracking-wider px-1.5 py-0.5 bg-primary/10 text-primary border border-primary/20 rounded-[3px] shrink-0">
                    Admin
                  </span>
                )}
                {isRealAdmin && viewAsUser && (
                  <span className="text-[9.5px] font-bold uppercase tracking-wider px-1.5 py-0.5 bg-foreground/[0.06] text-muted-foreground border border-border/30 rounded-[3px] shrink-0">
                    User
                  </span>
                )}
              </div>
            </div>
            <div className="p-1">
              <Link
                href="/settings"
                onClick={() => setOpen(false)}
                className="w-full flex items-center gap-2 px-2.5 py-2 rounded-[calc(var(--radius)-2px)] text-[10px] font-mono font-semibold uppercase tracking-[0.10em] text-muted-foreground hover:text-foreground hover:bg-foreground/[0.04] transition-colors duration-150 focus:outline-none focus-visible:ring-2 focus-visible:ring-accent/40"
              >
                <Settings className="w-3 h-3" />
                SETTINGS
              </Link>
              <button
                onClick={() => { setOpen(false); logout(); }}
                className="w-full flex items-center gap-2 px-2.5 py-2 rounded-[calc(var(--radius)-2px)] text-[10px] font-mono font-semibold uppercase tracking-[0.10em] text-muted-foreground hover:text-destructive hover:bg-destructive/[0.06] transition-colors duration-150 focus:outline-none focus-visible:ring-2 focus-visible:ring-accent/40"
              >
                <LogOut className="w-3 h-3" />
                SIGN OUT
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

/* ── ThemeToggle ────────────────────────────────────────────────────────── */

function ThemeToggle() {
  const { theme, toggleTheme } = useTheme();
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);
  if (!mounted) return <div className="w-8 h-8" />;

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

/* ── MobileNavLink ─────────────────────────────────────────────────────── */

function MobileNavLink({ href, children }: { href: string; children: React.ReactNode }) {
  const pathname = usePathname();
  const isActive = href === '/' ? pathname === '/' : pathname.startsWith(href);

  return (
    <Link
      href={href}
      className={`px-3 py-2 rounded-[var(--radius)] text-[11px] font-mono font-bold uppercase tracking-[0.14em] transition-colors duration-150 ${
        isActive
          ? 'text-foreground bg-foreground/[0.07]'
          : 'text-muted-foreground hover:text-foreground hover:bg-foreground/[0.04]'
      }`}
    >
      {children}
    </Link>
  );
}

/* ── Main Navbar ───────────────────────────────────────────────────────── */

export default function Navbar({ onOpenSearch }: { onOpenSearch?: () => void }) {
  const { user, logout, isAuthenticated, viewAsUser } = useAuth();
  const { theme } = useTheme();
  const isRealAdmin = !!user && (user.role === 'owner' || user.role === 'admin' || user.is_admin);
  const [menuOpen, setMenuOpen] = useState(false);
  const pathname = usePathname();

  // Close mobile menu on navigation
  useEffect(() => { setMenuOpen(false); }, [pathname]);

  // Close mobile menu on Escape
  useEffect(() => {
    if (!menuOpen) return;
    const handleKey = (e: KeyboardEvent) => { if (e.key === 'Escape') setMenuOpen(false); };
    document.addEventListener('keydown', handleKey);
    return () => document.removeEventListener('keydown', handleKey);
  }, [menuOpen]);

  // Filter nav items based on role
  const filteredLinks = NAV_ITEMS.filter(item =>
    !item.adminOnly || (isRealAdmin && !viewAsUser)
  );

  return (
    <nav aria-label="Main navigation" className="fixed top-0 left-0 right-0 z-[100] h-[56px] bg-background border-b border-border/40">
      <div className="max-w-[1600px] mx-auto px-3 sm:px-5 lg:px-6 h-full flex items-center gap-3 sm:gap-4">

        {/* Logo */}
        <Link href="/" className="shrink-0 mr-1 sm:mr-2">
          <Image
            src={theme === 'dark' ? '/investment-x-logo-light.svg' : '/investment-x-logo-dark.svg'}
            alt="Investment-X"
            width={160}
            height={16}
            className="h-[18px] w-auto"
            priority
            unoptimized
          />
        </Link>

        {/* Desktop nav — auto-overflows into "More" dropdown */}
        <OverflowNav links={filteredLinks} />

        {/* Right actions */}
        <div className="flex items-center gap-1.5 ml-auto shrink-0">
          {/* Utility buttons — hidden on small phones to keep hamburger visible */}
          {onOpenSearch && (
            <>
              <button
                onClick={onOpenSearch}
                className="hidden sm:flex lg:hidden btn-icon"
                aria-label="Search (Ctrl+K)"
              >
                <Search className="w-3.5 h-3.5" />
              </button>
              <SearchTrigger onClick={onOpenSearch} className="hidden lg:flex" />
            </>
          )}

          <LiveBadge />

          <div className="hidden xl:block w-px h-3.5 bg-border/30 mx-1.5" />

          <span className="hidden sm:flex items-center gap-1.5">
            <ThemeToggle />
          </span>

          <div className="w-px h-3.5 bg-border/30 mx-1.5 hidden sm:block" />

          {isAuthenticated ? (
            <UserMenu />
          ) : (
            <Link
              href="/login"
              className="h-7 px-3 bg-foreground text-background text-[10px] font-mono font-bold uppercase tracking-[0.12em] inline-flex items-center hover:opacity-85 transition-opacity duration-150 focus:outline-none focus-visible:ring-2 focus-visible:ring-accent/40"
            >
              SIGN IN
            </Link>
          )}

          {/* Mobile menu button — always visible below md */}
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

      {/* Mobile menu + backdrop */}
      <AnimatePresence>
        {menuOpen && (
          <>
            {/* Backdrop — click to close */}
            <motion.div
              key="backdrop"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.12 }}
              className="md:hidden fixed inset-0 top-[56px] bg-black/20 z-[80]"
              onClick={() => setMenuOpen(false)}
              aria-hidden="true"
            />
            {/* Menu panel */}
            <motion.div
              key="menu"
              initial={{ opacity: 0, y: -6 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -6 }}
              transition={{ duration: 0.12 }}
              role="navigation"
              aria-label="Mobile navigation"
              className="md:hidden absolute top-[56px] left-0 right-0 bg-background border-b border-border/40 px-3 py-2 flex flex-col gap-0.5 shadow-md z-[90]"
            >
              {filteredLinks.map(link => (
                <MobileNavLink key={link.href} href={link.href}>{link.label}</MobileNavLink>
              ))}
              <div className="mt-1.5 pt-2 border-t border-border/20">
                {isAuthenticated ? (
                  <button
                    onClick={logout}
                    className="flex items-center gap-2 px-3 py-2 rounded-[var(--radius)] text-[11px] font-mono font-bold uppercase tracking-[0.14em] text-muted-foreground hover:text-destructive hover:bg-destructive/[0.06] transition-colors w-full focus:outline-none focus-visible:ring-2 focus-visible:ring-accent/40"
                  >
                    <LogOut className="w-3 h-3" />
                    SIGN OUT
                  </button>
                ) : (
                  <Link
                    href="/login"
                    className="flex items-center justify-center gap-2 w-full py-2.5 bg-foreground text-background text-[11px] font-mono font-bold uppercase tracking-[0.14em] focus:outline-none focus-visible:ring-2 focus-visible:ring-accent/40"
                  >
                    <LogIn className="w-3 h-3" />
                    SIGN IN
                  </Link>
                )}
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </nav>
  );
}
