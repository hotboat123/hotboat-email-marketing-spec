/** @type {import('next').NextConfig} */
const nextConfig = {
  eslint: { ignoreDuringBuilds: true },
  typescript: { ignoreBuildErrors: true },
  trailingSlash: true,   // keep trailing slashes — prevents 308 redirect that drops auth headers
};

export default nextConfig;
