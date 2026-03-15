import DashboardContainer from '@/components/DashboardContainer';
import { cookies } from 'next/headers';
import { Suspense } from 'react';
import type { Metadata } from 'next';

export const metadata: Metadata = { title: 'Charts Dashboard | Investment-X' };
export const dynamic = process.env.NEXT_BUILD_MODE === 'export' ? 'auto' : 'force-dynamic';

export default async function OldDashboard() {
  if (process.env.NEXT_BUILD_MODE === 'export') {
    return (
      <Suspense fallback={null}>
        <DashboardContainer />
      </Suspense>
    );
  }

  let token = null;
  let initialData = null;

  try {
    const cookieStore = await cookies();
    token = cookieStore.get('access_token')?.value;

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 3000);

    const apiBase = process.env.INTERNAL_API_URL || process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';
    const res = await fetch(`${apiBase}/api/v1/dashboard/summary?include_figures=false`, {
      headers: token ? { 'Authorization': `Bearer ${token}` } : {},
      cache: 'no-store',
      signal: controller.signal
    });

    clearTimeout(timeoutId);

    if (res.ok) {
        initialData = await res.json();
    }
  } catch (err: any) {
    console.warn('[SSR] Dashboard pre-fetch skipped or failed');
  }

  return (
    <Suspense fallback={null}>
      <DashboardContainer initialData={initialData} />
    </Suspense>
  );
}
