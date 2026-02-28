'use client';

import { type ReactNode, type RefObject } from 'react';
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

  // Top bar (in main area, right of sidebar)
  /** Content placed after the sidebar toggle button on the left */
  topBarLeft?: ReactNode;
  /** Action buttons on the right side of the top bar */
  topBarRight?: ReactNode;

  // Main content
  children: ReactNode;
  /** Optional ref forwarded to the main scrollable element */
  mainScrollRef?: RefObject<HTMLElement>;
  mainClassName?: string;
}

export default function NavigatorShell({
  sidebarOpen,
  onSidebarToggle,
  sidebarIcon,
  sidebarLabel,
  sidebarHeaderActions,
  sidebarContent,
  topBarLeft,
  topBarRight,
  children,
  mainScrollRef,
  mainClassName = '',
}: NavigatorShellProps) {
  return (
    <div className="h-[calc(100vh-40px)] flex overflow-hidden">
      {/* ── Sidebar ── */}
      <aside
        className={`shrink-0 transition-all duration-200 overflow-hidden border-r border-border/50 bg-card/20 flex flex-col ${
          sidebarOpen ? 'w-[190px]' : 'w-0'
        }`}
      >
        {/* Header */}
        <div className="h-8 px-2.5 border-b border-border/50 flex items-center justify-between shrink-0">
          <div className="text-[11px] font-semibold tracking-wide flex items-center gap-1.5 text-muted-foreground">
            {sidebarIcon}
            {sidebarLabel}
          </div>
          <div className="flex items-center gap-0.5">
            {sidebarHeaderActions}
          </div>
        </div>
        {/* Body */}
        {sidebarContent}
      </aside>

      {/* ── Main area ── */}
      <section className="min-h-0 flex-1 flex flex-col bg-background overflow-hidden">
        {/* Top bar */}
        <div className="h-8 px-2.5 border-b border-border/50 flex items-center justify-between gap-2 shrink-0">
          <div className="shrink-0 flex items-center gap-1.5">
            <button
              onClick={onSidebarToggle}
              className="w-5 h-5 rounded flex items-center justify-center text-muted-foreground hover:text-foreground hover:bg-foreground/8 transition-colors"
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
