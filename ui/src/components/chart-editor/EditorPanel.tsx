'use client';

import React from 'react';
import {
  Loader2, Search, Plus, Copy, Terminal, X,
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import Editor from '@monaco-editor/react';
import { registerIxCompletions } from '@/lib/monacoCompletions';
import type { TimeseriesLookupItem } from '@/hooks/useChartEditor';

interface EditorPanelProps {
  // Code state
  code: string;
  setCode: (v: string | ((prev: string) => string)) => void;
  codeEditorRef: React.MutableRefObject<any>;
  savedCursorPos: React.MutableRefObject<{ lineNumber: number; column: number } | null>;

  // Theme
  isLight: boolean;

  // Editor settings
  editorFontSize: number;
  editorFontFamily: string;
  isMounted: boolean;

  // Timeseries
  timeseriesSearch: string;
  setTimeseriesSearch: (v: string) => void;
  timeseriesQuery: string;
  setTimeseriesQuery: (v: string) => void;
  timeseriesMatches: TimeseriesLookupItem[];
  timeseriesLoading: boolean;
  runTimeseriesSearch: () => void;
  insertSeriesSnippet: (ts: TimeseriesLookupItem) => void;
  copySeriesSnippet: (ts: TimeseriesLookupItem) => void;

  // Console
  error: any;
  successMsg: string | null;
  consoleExpanded: boolean;
  setConsoleExpanded: (v: boolean | ((prev: boolean) => boolean)) => void;
  userManuallyCollapsed: boolean;
  setUserManuallyCollapsed: (v: boolean) => void;
}

export default function EditorPanel({
  code,
  setCode,
  codeEditorRef,
  savedCursorPos,
  isLight,
  editorFontSize,
  editorFontFamily,
  isMounted,
  timeseriesSearch,
  setTimeseriesSearch,
  timeseriesQuery,
  setTimeseriesQuery,
  timeseriesMatches,
  timeseriesLoading,
  runTimeseriesSearch,
  insertSeriesSnippet,
  copySeriesSnippet,
  error,
  successMsg,
  consoleExpanded,
  setConsoleExpanded,
  userManuallyCollapsed,
  setUserManuallyCollapsed,
}: EditorPanelProps) {
  return (
    <div className="h-full flex flex-col min-h-0 gap-2 p-2.5">
      {/* Timeseries Search */}
      <div className="shrink-0 rounded-[var(--radius)] border border-border/40 overflow-hidden bg-card">
        <div className="flex items-center gap-2 px-2.5 py-1.5">
          <div className="relative flex-1 min-w-0">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3 h-3 text-muted-foreground/30 pointer-events-none" />
            <input
              value={timeseriesSearch}
              onChange={(e) => setTimeseriesSearch(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); runTimeseriesSearch(); } }}
              placeholder="Search timeseries... (Enter)"
              className="w-full pl-7 pr-7 py-1.5 rounded-[var(--radius)] text-[11px] font-mono bg-background border border-border/40 text-foreground placeholder:text-muted-foreground/30 focus:outline-none focus:border-primary/40 focus:ring-1 focus:ring-primary/20 transition-colors"
            />
            {timeseriesSearch && (
              <button
                onClick={() => { setTimeseriesSearch(''); setTimeseriesQuery(''); }}
                className="absolute right-2 top-1/2 -translate-y-1/2 w-4 h-4 flex items-center justify-center rounded-full hover:bg-primary/10 text-muted-foreground/40 transition-colors"
              >
                <X className="w-2.5 h-2.5" />
              </button>
            )}
          </div>
          {timeseriesLoading && <Loader2 className="w-3 h-3 animate-spin text-primary/40 shrink-0" />}
        </div>

        {(timeseriesQuery.length > 0 || timeseriesMatches.length > 0) && (
          <div className="max-h-44 overflow-y-auto border-t border-border/30">
            {!timeseriesLoading && timeseriesQuery.length > 0 && timeseriesMatches.length === 0 && (
              <div className="px-3 py-3 text-center text-[11px] text-muted-foreground/40">
                No results for &ldquo;{timeseriesQuery}&rdquo;
              </div>
            )}
            {timeseriesMatches.map((ts) => (
              <div
                key={ts.id}
                className="group flex items-center gap-2 px-2.5 py-1.5 border-b border-border/20 last:border-b-0 hover:bg-primary/[0.04] transition-colors"
              >
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-1.5">
                    <span className="text-[11px] font-mono text-primary/70">{ts.code}</span>
                    {ts.frequency && (
                      <span className="stat-label">{ts.frequency}</span>
                    )}
                  </div>
                  {ts.name && ts.name !== ts.code && (
                    <div className="text-[10px] text-muted-foreground/40 truncate">{ts.name}</div>
                  )}
                </div>
                <div className="flex gap-0.5 shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">
                  <button
                    onClick={() => insertSeriesSnippet(ts)}
                    className="flex items-center gap-1 px-2 py-0.5 rounded-[var(--radius)] text-[10px] font-medium text-success/70 hover:text-success hover:bg-success/10 transition-colors"
                    title="Insert Series() into code"
                  >
                    <Plus className="w-3 h-3" />
                    Insert
                  </button>
                  <button
                    onClick={() => copySeriesSnippet(ts)}
                    className="w-6 h-6 flex items-center justify-center rounded-[var(--radius)] text-muted-foreground/40 hover:text-foreground hover:bg-primary/10 transition-colors"
                    title="Copy snippet"
                    aria-label="Copy snippet"
                  >
                    <Copy className="w-3 h-3" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Monaco Editor */}
      <div className="flex-grow relative overflow-hidden rounded-[var(--radius)] border border-border/40 bg-card">
        {isMounted ? (
          <Editor
            height="100%"
            language="python"
            value={code}
            onChange={(v) => setCode(v ?? '')}
            beforeMount={registerIxCompletions}
            onMount={(editor) => {
              codeEditorRef.current = editor;
              editor.onDidChangeCursorPosition((e: any) => {
                savedCursorPos.current = { lineNumber: e.position.lineNumber, column: e.position.column };
              });
            }}
            theme={isLight ? 'vs' : 'vs-dark'}
            options={{
              readOnly: false,
              fontSize: editorFontSize,
              fontFamily: editorFontFamily,
              minimap: { enabled: false },
              scrollBeyondLastLine: false,
              lineNumbers: 'on',
              wordWrap: 'on',
              padding: { top: 16, bottom: 16 },
              renderLineHighlight: 'none',
              contextmenu: true,
              quickSuggestions: true,
              suggestOnTriggerCharacters: true,
              parameterHints: { enabled: true },
              scrollbar: {
                verticalScrollbarSize: 4,
                horizontalScrollbarSize: 4,
                useShadows: false,
              },
            }}
          />
        ) : (
          <div className="h-full w-full flex items-center justify-center">
            <Loader2 className="w-4 h-4 animate-spin text-primary/30" />
          </div>
        )}
      </div>

      {/* Output / Console Panel */}
      {(error || successMsg) && (
        <div className={`shrink-0 rounded-[var(--radius)] border overflow-hidden ${error ? 'border-destructive/20 bg-destructive/[0.03]' : 'border-success/20 bg-success/[0.03]'}`}>
          <button
            onClick={() => { setConsoleExpanded(v => !v); setUserManuallyCollapsed(consoleExpanded); }}
            className="w-full flex items-center gap-2 px-3 py-1.5 text-left hover:bg-foreground/[0.02] transition-colors"
          >
            <Terminal className={`w-3 h-3 shrink-0 ${error ? 'text-destructive/50' : 'text-success/50'}`} />
            <span className="stat-label flex-1">Output</span>
            {error
              ? <span className="text-[10px] font-mono font-medium text-destructive">{typeof error === 'string' ? 'Error' : error.error || 'Error'}</span>
              : <span className="text-[10px] font-mono font-medium text-success">OK</span>
            }
            <span className="text-muted-foreground/25 text-[9px] ml-1">{consoleExpanded ? '▲' : '▼'}</span>
          </button>
          <AnimatePresence>
            {consoleExpanded && (
              <motion.div
                initial={{ height: 0 }}
                animate={{ height: 'auto' }}
                exit={{ height: 0 }}
                className="overflow-hidden"
              >
                <div className="px-3 py-2 font-mono text-[11px] leading-relaxed max-h-36 overflow-y-auto border-t border-border/20">
                  {error ? (
                    <pre className="text-destructive/80 whitespace-pre-wrap break-words">
                      {typeof error === 'string' ? error : error.message || JSON.stringify(error)}
                    </pre>
                  ) : (
                    <span className="text-success/80">{successMsg}</span>
                  )}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      )}
    </div>
  );
}
