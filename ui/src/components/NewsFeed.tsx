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
      <div className="h-48 !bg-card border border-border/50 rounded-2xl animate-pulse flex items-center justify-center text-muted-foreground text-sm">
        Loading Intelligence Feed...
      </div>
    );
  }

  if (isError) {
    return (
      <div className="border border-rose-500/20 rounded-2xl bg-rose-500/5 mb-12">
        <div className="flex flex-col items-center justify-center py-16 gap-4 text-center">
          <WifiOff className="w-8 h-8 text-rose-400/50" />
          <div>
            <p className="text-sm font-medium text-foreground">Unable to load intelligence feed</p>
            <p className="text-xs text-muted-foreground mt-1">Check your connection and try again.</p>
          </div>
        </div>
      </div>
    );
  }

  if (messages.length === 0) return null;

  return (
    <div className="!bg-background border border-border/50 rounded-2xl overflow-hidden mb-12 shadow-2xl">
      <div className="bg-sky-500/5 px-6 py-4 flex items-center justify-between border-b border-border/50">
        <h3 className="text-sky-400 font-semibold flex items-center gap-2 text-sm uppercase tracking-wider">
          <Cpu className="w-5 h-5" />
          Quant Intelligence Feed (24h)
        </h3>
        <span className="text-[10px] text-sky-500/60 uppercase tracking-widest font-mono">Live Sync</span>
      </div>
      
      <div className="max-h-[600px] overflow-y-auto overflow-x-hidden custom-scrollbar">
        <div className="divide-y divide-border/30">
          {/* Sticky header */}
          <div className="sticky top-0 z-10 !bg-background !opacity-100 border-b border-border px-6 py-3 grid grid-cols-[auto_1fr] md:grid-cols-[100px_180px_1fr] gap-4 text-[10px] uppercase tracking-wider text-muted-foreground font-black">
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
              <div className="text-xs text-muted-foreground tabular-nums whitespace-nowrap flex items-start gap-2 pt-0.5 font-mono">
                <Clock className="w-3 h-3 mt-0.5 shrink-0" />
                {mounted ? new Date(msg.date).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '---'}
              </div>

              {/* Source — visible on md+ */}
              <div className="hidden md:block text-xs font-bold text-foreground/80 truncate pt-0.5 font-mono">
                {msg.channel_name.replace('t.me/', '')}
              </div>

              {/* Content */}
              <div className="text-[13px] text-foreground/90 leading-relaxed font-normal break-words whitespace-pre-wrap overflow-hidden min-w-0">
                <span className="md:hidden text-[10px] font-bold text-sky-500 uppercase tracking-wider mr-2">{msg.channel_name}</span>
                {msg.message}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
