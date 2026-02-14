'use client';

import { useAuth } from '@/context/AuthContext';
import { LogOut, User } from 'lucide-react';

export default function Header() {
  const { user, logout } = useAuth();

  return (
    <header className="max-w-[1600px] mx-auto mb-16 flex flex-col md:flex-row md:items-end justify-between gap-8">
        <div className="space-y-2">
           {/* Header content removed as requested */}
        </div>
        
        <div className="flex flex-col items-end gap-6 text-slate-500 font-mono text-xs">
            <div className="flex items-center gap-6">
                <div className="flex flex-col items-end">
                    <span className="text-[10px] text-slate-600 mb-1">DATA STATUS</span>
                    <span className="text-emerald-500 flex items-center gap-2">
                        <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]" />
                        LIVE PIPELINE
                    </span>
                </div>
                <div className="w-px h-8 bg-white/10" />
                <div className="flex flex-col items-end">
                    <span className="text-[10px] text-slate-600 mb-1">REGION</span>
                    <span className="text-slate-300 font-semibold uppercase">Seoul / KST</span>
                </div>
            </div>

        </div>
    </header>
  );
}
