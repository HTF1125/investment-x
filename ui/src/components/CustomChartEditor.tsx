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
}) as any;

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
  const [graphDiv, setGraphDiv] = useState<HTMLElement | null>(null);
  const [copying, setCopying] = useState(false);

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

  const handleCopyChart = async () => {
    if (!graphDiv || copying) return;
    setCopying(true);
    try {
        const Plotly = (await import('plotly.js-dist-min')).default;
        const url = await Plotly.toImage(graphDiv as any, { format: 'png', width: 1200, height: 800, scale: 2 });
        
        const res = await fetch(url);
        const blob = await res.blob();
        
        await navigator.clipboard.write([
            new ClipboardItem({ 'image/png': blob })
        ]);
        
        setSuccessMsg('Chart copied to clipboard!');
        setTimeout(() => setCopying(false), 1000);
    } catch (err) {
        setPreviewError('Failed to copy chart: ' + String(err));
        setCopying(false);
    }
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
    <div className="flex flex-col lg:flex-row h-auto lg:h-full gap-6 pb-20 lg:pb-0">
      
      {/* Column 1: Library (Sidebar) */}
      <div className="w-full lg:w-[220px] h-[300px] lg:h-auto flex flex-col shrink-0 bg-slate-900/40 backdrop-blur-md rounded-2xl border border-white/10 overflow-hidden shadow-xl order-3 lg:order-1">
          <div className="p-4 border-b border-white/10 bg-white/5 flex justify-between items-center">
              <h3 className="font-semibold text-slate-200 flex items-center gap-2">
                  <Save className="w-4 h-4 text-indigo-400" /> Library
              </h3>
              <button 
                  onClick={clearEditor}
                  className="p-1.5 hover:bg-white/10 rounded-lg text-slate-400 hover:text-white transition-colors"
                  title="New Analysis"
              >
                  <Pencil className="w-4 h-4" />
              </button>
          </div>
          
          <div className="flex-grow overflow-y-auto p-2 space-y-1 custom-scrollbar">
              {orderedCharts.length === 0 ? (
                  <div className="text-center py-10 text-slate-600 text-sm">No saved items.</div>
              ) : (
                <Reorder.Group axis="y" values={orderedCharts} onReorder={setOrderedCharts} className="space-y-2">
                  {orderedCharts.map((chart: any) => (
                      <Reorder.Item 
                          key={chart.id} 
                          value={chart}
                          className={`p-2 rounded-lg border cursor-pointer group transition-all duration-200 select-none ${
                              currentChartId === chart.id 
                              ? 'bg-indigo-500/20 border-indigo-500/40 shadow-lg shadow-indigo-900/20' 
                              : 'bg-white/[0.02] hover:bg-white/[0.05] border-transparent hover:border-white/5'
                          }`}
                      >
                          <div className="flex items-center gap-3" onClick={() => loadChart(chart)}>
                             <div className={`p-2 rounded-lg ${currentChartId === chart.id ? 'bg-indigo-500/20 text-indigo-300' : 'bg-white/5 text-slate-500'}`}>
                                <FileText className="w-4 h-4" />
                             </div>
                             <div className="min-w-0 flex-grow">
                                 <div className={`text-sm font-medium truncate ${currentChartId === chart.id ? 'text-indigo-200' : 'text-slate-300'}`}>
                                     {chart.name || 'Untitled'}
                                 </div>
                                 <div className="text-[10px] text-slate-500 truncate">{chart.category}</div>
                             </div>
                             <GripVertical className="w-4 h-4 text-slate-700 opacity-0 group-hover:opacity-100 cursor-grab" />
                          </div>
                      </Reorder.Item>
                  ))}
                </Reorder.Group>
              )}
          </div>
          
          <div className="p-4 border-t border-white/10 bg-white/5">
              <button 
                onClick={handleExportPDF}
                disabled={exporting || orderedCharts.length === 0}
                className="w-full flex items-center justify-center gap-2 px-3 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl text-xs font-medium transition-colors border border-white/10"
              >
                  {exporting ? <Loader2 className="w-3 h-3 animate-spin" /> : <Download className="w-3 h-3" />}
                  Export PDF Report
              </button>
          </div>
      </div>

      {/* Column 2: Editor (Center) */}
      <div className="flex-1 w-full lg:w-auto min-w-0 flex flex-col gap-4 min-h-[600px] lg:min-h-0 order-1 lg:order-2">
      {/* Metadata & Actions Bar */}
          <div className="relative z-20 flex flex-col gap-2 bg-slate-900/40 backdrop-blur-md p-3 rounded-2xl border border-white/10 shadow-lg">
             <div className="flex justify-between items-start gap-4">
                 <div className="flex-1 min-w-0 flex flex-col gap-2">
                     <input 
                        type="text" 
                        value={name}
                        onChange={(e) => setName(e.target.value)}
                        className="bg-transparent text-base lg:text-lg font-bold text-white placeholder-slate-600 focus:outline-none w-full border-b border-dashed border-white/20 hover:border-white/40 focus:border-indigo-500 transition-colors pb-1 truncate"
                        placeholder="Untitled Analysis"
                     />
                     <div className="flex gap-2">
                         <input 
                            type="text" 
                            value={category}
                            onChange={(e) => setCategory(e.target.value)}
                            className="w-24 lg:w-32 bg-black/20 border border-white/10 rounded-lg px-2 py-1 text-xs text-slate-300 focus:border-indigo-500/50 outline-none"
                            placeholder="Category"
                         />
                         <input 
                            type="text" 
                            value={tags}
                            onChange={(e) => setTags(e.target.value)}
                            className="flex-1 min-w-0 bg-black/20 border border-white/10 rounded-lg px-2 py-1 text-xs text-slate-300 focus:border-indigo-500/50 outline-none"
                            placeholder="Tags (comma separated)"
                         />
                     </div>
                 </div>

                 {/* Action Buttons (Top Right) */}
                 <div className="flex gap-1.5 shrink-0 pt-0.5">
                     <button
                        onClick={handlePreview}
                        disabled={loading}
                        className="p-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg shadow-lg shadow-indigo-900/20 active:scale-[0.98] transition-all flex items-center justify-center border border-white/10"
                        title="Run Analysis"
                     >
                        {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4 fill-current" />}
                     </button>
                     <button
                        onClick={handleSave}
                        disabled={saving}
                        className="p-2 bg-emerald-600/20 hover:bg-emerald-500/30 text-emerald-400 hover:text-emerald-300 rounded-lg border border-emerald-500/30 transition-all flex items-center justify-center"
                        title="Save Changes"
                     >
                        {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                     </button>
                 </div>
             </div>
          </div>

          {/* Monaco Editor */}
          <div className="flex-grow flex flex-col bg-slate-900/40 backdrop-blur-md rounded-2xl border border-white/10 overflow-hidden shadow-lg relative group">
              <div className="absolute top-0 left-0 right-0 h-8 bg-[#1e1e1e] border-b border-white/5 flex items-center px-4 justify-between z-10">
                  <span className="text-xs font-mono text-slate-500 flex items-center gap-2">
                      <Code className="w-3 h-3" /> logic.py
                  </span>
                  <span className="text-xs text-slate-600">Python 3.10 Runtime</span>
              </div>
              <div className="pt-8 h-full bg-[#1e1e1e]">
                  <Editor
                     height="100%"
                     defaultLanguage="python"
                     value={code}
                     theme="vs-dark"
                     onChange={(value) => setCode(value || "")}
                     options={{
                         minimap: { enabled: false },
                         fontSize: 13,
                         lineNumbers: 'on',
                         scrollBeyondLastLine: false,
                         padding: { top: 16, bottom: 16 },
                         fontFamily: 'JetBrains Mono, monospace',
                         renderLineHighlight: 'all',
                     }}
                  />
              </div>
          </div>


      </div>

      {/* Column 3: Preview (Right) */}
      <div className="w-full lg:w-[40%] lg:min-w-[450px] flex flex-col gap-4 h-[600px] lg:h-full order-2 lg:order-3">
          <div className="flex-grow bg-slate-900/40 backdrop-blur-md rounded-2xl border border-white/10 shadow-2xl overflow-hidden flex flex-col relative">
             <div className="p-3 border-b border-white/5 bg-white/[0.02] flex justify-between items-center">
                 <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Output Visualization</span>
                 <div className="flex items-center gap-2">
                    {previewFigure && (
                        <button
                            onClick={handleCopyChart}
                            disabled={copying}
                            className="p-1.5 text-slate-400 hover:text-white hover:bg-white/10 rounded-lg transition-colors border border-transparent hover:border-white/5"
                            title="Copy Chart"
                        >
                            {copying ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : (
                                <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="lucide lucide-copy"><rect width="14" height="14" x="8" y="8" rx="2" ry="2"/><path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2"/></svg>
                            )}
                        </button>
                    )}
                    {previewFigure && <span className="text-[10px] px-2 py-0.5 bg-emerald-500/10 text-emerald-400 rounded-full border border-emerald-500/20">Live</span>}
                 </div>
             </div>
             
             <div className="flex-grow relative bg-gradient-to-br from-black/20 to-black/40">
                {previewFigure ? (
                    <Plot
                        data={previewFigure.data}
                        layout={{
                            ...previewFigure.layout,
                            autosize: true,
                            paper_bgcolor: 'rgba(0,0,0,0)',
                            plot_bgcolor: 'rgba(0,0,0,0)',
                            font: { color: '#94a3b8', family: 'Inter, sans-serif' },
                            margin: { t: 40, r: 80, l: 40, b: 40 },
                        }}
                        config={{ responsive: true, displayModeBar: 'hover', displaylogo: false }}
                        style={{ width: '100%', height: '100%' }}
                        useResizeHandler={true}
                        className="w-full h-full"
                        onInitialized={(_, gd) => setGraphDiv(gd)}
                    />
                ) : (
                    <div className="absolute inset-0 flex flex-col items-center justify-center text-slate-600/50">
                        <div className="w-20 h-20 rounded-full bg-white/5 flex items-center justify-center mb-4 backdrop-blur-sm">
                           <Play className="w-8 h-8 ml-1 opacity-50" />
                        </div>
                        <p className="font-medium">Ready to run</p>
                        <p className="text-xs text-slate-600 mt-2">Execute code to render chart</p>
                    </div>
                )}
             </div>
          </div>

          {/* Console / Status */}
          <div className="h-[150px] bg-black/60 backdrop-blur-md rounded-2xl border border-white/10 p-4 overflow-y-auto font-mono text-xs shadow-inner">
              <div className="text-slate-500 mb-2 font-semibold">Console Output:</div>
              {error ? (
                  <div className="text-rose-400 whitespace-pre-wrap">{String(error)}</div>
              ) : successMsg ? (
                  <div className="text-emerald-400">&gt; {successMsg}</div>
              ) : (
                  <div className="text-slate-600 italic">&gt; Waiting for execution...</div>
              )}
          </div>
      </div>
    </div>
  );
}
