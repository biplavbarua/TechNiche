import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    const rawUrl = process.env.NEXT_PUBLIC_API_URL;
    let apiUrl = rawUrl || "http://127.0.0.1:8000";

    // Sanitize: Remove quotes and whitespace
    apiUrl = apiUrl.replace(/['"\s]/g, "");

    // Ensure no trailing slash
    if (apiUrl.endsWith("/")) {
      apiUrl = apiUrl.slice(0, -1);
    }

    console.log("Rewrite destination:", apiUrl); // Helpful for Vercel logs

    return [
      {
        source: "/api/:path*",
        destination:
          process.env.NODE_ENV === "development"
            ? "http://127.0.0.1:8000/api/:path*"
            : `${apiUrl}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
