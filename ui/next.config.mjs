import { resolve } from 'path';

/** @type {import('next').NextConfig} */
const nextConfig = {
  transpilePackages: ['@excalidraw/excalidraw'],
  webpack(config, { isServer }) {
    // Point react-plotly.js to finance bundle (cartesian + candlestick/ohlc, ~1.5MB).
    config.resolve.alias['plotly.js/dist/plotly'] = resolve(
      'node_modules/plotly.js-finance-dist-min/plotly-finance.min.js'
    );
    // Also alias direct imports of plotly.js-dist-min used for resize/export
    config.resolve.alias['plotly.js-dist-min'] = resolve(
      'node_modules/plotly.js-finance-dist-min'
    );

    // pdfjs-dist uses DOMMatrix and other browser APIs that break SSR.
    // Exclude it from the server bundle (it's only used client-side via dynamic import).
    if (isServer) {
      config.externals = config.externals || [];
      config.externals.push('pdfjs-dist');
    }

    return config;
  },
  skipTrailingSlashRedirect: true,
  eslint: {
    ignoreDuringBuilds: false,
  },
  typescript: {
    ignoreBuildErrors: false,
  },
  output: process.env.NEXT_BUILD_MODE === 'export' ? 'export' : undefined,
  images: {
      unoptimized: true,
  },
  async rewrites() {
    // If exporting, no rewrites needed (handled by backend server)
    if (process.env.NEXT_BUILD_MODE === 'export') {
        return [];
    }
    
    // Use environment variable for backend URL, fallback to 127.0.0.1 for dev to avoid IPv6 issues
    let apiUrl = process.env.INTERNAL_API_URL || process.env.API_URL || 'http://127.0.0.1:8000';
    
    // Ensure protocol for Render internal URLs (which might be just host:port)
    if (apiUrl && !apiUrl.startsWith('http')) {
        apiUrl = `http://${apiUrl}`;
    }
    
    return [
      {
        source: '/api/:path*',
        destination: `${apiUrl}/api/:path*`,
      },
    ];

    // Note: skipTrailingSlashRedirect prevents Next.js from
    // stripping trailing slashes on API proxy routes.
  },
};

export default nextConfig;
