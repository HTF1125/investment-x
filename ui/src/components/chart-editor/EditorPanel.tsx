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
    <div className="h-full flex flex-col min-h-0 gap-2 p-3">
      {/* Timeseries Search */}
      <div className="shrink-0 rounded-lg border border-border/50 overflow-hidden bg-background">
        <div className="flex items-center gap-2 px-3 py-2">
          <div className="relative flex-1 min-w-0">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3 h-3 text-muted-foreground/40" />
            <input
              value={timeseriesSearch}
              onChange={(e) => setTimeseriesSearch(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); runTimeseriesSearch(); } }}
              placeholder="Search timeseries... (Enter)"
              className="w-full pl-7 pr-7 py-1.5 rounded-md text-[11px] font-mono bg-transparent border border-border/50 text-foreground placeholder:text-muted-foreground/40 focus:outline-none focus:border-border transition-colors"
            />
            {timeseriesSearch && (
              <button
                onClick={() => { setTimeseriesSearch(''); setTimeseriesQuery(''); }}
                className="absolute right-2 top-1/2 -translate-y-1/2 p-0.5 rounded-full hover:bg-primary/10 text-muted-foreground/40"
              >
                <X className="w-2.5 h-2.5" />
              </button>
            )}
          </div>
          {timeseriesLoading && <Loader2 className="w-3.5 h-3.5 animate-spin text-muted-foreground/50 shrink-0" />}
        </div>

        {(timeseriesQuery.length > 0 || timeseriesMatches.length > 0) && (
          <div className="max-h-44 overflow-y-auto border-t border-border/50">
            {!timeseriesLoading && timeseriesQuery.length > 0 && timeseriesMatches.length === 0 && (
              <div className="px-3 py-3 text-center text-[11px] text-muted-foreground/50">
                No results for &ldquo;{timeseriesQuery}&rdquo;
              </div>
            )}
            {timeseriesMatches.map((ts) => (
              <div
                key={ts.id}
                className="group flex items-center gap-2.5 px-3 py-1.5 border-b border-border/25 last:border-b-0 hover:bg-primary/[0.04] transition-colors"
              >
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-1.5">
                    <span className="text-[11px] font-mono text-primary/80">{ts.code}</span>
                    {ts.frequency && <span className="text-[9px] text-muted-foreground/40">{ts.frequency}</span>}
                  </div>
                  {ts.name && ts.name !== ts.code && (
                    <div className="text-[10px] text-muted-foreground/50 truncate">{ts.name}</div>
                  )}
                </div>
                <div className="flex gap-1 shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">
                  <button
                    onClick={() => insertSeriesSnippet(ts)}
                    className="flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-medium text-emerald-500/80 hover:text-emerald-400 hover:bg-emerald-500/10 transition-colors"
                    title="Insert Series() into code"
                  >
                    <Plus className="w-3 h-3" />
                    Insert
                  </button>
                  <button
                    onClick={() => copySeriesSnippet(ts)}
                    className="flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-medium text-muted-foreground/60 hover:text-foreground hover:bg-primary/10 transition-colors"
                    title="Copy snippet"
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
      <div className="flex-grow relative overflow-hidden rounded-lg border border-border/50 bg-background">
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
            <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
          </div>
        )}
      </div>

      {/* Output / Console Panel */}
      {(error || successMsg) && (
        <div className="shrink-0 rounded-lg border border-border/50 overflow-hidden bg-background">
          <button
            onClick={() => { setConsoleExpanded(v => !v); setUserManuallyCollapsed(consoleExpanded); }}
            className="w-full flex items-center gap-2 px-3 py-2 border-b border-border/50 text-left"
          >
            <Terminal className="w-3 h-3 text-muted-foreground/50 shrink-0" />
            <span className="text-[10px] font-medium text-muted-foreground/60 uppercase tracking-wider flex-1">Output</span>
            {error
              ? <span className="text-[10px] font-medium text-rose-500">{typeof error === 'string' ? 'Error' : error.error || 'Error'}</span>
              : <span className="text-[10px] font-medium text-emerald-500">OK</span>
            }
            <span className="text-muted-foreground/30 text-[10px]">{consoleExpanded ? '\u25B2' : '\u25BC'}</span>
          </button>
          <AnimatePresence>
            {consoleExpanded && (
              <motion.div
                initial={{ height: 0 }}
                animate={{ height: 'auto' }}
                exit={{ height: 0 }}
                className="overflow-hidden"
              >
                <div className="px-3 py-2.5 font-mono text-[11px] leading-relaxed max-h-40 overflow-y-auto">
                  {error ? (
                    <pre className="text-rose-400 whitespace-pre-wrap break-words">
                      {typeof error === 'string' ? error : error.message || JSON.stringify(error)}
                    </pre>
                  ) : (
                    <span className="text-emerald-500">{successMsg}</span>
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
