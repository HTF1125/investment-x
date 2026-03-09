import React from 'react';

export default function Footer() {
  return (
    <footer className="max-w-[1920px] mx-auto py-3 px-4 sm:px-6 border-t border-border/40 flex flex-row justify-between items-center mt-auto">
      <span className="text-muted-foreground/40 text-[10px] font-mono tracking-widest uppercase">
        Investment-X
      </span>
      <span className="text-muted-foreground/30 text-[10px]">
        &copy; {new Date().getFullYear()} Research Library
      </span>
    </footer>
  );
}
