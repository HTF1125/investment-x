'use client';

import React from 'react';
import Link from 'next/link';
import { useAuth } from '@/context/AuthContext';
import { User as UserIcon, LogOut, LogIn, LayoutDashboard, Database, Radio } from 'lucide-react';

export default function Navbar() {
  const { user, logout, isAuthenticated } = useAuth();

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 bg-black/50 backdrop-blur-xl border-b border-white/5">
      <div className="max-w-[1600px] mx-auto px-6 h-16 flex items-center justify-between">
        
        {/* Brand */}
        <Link href="/" className="flex items-center gap-2 group">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-sky-500 to-indigo-600 flex items-center justify-center shadow-lg shadow-sky-500/20 group-hover:scale-105 transition-transform">
            <LayoutDashboard className="w-5 h-5 text-white" />
          </div>
          <span className="font-bold text-white tracking-tight">Investment-<span className="text-sky-400">X</span></span>
        </Link>
        
        {/* Navigation */}
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

        {/* User Actions */}
        <div className="flex items-center gap-4">
          {isAuthenticated ? (
             <>
                <div className="hidden md:flex items-center gap-3 px-3 py-1.5 bg-white/5 rounded-full border border-white/5">
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
      </div>
    </nav>
  );
}
