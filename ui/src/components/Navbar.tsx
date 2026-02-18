'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { 
  User as UserIcon, LogOut, LogIn, Database, Radio, 
  Menu, X, Layout, Activity, Cpu, Hexagon
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

export default function Navbar() {
  const { user, logout, isAuthenticated } = useAuth();
  const [menuOpen, setMenuOpen] = React.useState(false);
  const pathname = usePathname();

  React.useEffect(() => {
    setMenuOpen(false);
  }, [pathname]);

  return (
    <nav className="fixed top-0 left-0 right-0 z-[100] h-14 bg-[#05070c]/80 backdrop-blur-2xl border-b border-white/[0.05]">
      <div className="max-w-[1920px] mx-auto px-6 h-full flex items-center justify-between">
        
        {/* LOGO AREA */}
        <div className="flex items-center gap-8">
            <Link href="/" className="flex items-center gap-2.5 group">
                <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-indigo-600 to-sky-600 flex items-center justify-center shadow-lg shadow-indigo-500/20 group-hover:scale-105 transition-transform">
                    <Hexagon className="w-4 h-4 text-white fill-white/20" />
                </div>
                <div className="flex flex-col leading-none">
                    <span className="text-sm font-black text-white tracking-tighter uppercase">Investment<span className="text-indigo-400">X</span></span>
                    <span className="text-[9px] font-mono text-slate-500 uppercase tracking-[0.3em] mt-0.5">Core.Nexus</span>
                </div>
            </Link>

            {/* Desktop Navigation */}
            <div className="hidden lg:flex items-center gap-1 p-1 bg-black/20 rounded-xl border border-white/5">
                <NavLink href="/" icon={<Layout className="w-3.5 h-3.5" />}>Dashboard</NavLink>
                <NavLink href="/intel" icon={<Radio className="w-3.5 h-3.5" />}>Intel</NavLink>
                {user?.is_admin && (
                  <NavLink href="/admin/timeseries" icon={<Database className="w-3.5 h-3.5" />}>System</NavLink>
                )}
            </div>
        </div>

        {/* SYSTEM STATUS (Center) */}
        <div className="hidden xl:flex items-center gap-6 px-4 py-1.5 rounded-full bg-white/[0.02] border border-white/[0.05]">
            <div className="flex items-center gap-2">
                <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse shadow-[0_0_8px_rgba(16,185,129,0.5)]" />
                <span className="text-[10px] font-mono text-emerald-500/80 uppercase">Node: Active</span>
            </div>
            <div className="w-px h-3 bg-white/10" />
            <div className="flex items-center gap-2">
                <Cpu className="w-3 h-3 text-slate-600" />
                <span className="text-[10px] font-mono text-slate-500 uppercase">Quant Kernel: 1.2.0</span>
            </div>
        </div>

        {/* ACTIONS AREA */}
        <div className="flex items-center gap-3">
          <div className="hidden md:flex items-center">
             <TaskNotifications />
          </div>

          <div className="h-4 w-px bg-white/10 mx-1 hidden md:block" />

          {isAuthenticated ? (
             <div className="flex items-center gap-3">
                <div className="hidden sm:flex flex-col items-end leading-none">
                    <span className="text-[11px] font-bold text-slate-200">{user?.first_name || 'Operator'}</span>
                    <span className="text-[9px] font-mono text-slate-500 uppercase tracking-tighter">{user?.email?.split('@')[0]}</span>
                </div>
                
                <div className="group relative">
                    <button 
                        onClick={logout}
                        className="w-9 h-9 rounded-xl bg-white/5 border border-white/10 flex items-center justify-center text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 hover:border-rose-500/20 transition-all"
                    >
                        <UserIcon className="w-4 h-4" />
                    </button>
                    {/* Logout toolitp on hover could go here */}
                </div>
             </div>
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
              {menuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
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
            className="lg:hidden absolute top-14 left-0 right-0 bg-[#05070c] border-b border-white/10 p-6 flex flex-col gap-4 shadow-2xl z-[90]"
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
