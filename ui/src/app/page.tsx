import DashboardContainer from '@/components/DashboardContainer';
import { cookies } from 'next/headers';
import { Suspense } from 'react';

export const dynamic = process.env.NEXT_BUILD_MODE === 'export' ? 'auto' : 'force-dynamic';

export default async function Home() {
  // 🚀 For static export mode, we skip SSR to allow prerendering
  // This must be a clean return without calling any dynamic functions like cookies()
  if (process.env.NEXT_BUILD_MODE === 'export') {
    return (
      <Suspense fallback={null}>
        <DashboardContainer />
      </Suspense>
    );
  }

  // --- Dynamic SSR Logic (Only for non-export builds) ---
  let token = null;
  let initialData = null;

  try {
    // Dynamic access to cookies forces dynamic rendering in dev/prod-ssr
    const cookieStore = await cookies();
    token = cookieStore.get('access_token')?.value;

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 3000);

    const res = await fetch('http://127.0.0.1:8000/api/v1/dashboard/summary', {
      headers: token ? { 'Authorization': `Bearer ${token}` } : {},
      cache: 'no-store',
      signal: controller.signal
    });
    
    clearTimeout(timeoutId);

    if (res.ok) {
        initialData = await res.json();
    }
  } catch (err: any) {
    // Silent fail for SSR fetch - the client-side useQuery will handle the fallback
    console.warn('[SSR] Dashboard pre-fetch skipped or failed');
  }

  return (
    <Suspense fallback={null}>
      <DashboardContainer initialData={initialData} />
    </Suspense>
  );
}
