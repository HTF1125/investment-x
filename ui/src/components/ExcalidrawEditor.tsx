'use client';

import React, { useCallback, useEffect, useRef, useState } from 'react';
import dynamic from 'next/dynamic';
import { useTheme } from '@/context/ThemeContext';
import '@excalidraw/excalidraw/index.css';

const ExcalidrawComponent = dynamic(
  async () => (await import('@excalidraw/excalidraw')).Excalidraw,
  { ssr: false },
);

interface ExcalidrawEditorProps {
  initialData?: {
    elements?: readonly any[];
    appState?: Record<string, any>;
    files?: Record<string, any>;
  };
  onChange?: (elements: readonly any[], appState: any, files: any) => void;
  excalidrawAPI?: (api: any) => void;
}

export default function ExcalidrawEditor({
  initialData,
  onChange,
  excalidrawAPI,
}: ExcalidrawEditorProps) {
  const { theme } = useTheme();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) {
    return (
      <div className="w-full h-full flex items-center justify-center bg-background">
        <div className="w-5 h-5 border-2 border-primary/30 border-t-primary rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="w-full h-full [&_.excalidraw]:h-full">
      <ExcalidrawComponent
        initialData={initialData}
        onChange={onChange}
        excalidrawAPI={excalidrawAPI}
        theme={theme === 'dark' ? 'dark' : 'light'}
        UIOptions={{
          canvasActions: {
            loadScene: false,
          },
        }}
      />
    </div>
  );
}
