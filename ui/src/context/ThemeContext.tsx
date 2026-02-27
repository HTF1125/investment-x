'use client';

import React, { createContext, useContext, useEffect, useState } from 'react';
import { type ChartStyle } from '@/lib/chartTheme';

type Theme = 'light' | 'dark';

interface ThemeContextType {
  theme: Theme;
  toggleTheme: () => void;
  chartStyle: ChartStyle;
  setChartStyle: (style: ChartStyle) => void;
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  // Initialize with 'dark' to prevent hydration mismatch flash if possible,
  // but better to check system preference in useEffect.
  // For now, default to 'dark' as it's the primary aesthetic.
  const [theme, setTheme] = useState<Theme>('dark');
  const [chartStyle, setChartStyleState] = useState<ChartStyle>('terminal');
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    // Check local storage or system preference
    const stored = localStorage.getItem('theme') as Theme;
    if (stored) {
      setTheme(stored);
    } else if (window.matchMedia('(prefers-color-scheme: light)').matches) {
      setTheme('light');
    }

    const storedStyle = localStorage.getItem('chart_style') as ChartStyle;
    if (storedStyle) {
      setChartStyleState(storedStyle);
    }

    setMounted(true);
  }, []);

  useEffect(() => {
    if (!mounted) return;

    const root = window.document.documentElement;
    root.classList.remove('light', 'dark');
    root.classList.add(theme);

    // Also set specific style helper for Tailwind generic usage if needed
    if (theme === 'dark') {
      root.style.colorScheme = 'dark';
    } else {
      root.style.colorScheme = 'light';
    }

    localStorage.setItem('theme', theme);
  }, [theme, mounted]);

  const toggleTheme = () => {
    setTheme(prev => prev === 'dark' ? 'light' : 'dark');
  };

  const setChartStyle = (style: ChartStyle) => {
    setChartStyleState(style);
    localStorage.setItem('chart_style', style);
  };

  return (
    <ThemeContext.Provider value={{ theme, toggleTheme, chartStyle, setChartStyle }}>
      <div style={{ visibility: mounted ? 'visible' : 'hidden' }}>
        {children}
      </div>
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  const context = useContext(ThemeContext);
  if (context === undefined) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return context;
}
