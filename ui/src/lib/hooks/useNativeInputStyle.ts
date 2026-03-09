import { useMemo } from 'react';
import { useTheme } from '@/context/ThemeContext';

/**
 * Returns an inline style object for native form elements (input, select)
 * that need explicit colorScheme, background, and foreground to work
 * correctly across light/dark themes.
 *
 * Usage:
 *   const nativeInputStyle = useNativeInputStyle();
 *   <input style={nativeInputStyle} ... />
 */
export function useNativeInputStyle(): React.CSSProperties {
  const { theme } = useTheme();
  return useMemo(
    () => ({
      colorScheme: theme === 'light' ? ('light' as const) : ('dark' as const),
      backgroundColor: 'rgb(var(--background))',
      color: 'rgb(var(--foreground))',
    }),
    [theme],
  );
}
