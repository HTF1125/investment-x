import { resolve } from 'path';

/** @type {import('next').NextConfig} */
const nextConfig = {
  transpilePackages: ['@excalidraw/excalidraw'],
  webpack(config, { isServer }) {
    // Point react-plotly.js (which imports plotly.js/dist/plotly) to the
    // much smaller plotly.js-dist-min bundle to avoid shipping both.
    config.resolve.alias['plotly.js/dist/plotly'] = resolve(
      'node_modules/plotly.js-dist-min/plotly.min.js'
    );

    // pdfjs-dist uses DOMMatrix and other browser APIs that break SSR.
    // Exclude it from the server bundle (it's only used client-side via dynamic import).
    if (isServer) {
      config.externals = config.externals || [];
      config.externals.push('pdfjs-dist');
    }

    return config;
  },
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
    let apiUrl = process.env.INTERNAL_API_URL || process.env.API_URL || 'http://127.0.0.1:8001';
    
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
  },
};

export default nextConfig;
