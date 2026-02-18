import DashboardContainer from '@/components/DashboardContainer';
import { cookies } from 'next/headers';

export const dynamic = 'force-dynamic';

export default async function Home() {
  const cookieStore = await cookies();
  const token = cookieStore.get('access_token')?.value;

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
