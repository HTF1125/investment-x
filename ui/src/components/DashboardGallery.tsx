'use client';

import React, { useState, useMemo, useEffect } from 'react';
import { TrendingUp, Search, Layers, Grid, List as ListIcon, X, LayoutGrid } from 'lucide-react';
import Chart from './Chart';

interface ChartMeta {
  code: string;
  category: string | null;
  description: string | null;
  updated_at: string | null;
}

interface DashboardGalleryProps {
  categories: string[];
  chartsByCategory: Record<string, ChartMeta[]>;
}

export default function DashboardGallery({ categories, chartsByCategory }: DashboardGalleryProps) {
  // Add 'All' as a virtual category
  const allCategories = useMemo(() => ['All Indicators', ...(categories || [])], [categories]);
  
  const [activeCategory, setActiveCategory] = useState<string>(allCategories[0]);
  const [searchQuery, setSearchQuery] = useState('');
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  // Ensure active category is valid when categories change
  useEffect(() => {
    if (activeCategory === 'All Indicators') return;
    if (!allCategories.includes(activeCategory)) {
        setActiveCategory(allCategories[0]);
    }
  }, [allCategories, activeCategory]);

  // Filter charts based on search and/or category
  const filteredCharts = useMemo(() => {
    let result: ChartMeta[] = [];
    
    if (searchQuery.trim()) {
      // Search across ALL categories
      Object.values(chartsByCategory || {}).forEach(charts => {
        if (Array.isArray(charts)) {
          result.push(...charts.filter(c => 
            (c.code || '').toLowerCase().includes(searchQuery.toLowerCase()) || 
            (c.description?.toLowerCase().includes(searchQuery.toLowerCase()))
          ));
        }
      });
      // Deduplicate
      result = Array.from(new Map(result.map(item => [item.code, item])).values());
    } else if (activeCategory === 'All Indicators') {
      Object.values(chartsByCategory || {}).forEach(charts => {
        if (Array.isArray(charts)) result.push(...charts);
      });
    } else {
      result = (chartsByCategory || {})[activeCategory] || [];
    }
    
    return result.sort((a, b) => (a.code || '').localeCompare(b.code || ''));
  }, [activeCategory, searchQuery, chartsByCategory]);

  // Pagination state to prevent Thundering Herd
  const INITIAL_LOAD_COUNT = 12;
  const LOAD_MORE_INCREMENT = 12;
  const [visibleCount, setVisibleCount] = useState(INITIAL_LOAD_COUNT);

  // Reset visible count when filters change
  useEffect(() => {
    setVisibleCount(INITIAL_LOAD_COUNT);
  }, [activeCategory, searchQuery]);

  const loadMore = () => {
    setVisibleCount(prev => prev + LOAD_MORE_INCREMENT);
  };

  if (!mounted) {
    return <div className="min-h-[800px] flex items-center justify-center text-slate-500 font-mono">Initializing Research Engine...</div>;
  }

  return (
    <div className="space-y-8 min-h-[800px]">
      {/* 🧭 Filter & Search Command Bar */}
      <div className="flex flex-col lg:flex-row gap-6 items-center justify-between sticky top-6 z-40 px-6 py-4 glass-card bg-slate-900/60 backdrop-blur-2xl border-white/10 shadow-2xl">
        <div className="flex flex-wrap items-center gap-2 pb-2 lg:pb-0 w-full lg:w-[75%]">
          {!searchQuery && (
            <div className="flex flex-wrap gap-2">
              {allCategories.map((cat) => (
                <button
                  key={cat}
                  onClick={() => setActiveCategory(cat)}
                  className={`px-4 py-1.5 text-xs font-semibold rounded-full transition-all border ${
                    activeCategory === cat 
                      ? 'bg-sky-500 border-sky-400 text-white shadow-lg shadow-sky-500/20' 
                      : 'bg-white/5 border-white/5 text-slate-400 hover:bg-white/10 hover:text-slate-200'
                  }`}
                >
                  {cat}
                </button>
              ))}
            </div>
          )}
          {searchQuery && (
            <div className="flex items-center gap-2 text-sky-400 text-xs font-semibold px-4 py-1.5 bg-sky-500/10 rounded-full border border-sky-500/20">
              <Layers className="w-4 h-4" />
              Intelligence Search: Global Scope ({Object.values(chartsByCategory || {}).flat().length} indicators)
            </div>
          )}
        </div>

        <div className="flex items-center gap-3 w-full lg:w-auto">
          <div className="relative flex-grow lg:w-80">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
            <input 
              type="text"
              placeholder="Filter by code or analysis keyword..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-10 py-2.5 bg-black/40 border border-white/10 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-sky-500/50 transition-all font-light"
            />
            {searchQuery && (
              <button 
                onClick={() => setSearchQuery('')}
                className="absolute right-3 top-1/2 -translate-y-1/2 p-1 hover:bg-white/10 rounded-md transition-colors"
                type="button"
              >
                <X className="w-3 h-3 text-slate-400" />
              </button>
            )}
          </div>
          
          <div className="flex gap-1 p-1 bg-black/40 border border-white/5 rounded-xl">
            <button 
              onClick={() => setViewMode('grid')}
              className={`p-2 rounded-lg transition-all ${viewMode === 'grid' ? 'bg-sky-500/20 text-sky-400 border border-sky-500/20' : 'text-slate-500 hover:text-slate-300'}`}
              title="Grid View"
              type="button"
            >
              <LayoutGrid className="w-4 h-4" />
            </button>
            <button 
              onClick={() => setViewMode('list')}
              className={`p-2 rounded-lg transition-all ${viewMode === 'list' ? 'bg-sky-500/20 text-sky-400 border border-sky-500/20' : 'text-slate-500 hover:text-slate-300'}`}
              title="List View"
              type="button"
            >
              <ListIcon className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* 📊 Results Header */}
      <div className="flex items-center justify-between px-2">
        <h2 className="text-2xl font-semibold text-slate-200 flex items-center gap-3 tracking-tight">
          {searchQuery ? (
            <>Internal Discovery <span className="text-sky-500 font-mono text-lg">[{filteredCharts.length}]</span></>
          ) : (
            <>
              <TrendingUp className="w-6 h-6 text-sky-400" />
              {activeCategory}
              <span className="text-xs font-mono font-normal text-slate-500 mt-1.5 uppercase tracking-widest">
                / {filteredCharts.length} Indices
              </span>
            </>
          )}
        </h2>
      </div>

      {/* 🖼️ Grid/List Display */}
      <div 
        className={`grid gap-8 ${viewMode === 'grid' ? 'grid-cols-1 xl:grid-cols-2' : 'grid-cols-1'}`}
      >
        {filteredCharts.slice(0, visibleCount).map((chart) => (
          <div
            key={chart.code}
            className={`glass-card overflow-hidden flex flex-col group ${viewMode === 'list' ? 'min-h-[200px]' : ''}`}
          >
            {/* Card Header */}
            <div className="px-6 py-4 flex items-center justify-between border-b border-white/5 bg-white/[0.02]">
               <div className="flex items-center gap-3">
                 <span className="text-xs font-mono text-sky-400 uppercase tracking-widest px-2.5 py-1 bg-sky-500/10 rounded border border-sky-500/10">
                   {chart.code.split('(')[0].trim()}
                 </span>
                 {viewMode === 'list' && (
                   <span className="text-sm font-medium text-slate-300">{chart.category}</span>
                 )}
               </div>
               <div className="text-[10px] text-slate-500 font-mono flex items-center gap-2">
                 <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                 {chart.updated_at ? new Date(chart.updated_at).toLocaleTimeString() : '---'}
               </div>
            </div>

            <div className={`flex ${viewMode === 'list' ? 'flex-row items-center gap-8' : 'flex-col'}`}>
              {/* Chart Area */}
              <div className={`p-4 bg-slate-950/20 relative ${viewMode === 'list' ? 'w-1/3' : 'w-full'}`}>
                <Chart code={chart.code} />
              </div>

              {/* Card Analysis */}
              <div className={`px-6 py-5 bg-black/20 border-t border-white/5 transition-colors ${viewMode === 'list' ? 'border-t-0 border-l w-2/3 h-full flex flex-col justify-center' : ''}`}>
                <p className="text-sm text-slate-400 leading-relaxed font-light line-clamp-2">
                  {chart.description || "Intelligence analysis data stream currently aggregating for this indicator."}
                </p>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Load More Button */}
      {visibleCount < filteredCharts.length && (
          <div className="flex justify-center pt-8">
              <button 
                  onClick={loadMore}
                  className="px-8 py-3 bg-white/5 hover:bg-white/10 border border-white/10 rounded-full text-sm font-medium text-slate-300 transition-all flex items-center gap-2"
              >
                  Load More Indices ({filteredCharts.length - visibleCount} remaining)
                  <Layers className="w-4 h-4" />
              </button>
          </div>
      )}

      {/* 📭 Empty State */}
      {filteredCharts.length === 0 && (
        <div className="py-32 text-center glass-card border-dashed border-white/10 bg-transparent">
          <Layers className="w-12 h-12 text-slate-700 mx-auto mb-4 opacity-20" />
          <h3 className="text-xl font-medium text-slate-500">No matching indicators</h3>
          <p className="text-slate-600 mt-2 text-sm font-light">Try expanding your search parameters.</p>
        </div>
      )}
    </div>
  );
}
