'use client';

import React, { useState, useEffect } from 'react';
import dynamic from 'next/dynamic';
import { useAuth } from '@/context/AuthContext';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Loader2, Play, Save, Code, Tag, FileText, Pencil, GripVertical, Download } from 'lucide-react';
import { Reorder } from 'framer-motion';
import Editor from '@monaco-editor/react';

// Dynamic import for Plotly to avoid SSR issues
const Plot = dynamic(() => import('react-plotly.js'), {
  ssr: false,
  loading: () => (
    <div className="flex items-center justify-center h-[400px] w-full bg-white/5 rounded-xl animate-pulse">
      <Loader2 className="w-8 h-8 text-sky-500 animate-spin" />
    </div>
  ),
});

export default function CustomChartEditor() {
  const { token } = useAuth();
  const queryClient = useQueryClient();
  
  // State (Editor)
  const [code, setCode] = useState<string>(`# Define your chart logic here
# Available: pd, px, df_plot(df, kind='line', ...)
# MUST define a variable 'fig' at the end

import pandas as pd
import plotly.express as px

data = {
    'Year': [2020, 2021, 2022, 2023],
    'Value': [100, 120, 110, 135]
}
df = pd.DataFrame(data)

# Create figure
fig = px.bar(df, x='Year', y='Value', title='New Analysis')
`);
  const [name, setName] = useState('Untitled Analysis');
  const [category, setCategory] = useState('Personal');
  const [description, setDescription] = useState('');
  const [tags, setTags] = useState('');
  const [currentChartId, setCurrentChartId] = useState<string | null>(null);
  
  const [previewFigure, setPreviewFigure] = useState<any>(null);
  const [previewError, setPreviewError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  
  // Local state for reordering
  const [orderedCharts, setOrderedCharts] = useState<any[]>([]);
  const [isLoaded, setIsLoaded] = useState(false);
  const [exporting, setExporting] = useState(false);

  // Fetch Saved Charts
  const { data: savedCharts = [] } = useQuery({
    queryKey: ['custom-charts'],
    queryFn: async () => {
      const res = await fetch('/api/custom', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (!res.ok) throw new Error('Failed to load charts');
      return res.json();
    },
    enabled: !!token,
  });

  // Sync savedCharts to orderedCharts initially
  useEffect(() => {
    if (savedCharts.length > 0 && !isLoaded) {
        setOrderedCharts(savedCharts);
        setIsLoaded(true);
    } else if (savedCharts.length > 0 && savedCharts.length !== orderedCharts.length) {
        setOrderedCharts(savedCharts);
    }
  }, [savedCharts, isLoaded, orderedCharts.length]);

  // Reorder Mutation
  const reorderMutation = useMutation({
    mutationFn: async (items: any[]) => {
        const payload = { items: items.map(c => ({ id: c.id })) };
        const res = await fetch('/api/custom/reorder', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
            body: JSON.stringify(payload)
        });
        if (!res.ok) throw new Error('Failed to save order');
        return res.json();
    }
  });

  // Debounced Auto-Save for Reordering
  useEffect(() => {
    if (orderedCharts.length === 0 || !isLoaded) return;
    
    const timer = setTimeout(() => {
       reorderMutation.mutate(orderedCharts);
    }, 1500);
    
    return () => clearTimeout(timer);
  }, [orderedCharts, isLoaded]);

  // Preview Mutation
  const previewMutation = useMutation({
    mutationFn: async () => {
        const res = await fetch('/api/custom/preview', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
            body: JSON.stringify({ code })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Failed to preview');
        return data;
    },
    onSuccess: (data) => {
        setPreviewFigure(data);
        setPreviewError(null);
    },
    onError: (err: any) => setPreviewError(err.message),
  });

  // Save Mutation
  const saveMutation = useMutation({
    mutationFn: async () => {
        const tagList = tags.split(',').map(t => t.trim()).filter(Boolean);
        const payload = { name, code, category, description, tags: tagList };
        const url = currentChartId ? `/api/custom/${currentChartId}` : '/api/custom';
        const method = currentChartId ? 'PUT' : 'POST';

        const res = await fetch(url, {
            method,
            headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Save failed');
        return { data, method }; 
    },
    onSuccess: ({ data, method }) => {
        if (method === 'POST') setCurrentChartId(data.id);
        setSuccessMsg(method === 'POST' ? 'Analysis created successfully!' : 'Analysis updated successfully!');
        queryClient.invalidateQueries({ queryKey: ['custom-charts'] });
        if (!previewFigure) previewMutation.mutate();
    },
    onError: (err: any) => setPreviewError(err.message),
  });

  // Handlers
  const handlePreview = () => {
      setSuccessMsg(null);
      previewMutation.mutate();
  };

  const handleSave = () => {
      setSuccessMsg(null);
      setPreviewError(null);
      saveMutation.mutate();
  };
  
  const handleExportPDF = async () => {
    setExporting(true);
    setSuccessMsg(null);
    setPreviewError(null);
    try {
        const payload = { items: orderedCharts.map(c => c.id) };
        const res = await fetch('/api/custom/pdf', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
            body: JSON.stringify(payload)
        });
        if (!res.ok) throw new Error('Failed to generate PDF');
        
        // Handle Blob
        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `InvestmentX_Report_${new Date().toISOString().slice(0,10)}.pdf`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        setSuccessMsg("PDF Report downloaded successfully.");
    } catch (err: any) {
        setPreviewError(err.message);
    } finally {
        setExporting(false);
    }
  };
  
  const loadChart = (chart: any) => {
      setCurrentChartId(chart.id);
      setName(chart.name || 'Untitled Analysis');
      setCode(chart.code);
      setCategory(chart.category || 'Personal');
      setDescription(chart.description || '');
      setTags(chart.tags ? chart.tags.join(', ') : '');
      if (chart.figure) {
          setPreviewFigure(chart.figure);
      } else {
          setPreviewFigure(null);
      }
      setSuccessMsg(`Loaded "${chart.name || 'Untitled'}" analysis.`);
      setPreviewError(null);
  };

  const clearEditor = () => {
    setCurrentChartId(null);
    setName('Untitled Analysis');
    setCode(`# Define your chart logic here
# Available: pd, px, df_plot(df, kind='line', ...)
# MUST define a variable 'fig' at the end

import pandas as pd
import plotly.express as px

data = {
    'Year': [2020, 2021, 2022, 2023],
    'Value': [100, 120, 110, 135]
}
df = pd.DataFrame(data)

# Create figure
fig = px.bar(df, x='Year', y='Value', title='New Analysis')
`);
    setCategory('Personal');
    setDescription('');
    setTags('');
    setPreviewFigure(null);
    setSuccessMsg('Started new analysis.');
    setPreviewError(null);
  };
  
  const loading = previewMutation.isPending; 
  const saving = saveMutation.isPending;     
  const error = previewError || (saveMutation.isError ? saveMutation.error?.message : null) || null;

  return (
    <div className="grid grid-cols-1 lg:grid-cols-[55%_45%] gap-8 h-full">
      {/* Left Column: Preview & Library (Swapped & Resized) */}
      <div className="flex flex-col gap-6 h-full order-1 lg:order-1 min-w-0">
          {/* Preview Panel */}
          <div className="flex flex-col bg-white/[0.02] rounded-2xl border border-white/5 overflow-hidden min-h-[500px]">
             <div className="p-4 border-b border-white/5 font-medium text-slate-400 flex items-center justify-between">
                 <span>Result Preview</span>
                 {previewFigure && <span className="text-xs px-2 py-0.5 bg-emerald-500/20 text-emerald-400 rounded">Rendered</span>}
             </div>
             
             <div className="flex-grow relative p-4 bg-black/20">
             {previewFigure ? (
                 <Plot
                     data={previewFigure.data}
                     layout={{
                         ...previewFigure.layout,
                         autosize: true,
                         width: undefined,
                         height: undefined,
                         paper_bgcolor: 'rgba(0,0,0,0)',
                         plot_bgcolor: 'rgba(0,0,0,0)',
                         font: { color: '#94a3b8' }
                     }}
                     config={{ responsive: true, displayModeBar: 'hover' }}
                     style={{ width: '100%', height: '100%' }}
                     useResizeHandler={true}
                 />
             ) : (
                 <div className="absolute inset-0 flex flex-col items-center justify-center text-slate-600">
                     <Play className="w-12 h-12 mb-4 opacity-20" />
                     <p>Run code to generate preview</p>
                 </div>
             )}
             </div>
           </div>

           {/* Library Panel with Drag and Drop */}
           <div className="flex flex-col bg-white/[0.02] rounded-2xl border border-white/5 overflow-hidden flex-grow max-h-[300px]">
              <div className="p-4 border-b border-white/5 font-medium text-slate-400 flex items-center justify-between">
                 <div className="flex items-center gap-2">
                     <Save className="w-4 h-4" /> Saved Analyses
                 </div>
                 <button 
                    onClick={handleExportPDF}
                    disabled={exporting || orderedCharts.length === 0}
                    className="flex items-center gap-1.5 px-3 py-1 bg-white/5 hover:bg-sky-500/20 text-xs text-slate-400 hover:text-sky-400 border border-white/5 hover:border-sky-500/30 rounded-full transition-all disabled:opacity-50"
                 >
                    {exporting ? <Loader2 className="w-3 h-3 animate-spin" /> : <Download className="w-3 h-3" />}
                    {exporting ? 'Generating...' : 'Export PDF'}
                 </button>
              </div>
              <div className="overflow-y-auto p-2 no-scrollbar">
                 {orderedCharts.length === 0 ? (
                     <div className="text-center py-8 text-slate-600 text-sm">No saved charts yet.</div>
                 ) : (
                     <Reorder.Group 
                        axis="y" 
                        values={orderedCharts} 
                        onReorder={setOrderedCharts}
                        className="space-y-2"
                     >
                         {orderedCharts.map((chart: any) => (
                             <Reorder.Item 
                                key={chart.id} 
                                value={chart}
                                className={`p-3 rounded-lg border cursor-pointer flex justify-between items-center group transition-colors relative select-none ${
                                    currentChartId === chart.id 
                                    ? 'bg-indigo-500/10 border-indigo-500/30' 
                                    : 'bg-white/5 hover:bg-white/10 border-white/5'
                                }`}
                             >
                                 <div className="flex items-center gap-3 flex-grow min-w-0" onClick={() => loadChart(chart)}>
                                     <GripVertical className="w-4 h-4 text-slate-600 cursor-grab active:cursor-grabbing" />
                                     <div className="min-w-0">
                                         <div className={`text-sm font-medium truncate ${currentChartId === chart.id ? 'text-indigo-400' : 'text-slate-200'}`}>
                                             {chart.name || chart.category || 'Untitled'}
                                         </div>
                                         {chart.name && (
                                             <div className="text-xs text-slate-500 truncate">{chart.category}</div>
                                         )}
                                     </div>
                                 </div>
                                 <div className="text-[10px] text-slate-600 font-mono group-hover:text-slate-400" onClick={() => loadChart(chart)}>
                                     {new Date(chart.updated_at || Date.now()).toLocaleDateString()}
                                 </div>
                             </Reorder.Item>
                         ))}
                     </Reorder.Group>
                 )}
              </div>
           </div>
      </div>

      {/* Right Column: Editor & Metadata (Swapped) */}
      <div className="flex flex-col gap-6 h-full order-2 lg:order-2 min-w-0">
        
        {/* Toolbar */}
        <div className="flex justify-between items-center pb-2 border-b border-white/5">
             <div className="flex items-center gap-2 flex-grow mr-4">
                <Pencil className="w-4 h-4 text-slate-500" />
                <input 
                    type="text" 
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    className="bg-transparent text-slate-200 font-semibold focus:outline-none focus:border-b border-sky-500/50 w-full"
                    placeholder="Untitled Analysis"
                />
             </div>
             <button 
                onClick={clearEditor}
                className="text-xs px-3 py-1 bg-white/5 hover:bg-white/10 rounded-full text-slate-400 transition-colors whitespace-nowrap"
             >
                + New Analysis
             </button>
        </div>

        {/* Code Editor (Monaco) */}
        <div className="flex flex-col gap-2 flex-grow min-h-[300px]">
          <div className="relative flex-grow border border-white/10 rounded-xl overflow-hidden bg-[#1e1e1e]">
             <Editor
                height="100%"
                defaultLanguage="python"
                value={code}
                theme="vs-dark"
                onChange={(value) => setCode(value || "")}
                loading={<div className="flex items-center justify-center h-full text-slate-500 gap-2"><Loader2 className="animate-spin w-5 h-5" /> Loading IDE...</div>}
                options={{
                    minimap: { enabled: false },
                    fontSize: 13,
                    lineNumbers: 'on',
                    roundedSelection: false,
                    scrollBeyondLastLine: false,
                    readOnly: false,
                    automaticLayout: true,
                    padding: { top: 16, bottom: 16 },
                    fontFamily: 'JetBrains Mono, monospace',
                }}
             />
          </div>
          <p className="text-xs text-slate-500">
            Environment includes: <code>pandas (pd)</code>, <code>plotly.express (px)</code>, <code>df_plot</code> helper.
          </p>
        </div>

        {/* Metadata Controls */}
        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-2">
            <label className="text-xs text-slate-400 font-medium">Category</label>
            <input 
              type="text" 
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-slate-200 focus:ring-1 focus:ring-sky-500/50 outline-none"
              placeholder="e.g. Personal"
            />
          </div>
          <div className="space-y-2">
            <label className="text-xs text-slate-400 font-medium flex items-center gap-1">
              <Tag className="w-3 h-3" /> Tags
            </label>
            <input 
              type="text" 
              value={tags}
              onChange={(e) => setTags(e.target.value)}
              className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-slate-200 focus:ring-1 focus:ring-sky-500/50 outline-none"
              placeholder="comma, separated"
            />
          </div>
        </div>
        
        <div className="space-y-2">
            <label className="text-xs text-slate-400 font-medium flex items-center gap-1">
              <FileText className="w-3 h-3" /> Description
            </label>
            <textarea 
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-slate-200 focus:ring-1 focus:ring-sky-500/50 outline-none h-16 resize-none"
              placeholder="Describe your analysis..."
            />
        </div>

        {/* Action Buttons */}
        <div className="flex gap-4 pt-2">
          <button
            onClick={handlePreview}
            disabled={loading}
            className="flex-1 py-3 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl font-medium transition-all flex items-center justify-center gap-2 disabled:opacity-50"
          >
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
            Run Logic
          </button>
          
          <button
            onClick={handleSave}
            disabled={saving}
            className="flex-1 py-3 bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl font-medium transition-all flex items-center justify-center gap-2 disabled:opacity-50"
          >
            {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
            {currentChartId ? 'Update Analysis' : 'Save Analysis'}
          </button>
        </div>
        
        {/* Status Messages */}
        {error && (
            <div className="p-4 bg-rose-500/10 border border-rose-500/20 rounded-xl text-rose-400 text-xs font-mono whitespace-pre-wrap">
                ERROR: {String(error)}
            </div>
        )}
        {successMsg && (
            <div className="p-4 bg-emerald-500/10 border border-emerald-500/20 rounded-xl text-emerald-400 text-sm font-medium">
                {successMsg}
            </div>
        )}

      </div>
    </div>
  );
}
