import type { NextConfig } from "next";

const localApiBaseUrl = "http://127.0.0.1:8000";
const configuredApiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL;
const apiBaseUrl = configuredApiBaseUrl ?? localApiBaseUrl;

if (process.env.VERCEL === "1" && !configuredApiBaseUrl) {
  throw new Error(
    "NEXT_PUBLIC_API_BASE_URL must be set on Vercel to your public backend URL, for example https://journal-rag.onrender.com",
  );
}

const nextConfig: NextConfig = {
  async rewrites() {
    const normalizedApiBaseUrl = apiBaseUrl.replace(/\/$/, "");

    return [
      {
        source: "/chat",
        destination: `${normalizedApiBaseUrl}/chat`,
      },
      {
        source: "/journals",
        destination: `${normalizedApiBaseUrl}/journals`,
      },
      {
        source: "/journals/:path*",
        destination: `${normalizedApiBaseUrl}/journals/:path*`,
      },
      {
        source: "/sources",
        destination: `${normalizedApiBaseUrl}/sources`,
      },
      {
        source: "/sources/:path*",
        destination: `${normalizedApiBaseUrl}/sources/:path*`,
      },
    ];
  },
};

export default nextConfig;
