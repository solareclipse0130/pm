import type { NextConfig } from "next";

const isDev = process.env.NODE_ENV !== "production";
const apiTarget = process.env.NEXT_PUBLIC_API_PROXY_TARGET ?? "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  ...(isDev
    ? {
        async rewrites() {
          return [
            { source: "/api/:path*", destination: `${apiTarget}/api/:path*` },
          ];
        },
      }
    : { output: "export" }),
};

export default nextConfig;
