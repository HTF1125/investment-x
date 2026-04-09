'use client';

import { useEffect } from 'react';

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error('[GlobalError]', error);
  }, [error]);

  return (
    <html>
      <body style={{ margin: 0, fontFamily: '"Space Mono", monospace', backgroundColor: '#080a10', color: '#e5e5e5' }}>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: '100vh', padding: '1.5rem' }}>
          <p style={{ fontSize: '10px', fontFamily: 'Space Mono, monospace', textTransform: 'uppercase', letterSpacing: '0.12em', color: '#666', marginBottom: '1rem' }}>
            Runtime Error
          </p>
          <h1 style={{ fontSize: '1.5rem', fontWeight: 600, marginBottom: '0.5rem' }}>
            Something went wrong
          </h1>
          <p style={{ fontSize: '0.875rem', color: '#999', maxWidth: '28rem', textAlign: 'center', marginBottom: '2rem' }}>
            {error.message || 'An unexpected error occurred.'}
          </p>
          <button
            type="button"
            onClick={reset}
            style={{ padding: '0.5rem 1.25rem', borderRadius: '0.5rem', backgroundColor: '#e5e5e5', color: '#080a10', fontSize: '0.75rem', fontWeight: 500, border: 'none', cursor: 'pointer' }}
          >
            Try again
          </button>
        </div>
      </body>
    </html>
  );
}
