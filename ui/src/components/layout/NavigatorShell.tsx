'use client';

import { type ReactNode, type RefObject, useState, useRef, useEffect } from 'react';
import { PanelLeftClose, PanelLeftOpen } from 'lucide-react';

interface NavigatorShellProps {
  // Sidebar
  sidebarOpen: boolean;
  onSidebarToggle: () => void;
  sidebarIcon: ReactNode;
  sidebarLabel: string;
  /** Buttons rendered on the right of the sidebar header (e.g. + and collapse) */
  sidebarHeaderActions?: ReactNode;
  /** Full body of the sidebar below the header (search + list, etc.) */
  sidebarContent: ReactNode;
  sidebarClassName?: string;
  sidebarOpenWidthClassName?: string;
  sidebarHeaderClassName?: string;

  // Top bar (in main area, right of sidebar)
  /** Content placed after the sidebar toggle button on the left */
  topBarLeft?: ReactNode;
  /** Action buttons on the right side of the top bar */
  topBarRight?: ReactNode;
  topBarClassName?: string;

  // Main content
  children: ReactNode;
  /** Optional ref forwarded to the main scrollable element */
  mainScrollRef?: RefObject<HTMLElement>;
  mainClassName?: string;
  shellClassName?: string;
  mainSectionClassName?: string;
}

export default function NavigatorShell({
  sidebarOpen,
  onSidebarToggle,
  sidebarIcon,
  sidebarLabel,
  sidebarHeaderActions,
  sidebarContent,
  sidebarClassName = '',
  sidebarOpenWidthClassName = 'w-[190px]',
  sidebarHeaderClassName = '',
  topBarLeft,
  topBarRight,
  topBarClassName = '',
  children,
  mainScrollRef,
  mainClassName = '',
  shellClassName = '',
  mainSectionClassName = '',
}: NavigatorShellProps) {
  const [sidebarWidth, setSidebarWidth] = useState(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('navigator-sidebar-width');
      if (saved) return Number(saved);
    }
    if (sidebarOpenWidthClassName.includes('[190px]')) return 190;
    if (sidebarOpenWidthClassName.includes('[240px]')) return 240;
    if (sidebarOpenWidthClassName.includes('[250px]')) return 250;
    return 200;
  });

  const isDraggingRef = useRef(false);
  const [isDragging, setIsDragging] = useState(false);

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!isDraggingRef.current) return;
      const newWidth = Math.max(150, Math.min(800, e.clientX));
      setSidebarWidth(newWidth);
    };
    const handleMouseUp = () => {
      if (isDraggingRef.current) {
        isDraggingRef.current = false;
        setIsDragging(false);
        document.body.style.cursor = '';
        localStorage.setItem('navigator-sidebar-width', sidebarWidth.toString());
      }
    };

    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, [sidebarWidth]);

  return (
    <div className={`h-[calc(100vh-56px)] flex overflow-hidden ${shellClassName}`}>
      {/* ── Sidebar ── */}
      <aside
        className={`relative shrink-0 overflow-visible border-r border-border/40 bg-card/20 flex flex-col ${sidebarClassName}`}
        style={{
          width: sidebarOpen ? sidebarWidth : 0,
          transition: isDragging ? 'none' : 'width 0.2s',
          opacity: sidebarOpen ? 1 : 0
        }}
      >
        <div className="flex-1 min-h-0 overflow-hidden flex flex-col w-full h-full">
        {/* Header */}
        <div className={`h-11 px-3 border-b border-border/40 flex items-center justify-between shrink-0 ${sidebarHeaderClassName}`}>
          <div className="text-[12.5px] font-medium tracking-wide flex items-center gap-1.5 text-muted-foreground">
            {sidebarIcon}
            {sidebarLabel}
          </div>
          <div className="flex items-center gap-0.5">
            {sidebarHeaderActions}
          </div>
        </div>
        {/* Body */}
        {sidebarContent}
        </div>

        {/* Resize Handle */}
        {sidebarOpen && (
          <div
            className="absolute top-0 -right-1.5 w-3 h-full cursor-col-resize z-[50] group flex items-center justify-center hover:bg-primary/10 active:bg-primary/20"
            onMouseDown={(e) => {
              e.preventDefault();
              isDraggingRef.current = true;
              setIsDragging(true);
              document.body.style.cursor = 'col-resize';
            }}
          >
            <div className={`w-[2px] h-8 rounded-full transition-colors ${isDragging ? 'bg-primary' : 'bg-transparent group-hover:bg-border/60'}`} />
          </div>
        )}
      </aside>

      {/* ── Main area ── */}
      <section className={`min-h-0 flex-1 flex flex-col bg-background overflow-hidden ${mainSectionClassName}`}>
        {/* Top bar — matches .page-header height (44px) */}
        <div className={`h-11 px-3 border-b border-border/40 flex items-center justify-between gap-2 shrink-0 ${topBarClassName}`}
             style={{ background: 'rgb(var(--surface) / 0.30)' }}>
          <div className="shrink-0 flex items-center gap-1.5">
            <button
              onClick={onSidebarToggle}
              className="w-5 h-5 rounded flex items-center justify-center text-muted-foreground hover:text-primary hover:bg-primary/10 transition-colors"
              title={sidebarOpen ? 'Collapse sidebar' : 'Open sidebar'}
            >
              {sidebarOpen
                ? <PanelLeftClose className="w-3.5 h-3.5" />
                : <PanelLeftOpen className="w-3.5 h-3.5" />}
            </button>
            {topBarLeft}
          </div>
          <div className="flex items-center gap-1 overflow-x-auto no-scrollbar min-w-0">
            {topBarRight}
          </div>
        </div>
        {/* Content */}
        <div
          ref={mainScrollRef as RefObject<HTMLDivElement>}
          className={`min-h-0 flex-1 overflow-y-auto custom-scrollbar ${mainClassName}`}
        >
          {children}
        </div>
      </section>
    </div>
  );
}
