import React from 'react';

export default function Footer() {
  return (
    <footer className="max-w-[1920px] mx-auto py-12 px-8 border-t border-border flex flex-col md:flex-row justify-between items-center gap-6 opacity-60 grayscale hover:grayscale-0 hover:opacity-100 transition-all duration-700 ease-out mt-auto">
      <div className="flex flex-col gap-1">
        <div className="text-slate-500 text-[10px] font-mono tracking-[0.2em] uppercase">
          [ End of Intelligence Feed ]
        </div>
        <div className="text-slate-600 text-[10px] font-light">
           System Status: <span className="text-emerald-500">Nominal</span> • Latency: <span className="text-indigo-400">12ms</span>
        </div>
      </div>
      
      <div className="flex items-center gap-8">
         <div className="text-right">
            <div className="text-slate-500 text-[10px] font-bold uppercase tracking-widest text-right">
              Investment-X
            </div>
            <div className="text-slate-600 text-[10px] font-light">
              © {new Date().getFullYear()} Research Library. Proprietary Models.
            </div>
         </div>
      </div>
    </footer>
  );
}
