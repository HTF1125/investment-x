'use client';

import { useAuth } from '@/context/AuthContext';
import { useRouter } from 'next/navigation';
import { useEffect } from 'react';
import { Lock } from 'lucide-react';

export default function AuthGuard({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !user) {
      router.replace('/login');
    }
  }, [user, loading, router]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background text-muted-foreground font-mono text-sm">
        <div className="flex gap-2 items-center animate-pulse">
            <div className="w-2 h-2 bg-sky-500 rounded-full" />
            INITIALIZING SECURITY PROTOCOLS...
        </div>
      </div>
    );
  }

  if (!user) return null;

  return <>{children}</>;
}
