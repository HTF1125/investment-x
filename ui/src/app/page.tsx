import DashboardContainer from '@/components/DashboardContainer';
import { cookies } from 'next/headers';

export const dynamic = process.env.NEXT_BUILD_MODE === 'export' ? 'auto' : 'force-dynamic';

export default async function Home() {
  // 🚀 For static export mode, we skip SSR to allow prerendering
  if (process.env.NEXT_BUILD_MODE === 'export') {
    return <DashboardContainer />;
  }

  let token = null;
  try {
    const cookieStore = await cookies();
    token = cookieStore.get('access_token')?.value;
  } catch (e) {
    // cookies() might throw if called in a context where headers aren't available
    console.warn('[SSR] Could not access cookies');
  }

  let initialData = null;
  try {
    // 🛡️ SSR Fetch with defensive timeout
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
    } else {
        const errorText = await res.text().catch(() => 'No error body');
        console.warn(`[SSR] Dashboard fetch failed | Status: ${res.status} | Error: ${errorText.substring(0, 100)}`);
    }
  } catch (err: any) {
    if (err.name === 'AbortError') {
        console.error('[SSR] Dashboard fetch timed out after 3.0s | Backend at 127.0.0.1:8000 is too slow or unreachable');
    } else {
        console.error('[SSR] Dashboard fetch critical error:', err.message);
    }
  }

  return <DashboardContainer initialData={initialData} />;
}
