'use client';

import React from 'react';
import { CheckCircle2 } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

interface PropertiesDrawerProps {
  showMeta: boolean;
  mode: 'standalone' | 'integrated';
  category: string;
  setCategory: (v: string) => void;
  tags: string;
  setTags: (v: string) => void;
  description: string;
  setDescription: (v: string) => void;
  createdByLabel: string;
  canEditCurrentChart: boolean;
  exportPdf: boolean;
  setExportPdf: (v: boolean) => void;
  canToggleExport: boolean;
  currentChartId: string | null;
  toggleExportPdf: (chartId: string, newValue: boolean) => Promise<void>;
}

export default function PropertiesDrawer({
  showMeta,
  mode,
  category,
  setCategory,
  tags,
  setTags,
  description,
  setDescription,
  createdByLabel,
  canEditCurrentChart,
  exportPdf,
  setExportPdf,
  canToggleExport,
  currentChartId,
  toggleExportPdf,
}: PropertiesDrawerProps) {
  return (
    <AnimatePresence>
      {showMeta && (
        <motion.div
          initial={{ height: 0, opacity: 0 }}
          animate={{ height: 'auto', opacity: 1 }}
          exit={{ height: 0, opacity: 0 }}
          className="shrink-0 bg-background border-b border-border/50 overflow-hidden z-10"
        >
          <div className="flex flex-col gap-2 px-4 py-2 max-w-7xl mx-auto">
            <div className="grid grid-cols-4 gap-2 items-start">
              <div className="col-span-1 min-w-0 space-y-1">
                <label className="text-[10px] text-muted-foreground mb-0.5 block">Category</label>
                <input
                  type="text"
                  value={category}
                  onChange={(e) => setCategory(e.target.value)}
                  readOnly={!canEditCurrentChart}
                  className="w-full border border-border/50 rounded-md px-2 py-1 text-[11px] bg-transparent focus:outline-none focus:border-border transition-all text-foreground placeholder:text-muted-foreground/40"
                  placeholder="ChartPack"
                />
              </div>

              <div className="col-span-1 min-w-0 space-y-1">
                <label className="text-[10px] text-muted-foreground mb-0.5 block">Tags</label>
                <input
                  type="text"
                  value={tags}
                  onChange={(e) => setTags(e.target.value)}
                  readOnly={!canEditCurrentChart}
                  className="w-full border border-border/50 rounded-md px-2 py-1 text-[11px] bg-transparent focus:outline-none focus:border-border transition-all text-foreground placeholder:text-muted-foreground/40"
                  placeholder="Volatility, Strategy..."
                />
              </div>

              <div className="col-span-1 min-w-0 space-y-1">
                <label className="text-[10px] text-muted-foreground mb-0.5 block">Created By</label>
                <input
                  type="text"
                  value={createdByLabel}
                  readOnly
                  className="w-full border border-border/50 rounded-md px-2 py-1 text-[11px] bg-transparent focus:outline-none focus:border-border transition-all text-foreground placeholder:text-muted-foreground/40"
                />
              </div>

              <div className="col-span-1 min-w-0 space-y-1">
                <label className="text-[10px] text-muted-foreground mb-0.5 block">Description</label>
                <input
                  type="text"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  readOnly={!canEditCurrentChart}
                  className="w-full border border-border/50 rounded-md px-2 py-1 text-[11px] bg-transparent focus:outline-none focus:border-border transition-all text-foreground placeholder:text-muted-foreground/40"
                  placeholder="Describe the protocol..."
                />
              </div>
            </div>

            {mode === 'standalone' && (
              <div className="flex items-center justify-between p-2 border border-border/50 rounded-lg">
                <div className="flex items-center gap-2">
                  <div className={`w-1.5 h-1.5 rounded-full ${exportPdf ? 'bg-success' : 'bg-muted-foreground/30'}`} />
                  <span className="text-[11px] text-muted-foreground">Publish to Report</span>
                </div>
                <button
                  onClick={() => currentChartId ? toggleExportPdf(currentChartId, !exportPdf) : setExportPdf(!exportPdf)}
                  disabled={!canToggleExport}
                  className={`flex items-center gap-1 px-2 py-1 rounded-md border transition-all text-[10px] font-medium ${exportPdf ? 'text-foreground border-border/50 bg-primary/[0.08]' : 'text-muted-foreground border-border/40 hover:border-border/50'}`}
                >
                  <CheckCircle2 className="w-2.5 h-2.5" />
                  {canToggleExport ? (exportPdf ? 'On' : 'Off') : 'Owner only'}
                </button>
              </div>
            )}
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
