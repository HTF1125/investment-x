'use client';

import React, { useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiFetchJson } from '@/lib/api';
import { Cpu, Clock, WifiOff, Sparkles } from 'lucide-react';

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
      <div className="h-32 border border-border/60 rounded-xl bg-background animate-pulse flex items-center justify-center text-muted-foreground text-sm">
        Loading intelligence feed…
      </div>
    );
  }

  if (isError) {
    return (
      <div className="border border-rose-500/20 rounded-xl bg-rose-500/[0.04] p-8 flex flex-col items-center gap-3 text-center">
        <WifiOff className="w-6 h-6 text-rose-400/50" />
        <p className="text-sm text-muted-foreground">Unable to load intelligence feed</p>
      </div>
    );
  }

  if (messages.length === 0) return null;

  return (
    <section className="border border-border/60 rounded-xl overflow-hidden bg-background">
      <div className="h-11 flex items-center justify-between px-4 border-b border-border/60">
        <div className="flex items-center gap-2">
          <Cpu className="w-3.5 h-3.5 text-muted-foreground/50 shrink-0" />
          <span className="text-sm font-semibold text-foreground">Quant Intelligence</span>
          <span className="text-muted-foreground/30 text-[11px]">·</span>
          <span className="text-[11px] text-muted-foreground/60">24h</span>
        </div>
        <span className="text-[10px] text-muted-foreground/50 uppercase tracking-wider font-mono inline-flex items-center gap-1.5">
          <Sparkles className="w-3 h-3" />
          Live
        </span>
      </div>

      <div className="max-h-[640px] overflow-y-auto overflow-x-hidden custom-scrollbar">
        <div className="divide-y divide-border/40">
          {/* Sticky header */}
          <div className="sticky top-0 z-10 bg-background border-b border-border/60 px-4 md:px-5 py-2.5 grid grid-cols-[auto_1fr] md:grid-cols-[100px_180px_1fr] gap-4 text-[10px] uppercase tracking-wider text-muted-foreground/50 font-medium">
            <span>Time</span>
            <span className="hidden md:block">Source</span>
            <span>Content</span>
          </div>

          {messages.map((msg) => (
            <div
              key={msg.id}
              className="px-4 md:px-5 py-3.5 grid grid-cols-[auto_1fr] md:grid-cols-[100px_180px_1fr] gap-4 hover:bg-foreground/[0.02] transition-colors"
            >
              {/* Timestamp */}
              <div className="text-[11px] text-muted-foreground/60 tabular-nums whitespace-nowrap flex items-start gap-1.5 pt-0.5 font-mono">
                <Clock className="w-3 h-3 mt-0.5 shrink-0" />
                {mounted ? new Date(msg.date).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '─ ─'}
              </div>

              {/* Source */}
              <div className="hidden md:block text-[11px] font-medium text-foreground/70 truncate pt-0.5 font-mono">
                {msg.channel_name.replace('t.me/', '')}
              </div>

              {/* Content */}
              <div className="text-[13px] text-foreground/85 leading-relaxed break-words whitespace-pre-wrap overflow-hidden min-w-0">
                <span className="md:hidden text-[10px] font-medium text-muted-foreground uppercase tracking-wider mr-2">{msg.channel_name}</span>
                {msg.message}
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
