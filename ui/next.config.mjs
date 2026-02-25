/** @type {import('next').NextConfig} */
const nextConfig = {
  // TODO: re-enable once eslint-plugin-react is compatible with eslint 8
  // (eslint-plugin-react@7.37.5 crashes with "Cannot read properties of undefined (reading 'deprecated')")
  eslint: {
    ignoreDuringBuilds: true,
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
    
    console.log(`[NextConfig] Using API URL: ${apiUrl}`);
    return [
      {
        source: '/api/:path*',
        destination: `${apiUrl}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
