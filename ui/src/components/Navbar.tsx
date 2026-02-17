'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { User as UserIcon, LogOut, LogIn, Database, Radio, Menu, X } from 'lucide-react';
import TaskNotifications from '@/components/TaskNotifications';
import { AnimatePresence, motion } from 'framer-motion';

interface NavLinkProps {
  href: string;
  children: React.ReactNode;
  onClick?: () => void;
  className?: string;
}

/**
 * Shared nav link that auto-highlights when the current route matches.
 * Exact match for "/" to avoid false positives on sub-routes.
 */
function NavLink({ href, children, onClick, className = '' }: NavLinkProps) {
  const pathname = usePathname();
  const isActive = href === '/' ? pathname === '/' : pathname.startsWith(href);

  return (
    <Link
      href={href}
      onClick={onClick}
      className={`
        text-sm font-medium transition-colors flex items-center gap-1.5 relative
        ${isActive
          ? 'text-white'
          : 'text-slate-400 hover:text-slate-200'
        }
        ${className}
      `}
    >
      {children}
      {/* Active indicator bar (desktop only) */}
      {isActive && (
        <span className="hidden md:block absolute -bottom-[21px] left-0 right-0 h-[2px] bg-gradient-to-r from-sky-400 to-purple-500 rounded-full" />
      )}
    </Link>
  );
}

export default function Navbar() {
  const { user, logout, isAuthenticated } = useAuth();
  const [menuOpen, setMenuOpen] = React.useState(false);
  const pathname = usePathname();

  // Auto-close mobile menu on route change
  React.useEffect(() => {
    setMenuOpen(false);
  }, [pathname]);

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 bg-black/50 backdrop-blur-xl border-b border-white/5">
      <div className="max-w-[1600px] mx-auto px-6 h-16 flex items-center justify-between">
        
        <Link href="/" className="flex items-center gap-3 group">
          <img src="/logo.svg" alt="Investment-X" className="h-8 w-auto rounded-sm group-hover:opacity-80 transition-opacity" />
        </Link>
        
        {/* Desktop Navigation */}
        <div className="hidden md:flex items-center gap-6">
            <NavLink href="/">Dashboard</NavLink>
            <NavLink href="/intel">
                <Radio className="w-3.5 h-3.5" />
                Intel Feed
            </NavLink>
            <NavLink href="/studio">
                Analysis Studio
                <span className="px-1.5 py-0.5 text-[10px] bg-indigo-500/20 text-indigo-300 rounded border border-indigo-500/20">BETA</span>
            </NavLink>
            {user?.is_admin && (
              <NavLink href="/admin/timeseries">
                <Database className="w-3.5 h-3.5" />
                Timeseries
                <span className="px-1.5 py-0.5 text-[10px] bg-rose-500/20 text-rose-300 rounded border border-rose-500/20">ADMIN</span>
              </NavLink>
            )}
        </div>

        {/* User Actions (Desktop) */}
        <div className="hidden md:flex items-center gap-4">
          <TaskNotifications />
          {isAuthenticated ? (
             <>
                <div className="flex items-center gap-3 px-3 py-1.5 bg-white/5 rounded-full border border-white/5">
                    <div className="w-6 h-6 rounded-full bg-sky-500/20 flex items-center justify-center text-sky-400">
                        <UserIcon className="w-3 h-3" />
                    </div>
                    <div className="flex flex-col">
                        <span className="text-xs font-semibold text-slate-200 leading-none">{user?.first_name || 'User'}</span>
                        <span className="text-[10px] text-slate-500 font-mono leading-none mt-0.5">{user?.email}</span>
                    </div>
                </div>

                <button 
                  onClick={logout}
                  className="p-2 text-slate-400 hover:text-rose-400 hover:bg-white/5 rounded-lg transition-colors"
                  title="Logout"
                >
                  <LogOut className="w-5 h-5" />
                </button>
             </>
          ) : (
            <Link 
              href="/login"
              className="flex items-center gap-2 px-4 py-2 bg-sky-500 hover:bg-sky-400 text-white rounded-lg text-sm font-medium transition-colors shadow-lg shadow-sky-500/20"
            >
              <LogIn className="w-4 h-4" />
              Sign In
            </Link>
          )}
        </div>

        {/* Mobile Menu Button */}
        <button 
            className="md:hidden p-2 text-slate-300 hover:text-white transition-colors"
            onClick={() => setMenuOpen(!menuOpen)}
        >
            {menuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
        </button>
      </div>

      {/* Mobile Menu Overlay — animated with framer-motion */}
      <AnimatePresence>
        {menuOpen && (
          <motion.div
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.15, ease: 'easeOut' }}
            className="md:hidden absolute top-16 left-0 right-0 bg-slate-950/95 backdrop-blur-xl border-b border-white/10 p-6 flex flex-col gap-6 shadow-2xl"
          >
               <div className="flex flex-col gap-4">
                  <MobileNavLink href="/" pathname={pathname}>Dashboard</MobileNavLink>
                  <MobileNavLink href="/intel" pathname={pathname}>
                      <Radio className="w-4 h-4" /> Intel Feed
                  </MobileNavLink>
                  <MobileNavLink href="/studio" pathname={pathname}>
                      Analysis Studio <span className="text-[10px] bg-indigo-500/20 text-indigo-300 px-1.5 py-0.5 rounded">BETA</span>
                  </MobileNavLink>
                  {user?.is_admin && (
                    <MobileNavLink href="/admin/timeseries" pathname={pathname}>
                      <Database className="w-4 h-4" /> Timeseries (Admin)
                    </MobileNavLink>
                  )}
               </div>

               {/* Mobile User Actions */}
               <div className="flex flex-col gap-4 pt-2">
                  {isAuthenticated ? (
                    <>
                      <div className="flex items-center gap-3 px-3 py-3 bg-white/5 rounded-xl border border-white/5">
                          <div className="w-10 h-10 rounded-full bg-sky-500/20 flex items-center justify-center text-sky-400">
                              <UserIcon className="w-5 h-5" />
                          </div>
                          <div className="flex flex-col">
                              <span className="text-sm font-semibold text-slate-200">{user?.first_name || 'User'}</span>
                              <span className="text-xs text-slate-500 font-mono">{user?.email}</span>
                          </div>
                      </div>
                      <button 
                        onClick={logout}
                        className="flex items-center justify-center gap-2 w-full py-3 text-rose-300 bg-rose-500/10 hover:bg-rose-500/20 rounded-xl border border-rose-500/20 transition-colors font-medium"
                      >
                        <LogOut className="w-4 h-4" /> Logout
                      </button>
                    </>
                  ) : (
                      <Link 
                        href="/login"
                        className="flex items-center justify-center gap-2 w-full py-3 bg-sky-500 hover:bg-sky-400 text-white rounded-xl font-medium transition-colors shadow-lg shadow-sky-500/20"
                      >
                        <LogIn className="w-4 h-4" /> Sign In
                      </Link>
                  )}
               </div>
          </motion.div>
        )}
      </AnimatePresence>
    </nav>
  );
}

/** Mobile nav link with left-border active indicator. */
function MobileNavLink({ href, pathname, children }: { href: string; pathname: string; children: React.ReactNode }) {
  const isActive = href === '/' ? pathname === '/' : pathname.startsWith(href);

  return (
    <Link
      href={href}
      className={`
        text-lg font-medium transition-colors py-2 border-b border-white/5 flex items-center gap-2
        ${isActive
          ? 'text-white border-l-2 border-l-sky-400 pl-3'
          : 'text-slate-300 hover:text-white'
        }
      `}
    >
      {children}
    </Link>
  );
}
