import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    const rawUrl = process.env.NEXT_PUBLIC_API_URL;
    let apiUrl = rawUrl || "http://127.0.0.1:8000";

    // Aggressive Sanitization:
    // 1. Remove quotes and standard whitespace which might come from copy-pasting env vars
    apiUrl = apiUrl.replace(/['"\s]/g, "");

    // 2. Ensure it starts with http/https.
    try {
      // If it doesn't start with http, assume https if it looks like a domain, otherwise default
      if (!apiUrl.startsWith("http")) {
        if (apiUrl.includes(".")) {
          apiUrl = "https://" + apiUrl;
        } else {
          // Fallback if totally garbage
          console.warn("Invalid API URL detected, falling back to localhost");
          apiUrl = "http://127.0.0.1:8000";
        }
      }
      // Validate URL structure
      const urlObj = new URL(apiUrl);
      apiUrl = urlObj.origin; // This gives us a clean http://domain.com without trailing slash
    } catch (e) {
      console.warn("Failed to parse API URL, falling back to localhost:", e);
      apiUrl = "http://127.0.0.1:8000";
    }

    console.log("Rewriting /api to:", apiUrl);

    return [
      {
        source: "/api/:path*",
        destination: `${apiUrl}/api/:path*`,
      },
    ];
  },
  transpilePackages: ["three", "@react-three/fiber", "@react-three/drei", "maath"],
};

export default nextConfig;
