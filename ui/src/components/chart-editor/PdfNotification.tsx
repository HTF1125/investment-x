'use client';

import React from 'react';
import { Loader2, AlertCircle, CheckCircle2 } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import type { PdfStatus } from '@/hooks/useChartEditor';

interface PdfNotificationProps {
  pdfStatus: PdfStatus;
  pdfCount: number;
}

export default function PdfNotification({ pdfStatus, pdfCount }: PdfNotificationProps) {
  return (
    <AnimatePresence>
      {pdfStatus !== 'idle' && (
        <motion.div
          initial={{ opacity: 0, y: 50, scale: 0.95 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, scale: 0.95 }}
          className="fixed bottom-6 right-6 z-[100] flex items-center gap-3 px-4 py-3 bg-background border border-border/50 rounded-lg shadow-md"
        >
          <div className="text-muted-foreground">
            {pdfStatus === 'exporting' ? <Loader2 className="w-5 h-5 animate-spin" /> : pdfStatus === 'complete' ? <CheckCircle2 className="w-5 h-5" /> : <AlertCircle className="w-5 h-5" />}
          </div>
          <div className="flex flex-col">
            <span className="text-[13px] font-medium text-foreground">
              {pdfStatus === 'exporting' ? 'Generating PDF...' : pdfStatus === 'complete' ? 'Report ready' : 'Export failed'}
            </span>
            <span className="text-[11px] text-muted-foreground mt-0.5">
              {pdfStatus === 'exporting' ? `${pdfCount} charts` : pdfStatus === 'complete' ? 'Download started' : 'Try again'}
            </span>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
