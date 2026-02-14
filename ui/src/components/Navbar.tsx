'use client';

import React from 'react';
import Link from 'next/link';
import { useAuth } from '@/context/AuthContext';
import { User as UserIcon, LogOut, LogIn, LayoutDashboard, Database, Radio } from 'lucide-react';

export default function Navbar() {
  const { user, logout, isAuthenticated } = useAuth();

  const [menuOpen, setMenuOpen] = React.useState(false);

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 bg-black/50 backdrop-blur-xl border-b border-white/5">
      <div className="max-w-[1600px] mx-auto px-6 h-16 flex items-center justify-between">
        
        <Link href="/" className="flex items-center gap-3 group">
          <img src="/logo.svg" alt="Investment-X" className="h-8 w-auto rounded-sm group-hover:opacity-80 transition-opacity" />
        </Link>
        
        {/* Desktop Navigation */}
        <div className="hidden md:flex items-center gap-6">
            <Link href="/" className="text-sm font-medium text-slate-300 hover:text-white transition-colors">
                Dashboard
            </Link>
            <Link href="/intel" className="text-sm font-medium text-slate-300 hover:text-white transition-colors flex items-center gap-1.5">
                <Radio className="w-3.5 h-3.5" />
                Intel Feed
            </Link>
            <Link href="/studio" className="text-sm font-medium text-slate-300 hover:text-white transition-colors flex items-center gap-1.5">
                Analysis Studio
                <span className="px-1.5 py-0.5 text-[10px] bg-indigo-500/20 text-indigo-300 rounded border border-indigo-500/20">BETA</span>
            </Link>
            {user?.is_admin && (
              <Link href="/admin/timeseries" className="text-sm font-medium text-slate-300 hover:text-white transition-colors flex items-center gap-1.5">
                <Database className="w-3.5 h-3.5" />
                Timeseries
                <span className="px-1.5 py-0.5 text-[10px] bg-rose-500/20 text-rose-300 rounded border border-rose-500/20">ADMIN</span>
              </Link>
            )}
        </div>

        {/* User Actions (Desktop) */}
        <div className="hidden md:flex items-center gap-4">
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
            className="md:hidden p-2 text-slate-300 hover:text-white"
            onClick={() => setMenuOpen(!menuOpen)}
        >
            {menuOpen ? (
                <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>
            ) : (
                <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="4" x2="20" y1="12" y2="12"/><line x1="4" x2="20" y1="6" y2="6"/><line x1="4" x2="20" y1="18" y2="18"/></svg>
            )}
        </button>
      </div>

      {/* Mobile Menu Overlay */}
      {menuOpen && (
        <div className="md:hidden absolute top-16 left-0 right-0 bg-slate-950/95 backdrop-blur-xl border-b border-white/10 p-6 flex flex-col gap-6 shadow-2xl animate-in slide-in-from-top-4">
             <div className="flex flex-col gap-4">
                <Link href="/" onClick={() => setMenuOpen(false)} className="text-lg font-medium text-slate-300 hover:text-white transition-colors py-2 border-b border-white/5">
                    Dashboard
                </Link>
                <Link href="/intel" onClick={() => setMenuOpen(false)} className="text-lg font-medium text-slate-300 hover:text-white transition-colors py-2 border-b border-white/5 flex items-center gap-2">
                    <Radio className="w-4 h-4" /> Intel Feed
                </Link>
                <Link href="/studio" onClick={() => setMenuOpen(false)} className="text-lg font-medium text-slate-300 hover:text-white transition-colors py-2 border-b border-white/5 flex items-center gap-2">
                    Analysis Studio <span className="text-[10px] bg-indigo-500/20 text-indigo-300 px-1.5 py-0.5 rounded">BETA</span>
                </Link>
                {user?.is_admin && (
                  <Link href="/admin/timeseries" onClick={() => setMenuOpen(false)} className="text-lg font-medium text-slate-300 hover:text-white transition-colors py-2 border-b border-white/5 flex items-center gap-2">
                    <Database className="w-4 h-4" /> Timeseries (Admin)
                  </Link>
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
                      onClick={() => setMenuOpen(false)}
                      className="flex items-center justify-center gap-2 w-full py-3 bg-sky-500 hover:bg-sky-400 text-white rounded-xl font-medium transition-colors shadow-lg shadow-sky-500/20"
                    >
                      <LogIn className="w-4 h-4" /> Sign In
                    </Link>
                )}
             </div>
        </div>
      )}
    </nav>
  );
}
