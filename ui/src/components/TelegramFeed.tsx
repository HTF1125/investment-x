'use client';

import { useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiFetchJson } from '@/lib/api';
import { MessageSquare, Clock, WifiOff } from 'lucide-react';

interface TelegramMessage {
  id: string;
  channel_name: string;
  date: string;
  message: string | null;
}

interface NewsAggregateResponse {
  generated_at: string;
  telegram_messages: TelegramMessage[];
}

export default function TelegramFeed({ embedded }: { embedded?: boolean } = {}) {
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);

  const { data, isLoading, isError } = useQuery<NewsAggregateResponse>({
    queryKey: ['telegram-feed'],
    queryFn: () => apiFetchJson<NewsAggregateResponse>('/api/news'),
    staleTime: 30_000,
    refetchInterval: 60_000,
  });

  const messages = data?.telegram_messages || [];

  if (isLoading) {
    return (
      <div className="h-full border border-border/60 rounded-xl bg-background animate-pulse flex items-center justify-center text-muted-foreground text-sm">
        Loading Telegram feed...
      </div>
    );
  }

  if (isError) {
    return (
      <div className="h-full border border-rose-500/20 rounded-xl bg-rose-500/[0.04] p-8 flex flex-col items-center justify-center gap-3 text-center">
        <WifiOff className="w-6 h-6 text-rose-400/50" />
        <p className="text-sm text-muted-foreground">Unable to load Telegram feed</p>
      </div>
    );
  }

  const outer = embedded
    ? 'h-full flex flex-col min-h-0 overflow-hidden'
    : 'h-full border border-border/60 rounded-xl overflow-hidden bg-background flex flex-col min-h-0';

  return (
    <section className={outer}>
      <div className="h-10 flex items-center justify-between px-3 border-b border-border/60 shrink-0">
        <div className="flex items-center gap-2">
          <MessageSquare className="w-3.5 h-3.5 text-muted-foreground/50 shrink-0" />
          <span className="text-xs font-semibold text-foreground">Telegram Feed</span>
        </div>
        <span className="text-[10px] text-muted-foreground/60 font-mono">{messages.length} msgs</span>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto custom-scrollbar divide-y divide-border/40">
        {messages.length === 0 ? (
          <div className="h-full flex items-center justify-center text-sm text-muted-foreground">No recent Telegram messages.</div>
        ) : (
          messages.map((msg) => (
            <article key={msg.id} className="px-3 py-2 hover:bg-foreground/[0.02] transition-colors">
              <div className="flex items-center justify-between gap-2 text-[10px] text-muted-foreground/70 mb-1.5">
                <span className="truncate uppercase tracking-wider">{msg.channel_name.replace('t.me/', '')}</span>
                <span className="font-mono inline-flex items-center gap-1 shrink-0">
                  <Clock className="w-3 h-3" />
                  {mounted ? new Date(msg.date).toLocaleString() : '--'}
                </span>
              </div>
              <p className="text-[11px] leading-relaxed text-foreground/85 whitespace-pre-wrap break-words">
                {msg.message || '(empty)'}
              </p>
            </article>
          ))
        )}
      </div>
    </section>
  );
}
