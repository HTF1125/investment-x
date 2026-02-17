'use client';

import React, { useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiFetchJson } from '@/lib/api';
import { Cpu, Clock, WifiOff } from 'lucide-react';

interface Message {
  id: string;
  channel_name: string;
  date: string;
  message: string;
}

export default function NewsFeed() {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  const { data: messages = [], isLoading, isError } = useQuery<Message[]>({
    queryKey: ['telegram-news', { hours: 24 }],
    queryFn: () => apiFetchJson<Message[]>('/api/news/telegram?hours=24'),
  });

  if (isLoading) {
    return (
      <div className="h-48 glass-card animate-pulse flex items-center justify-center text-slate-500 text-sm">
        Loading Intelligence Feed...
      </div>
    );
  }

  if (isError) {
    return (
      <div className="glass-card overflow-hidden border-rose-500/20 mb-12">
        <div className="flex flex-col items-center justify-center py-16 gap-4 text-center">
          <WifiOff className="w-8 h-8 text-rose-400/50" />
          <div>
            <p className="text-sm font-medium text-slate-400">Unable to load intelligence feed</p>
            <p className="text-xs text-slate-600 mt-1">Check your connection and try again.</p>
          </div>
        </div>
      </div>
    );
  }

  if (messages.length === 0) return null;

  return (
    <div className="glass-card overflow-hidden border-sky-500/20 mb-12">
      <div className="bg-sky-500/10 px-6 py-4 flex items-center justify-between border-b border-sky-500/20">
        <h3 className="text-sky-400 font-semibold flex items-center gap-2">
          <Cpu className="w-5 h-5 text-sky-400" />
          Quant Intelligence Feed (24h)
        </h3>
        <span className="text-[10px] text-sky-500/60 uppercase tracking-widest font-mono">Live Sync</span>
      </div>
      
      <div className="max-h-[400px] overflow-y-auto overflow-x-hidden">
        <div className="divide-y divide-white/5">
          {/* Sticky header */}
          <div className="sticky top-0 z-10 bg-slate-900/95 backdrop-blur-md border-b border-white/5 px-6 py-2.5 grid grid-cols-[auto_1fr] md:grid-cols-[100px_180px_1fr] gap-4 text-[10px] uppercase tracking-wider text-slate-500 font-medium">
            <span>Timestamp</span>
            <span className="hidden md:block">Source</span>
            <span>Intelligence Content</span>
          </div>

          {messages.map((msg) => (
            <div
              key={msg.id}
              className="px-6 py-4 grid grid-cols-[auto_1fr] md:grid-cols-[100px_180px_1fr] gap-4 hover:bg-white/[0.03] transition-colors group"
            >
              {/* Timestamp */}
              <div className="text-xs text-slate-500 tabular-nums whitespace-nowrap flex items-start gap-2 pt-0.5">
                <Clock className="w-3 h-3 mt-0.5 shrink-0" />
                {mounted ? new Date(msg.date).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '---'}
              </div>

              {/* Source — visible on md+ */}
              <div className="hidden md:block text-xs font-semibold text-slate-300 truncate pt-0.5">
                {msg.channel_name}
              </div>

              {/* Content */}
              <div className="text-sm text-slate-400 leading-relaxed font-light break-words whitespace-pre-wrap overflow-hidden min-w-0">
                <span className="md:hidden text-[10px] font-semibold text-slate-500 uppercase tracking-wider mr-2">{msg.channel_name}</span>
                {msg.message}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
