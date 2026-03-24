import { useState, useRef, useCallback, useEffect } from 'react';

const BREAKPOINT = 1024;

/**
 * Manages sidebar open/close state with responsive behavior:
 * - Auto-collapses when viewport narrows below breakpoint
 * - Auto-expands when viewport widens above breakpoint
 * - Respects manual user collapse (toggle button) — won't auto-expand until user reopens
 *
 * Returns `sidebarOpen`, `toggleSidebar` (for the UI button), and `setSidebarOpen` (programmatic).
 */
export function useResponsiveSidebar(initialOpen = true) {
  const [sidebarOpen, setSidebarOpen] = useState(initialOpen);
  const userManuallyCollapsed = useRef(false);

  useEffect(() => {
    if (typeof window === 'undefined') return;

    const sync = () => {
      if (window.innerWidth < BREAKPOINT) {
        setSidebarOpen(false);
      } else if (!userManuallyCollapsed.current) {
        setSidebarOpen(true);
      }
    };

    sync();
    window.addEventListener('resize', sync);
    return () => window.removeEventListener('resize', sync);
  }, []);

  const toggleSidebar = useCallback(() => {
    setSidebarOpen((prev) => {
      const next = !prev;
      if (!next && typeof window !== 'undefined' && window.innerWidth >= BREAKPOINT) {
        userManuallyCollapsed.current = true;
      }
      if (next) {
        userManuallyCollapsed.current = false;
      }
      return next;
    });
  }, []);

  return { sidebarOpen, setSidebarOpen, toggleSidebar };
}
