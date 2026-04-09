'use client';

import { Lock } from 'lucide-react';
import Link from 'next/link';

interface SignInPromptProps {
  /** What the user needs to sign in for, e.g. "research files" */
  feature?: string;
  /** Compact mode for embedded panels (less vertical padding) */
  compact?: boolean;
}

/**
 * Reusable inline prompt shown when a feature requires authentication.
 * Drop into any page/section instead of showing an error state.
 */
export default function SignInPrompt({ feature, compact }: SignInPromptProps) {
  return (
    <div className={`flex flex-col items-center justify-center gap-3 text-center ${compact ? 'py-10' : 'py-20'}`}>
      <div className="w-10 h-10 rounded-full border border-border/30 bg-foreground/[0.03] flex items-center justify-center">
        <Lock className="w-4 h-4 text-muted-foreground/40" />
      </div>
      <div className="space-y-1">
        <p className="text-sm font-medium text-foreground/70">Sign in required</p>
        {feature && (
          <p className="text-xs text-muted-foreground/50">
            Sign in to access {feature}
          </p>
        )}
      </div>
      <Link
        href="/login"
        className="mt-1 h-8 px-5 inline-flex items-center justify-center rounded-[var(--radius)] bg-foreground text-background text-xs font-semibold hover:opacity-90 transition-opacity"
      >
        Sign In
      </Link>
    </div>
  );
}
