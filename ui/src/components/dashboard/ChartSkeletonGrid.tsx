'use client';

import React from 'react';

export default function ChartSkeletonGrid() {
  return (
    <div className="p-3 sm:p-4 lg:p-5">
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
        {[...Array(8)].map((_, i) => (
          <div
            key={i}
            className="panel-card overflow-hidden animate-pulse"
            style={{ animationDelay: `${i * 80}ms` }}
          >
            <div className="h-[190px] bg-background/50 p-3 flex flex-col justify-end gap-2">
              <div className="h-px w-full bg-border/10" />
              <div className="flex gap-3">
                <div className="h-[2px] flex-1 bg-primary/[0.04] rounded-full" />
                <div className="h-[2px] flex-1 bg-primary/[0.06] rounded-full" />
                <div className="h-[2px] w-1/3 bg-primary/[0.03] rounded-full" />
              </div>
            </div>
            <div className="px-3 py-2.5 border-t border-border/15 flex items-center gap-2">
              <div className="h-2.5 w-28 bg-primary/[0.06] rounded" />
              <div className="h-2 w-12 bg-primary/[0.03] rounded ml-auto" />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
