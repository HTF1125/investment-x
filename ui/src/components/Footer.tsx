import React from 'react';

export default function Footer() {
  return (
    <footer className="max-w-[1920px] mx-auto py-3 px-4 sm:px-8 border-t border-border flex flex-row justify-between items-center text-center md:text-left opacity-60 grayscale hover:grayscale-0 hover:opacity-100 transition-all duration-700 ease-out mt-auto">
      <div className="text-slate-500 text-[10px] font-mono tracking-[0.2em] uppercase">
        Investment-X
      </div>
      <div className="text-slate-600 text-[10px] font-light">
        © {new Date().getFullYear()} Research Library
      </div>
    </footer>
  );
}
