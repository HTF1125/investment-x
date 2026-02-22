'use client';

import React, { useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiFetchJson } from '@/lib/api';
import { Cpu, Clock, WifiOff, Sparkles } from 'lucide-react';
import { useTheme } from '@/context/ThemeContext';

interface Message {
  id: string;
  channel_name: string;
  date: string;
  message: string;
}

interface NewsAggregateResponse {
  generated_at: string;
  telegram_messages: Message[];
  video_summaries: Array<{
    video_id: string;
    channel: string;
    title: string;
    published_at: string;
    summary?: string | null;
    url: string;
  }>;
}

export default function NewsFeed() {
  const [mounted, setMounted] = useState(false);
  const { theme } = useTheme();
  const isLight = theme === 'light';

  useEffect(() => {
    setMounted(true);
  }, []);

  const { data, isLoading, isError } = useQuery<NewsAggregateResponse>({
    queryKey: ['news-feed'],
    queryFn: () => apiFetchJson<NewsAggregateResponse>('/api/news'),
  });
  const messages = data?.telegram_messages || [];

  if (isLoading) {
    return (
      <div className="h-52 border border-border/60 rounded-3xl bg-card/30 animate-pulse flex items-center justify-center text-muted-foreground text-sm">
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
    <section className={`border border-border/60 rounded-3xl overflow-hidden shadow-2xl mb-12 ${
      isLight ? 'bg-card' : 'bg-[linear-gradient(180deg,rgba(8,47,73,0.26),rgba(5,5,5,0.96)_28%)]'
    }`}>
      <div className="px-5 md:px-6 py-4 flex items-center justify-between border-b border-border/50">
        <h3 className="text-primary font-semibold flex items-center gap-2 text-sm uppercase tracking-[0.15em]">
          <Cpu className="w-5 h-5" />
          Quant Intelligence Feed (24h)
        </h3>
        <span className="text-[10px] text-primary/70 uppercase tracking-widest font-mono inline-flex items-center gap-1.5">
          <Sparkles className="w-3.5 h-3.5" />
          Live Sync
        </span>
      </div>
      
      <div className="max-h-[640px] overflow-y-auto overflow-x-hidden custom-scrollbar">
        <div className="divide-y divide-border/30">
          {/* Sticky header */}
          <div className="sticky top-0 z-10 bg-card/90 backdrop-blur-md border-b border-border px-5 md:px-6 py-3 grid grid-cols-[auto_1fr] md:grid-cols-[100px_180px_1fr] gap-4 text-[10px] uppercase tracking-wider text-muted-foreground font-black">
            <span>Timestamp</span>
            <span className="hidden md:block">Source</span>
            <span>Intelligence Content</span>
          </div>

          {messages.map((msg) => (
            <div
              key={msg.id}
              className="px-5 md:px-6 py-4 grid grid-cols-[auto_1fr] md:grid-cols-[100px_180px_1fr] gap-4 hover:bg-foreground/[0.03] transition-colors group"
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
                <span className="md:hidden text-[10px] font-bold text-primary uppercase tracking-wider mr-2">{msg.channel_name}</span>
                {msg.message}
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
