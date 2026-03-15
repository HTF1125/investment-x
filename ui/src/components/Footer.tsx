import React from 'react';

export default function Footer() {
  return (
    <footer className="max-w-[1440px] mx-auto py-3 px-4 sm:px-6 border-t border-border/15 flex flex-row justify-between items-center mt-auto w-full">
      <span className="text-muted-foreground/40 text-[9px] font-mono tracking-[0.1em] uppercase">
        Investment-X
      </span>
      <span className="text-muted-foreground/40 text-[9px] font-mono">
        &copy; {new Date().getFullYear()}
      </span>
    </footer>
  );
}
