/** @type {import('next').NextConfig} */
const nextConfig = {
  eslint: {
    ignoreDuringBuilds: true,
  },
  async rewrites() {
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
