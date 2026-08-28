import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    const apiBaseUrl =
      process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

    return [
      {
        source: "/chat",
        destination: `${apiBaseUrl}/chat`,
      },
      {
        source: "/journals",
        destination: `${apiBaseUrl}/journals`,
      },
      {
        source: "/journals/:path*",
        destination: `${apiBaseUrl}/journals/:path*`,
      },
    ];
  },
};

export default nextConfig;
