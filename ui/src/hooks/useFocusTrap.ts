import { useEffect, useRef, useCallback } from 'react';

const FOCUSABLE_SELECTOR = [
  'a[href]',
  'button:not([disabled])',
  'input:not([disabled])',
  'select:not([disabled])',
  'textarea:not([disabled])',
  '[tabindex]:not([tabindex="-1"])',
].join(', ');

/**
 * Trap keyboard focus inside a container while active.
 * Returns a ref to attach to the container element.
 *
 * - Tab / Shift+Tab cycle through focusable children
 * - Escape calls `onEscape` (if provided)
 * - Focus is restored to the previously focused element on deactivation
 */
export function useFocusTrap(
  isActive: boolean,
  onEscape?: () => void,
) {
  const containerRef = useRef<HTMLDivElement>(null);
  const previouslyFocusedRef = useRef<HTMLElement | null>(null);

  const getFocusableElements = useCallback(() => {
    if (!containerRef.current) return [];
    return Array.from(
      containerRef.current.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR),
    ).filter((el) => el.offsetParent !== null); // exclude hidden elements
  }, []);

  useEffect(() => {
    if (!isActive) return;

    // Save the currently focused element so we can restore it later
    previouslyFocusedRef.current = document.activeElement as HTMLElement | null;

    // Focus the first focusable element inside the trap after a tick
    // (allows the container to render)
    const rafId = requestAnimationFrame(() => {
      const focusable = getFocusableElements();
      if (focusable.length > 0) {
        focusable[0].focus();
      } else {
        // If no focusable children, make the container itself focusable
        containerRef.current?.focus();
      }
    });

    return () => {
      cancelAnimationFrame(rafId);
      // Restore focus to the element that was focused before the trap activated
      previouslyFocusedRef.current?.focus();
    };
  }, [isActive, getFocusableElements]);

  useEffect(() => {
    if (!isActive) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && onEscape) {
        e.preventDefault();
        onEscape();
        return;
      }

      if (e.key !== 'Tab') return;

      const focusable = getFocusableElements();
      if (focusable.length === 0) {
        e.preventDefault();
        return;
      }

      const first = focusable[0];
      const last = focusable[focusable.length - 1];

      if (e.shiftKey) {
        if (document.activeElement === first) {
          e.preventDefault();
          last.focus();
        }
      } else {
        if (document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [isActive, onEscape, getFocusableElements]);

  return containerRef;
}
