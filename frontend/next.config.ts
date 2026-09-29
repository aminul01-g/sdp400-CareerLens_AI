import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  // The API is a separate FastAPI service, so there is no need to rewrite asset
  // URLs or add image domains for local images stored under /public.
  images: { unoptimized: true },
  // Type errors and lint errors both fail the build: a green build is a gate,
  // not a suggestion.
  typescript: { ignoreBuildErrors: false },
};

export default nextConfig;
