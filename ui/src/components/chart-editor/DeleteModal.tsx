'use client';

import React from 'react';
import { Trash2 } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

interface DeleteModalProps {
  deleteConfirm: string | null;
  setDeleteConfirm: (v: string | null) => void;
  deleteMutation: {
    mutate: (chartId: string) => void;
    isPending: boolean;
  };
}

export default function DeleteModal({
  deleteConfirm,
  setDeleteConfirm,
  deleteMutation,
}: DeleteModalProps) {
  return (
    <AnimatePresence>
      {deleteConfirm && (
        <div className="fixed inset-0 z-[110] flex items-center justify-center p-4">
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setDeleteConfirm(null)}
            className="absolute inset-0 bg-foreground/40 dark:bg-black/70 backdrop-blur-md"
          />
          <motion.div
            initial={{ scale: 0.9, opacity: 0, y: 20 }}
            animate={{ scale: 1, opacity: 1, y: 0 }}
            exit={{ scale: 0.9, opacity: 0, y: 20 }}
            className="relative w-full max-w-sm bg-background border border-border/60 rounded-xl shadow-xl p-6"
          >
            <div className="flex items-center gap-4 mb-6">
              <div className="w-10 h-10 rounded-lg bg-rose-500/[0.08] flex items-center justify-center text-rose-500">
                <Trash2 className="w-6 h-6" />
              </div>
              <div>
                <h3 className="text-lg font-bold text-foreground">Delete Analysis?</h3>
                <p className="text-xs text-muted-foreground mt-1">This action is permanent and cannot be undone.</p>
              </div>
            </div>

            <div className="flex gap-3">
              <button
                onClick={() => setDeleteConfirm(null)}
                className="flex-1 px-4 py-2.5 border border-border/60 text-muted-foreground text-[12px] font-medium rounded-lg hover:text-foreground transition-all"
              >
                Cancel
              </button>
              <button
                onClick={() => deleteConfirm && deleteMutation.mutate(deleteConfirm)}
                disabled={deleteMutation.isPending}
                className="flex-1 px-4 py-2.5 bg-foreground text-background text-[12px] font-medium rounded-lg hover:opacity-80 transition-opacity disabled:opacity-50"
              >
                {deleteMutation.isPending ? 'Deleting...' : 'Confirm Delete'}
              </button>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}
