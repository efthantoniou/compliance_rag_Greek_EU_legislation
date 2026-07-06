import type { NextConfig } from "next";

const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:9000";

const nextConfig: NextConfig = {
  reactCompiler: true,
  async rewrites() {
    // Proxy API calls straight to the backend. `/api/health` keeps its own
    // route handler (for the offline fallback) and, as a filesystem route,
    // takes precedence over this rewrite.
    return [
      {
        source: "/api/:path*",
        destination: `${BACKEND_URL}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
