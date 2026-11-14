import type { NextConfig } from "next";
import { readFileSync } from "node:fs";
import path from "node:path";

const appVersion = readFileSync(
  path.resolve(process.cwd(), "..", "version.txt"),
  "utf8",
).trim();

if (!appVersion) {
  throw new Error("The application version file is empty.");
}

const nextConfig: NextConfig = {
  /* config options here */
  cacheComponents: true,
  partialPrefetching: true,
  env: {
    NEXT_PUBLIC_APP_VERSION: appVersion,
  },
  outputFileTracingRoot: path.resolve(process.cwd(), ".."),
  outputFileTracingIncludes: {
    "/api/whats-new": ["../CHANGELOG.md"],
  },
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
