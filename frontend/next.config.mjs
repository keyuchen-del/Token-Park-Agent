/** @type {import('next').NextConfig} */
const nextConfig = {
  // standalone 让 Docker 镜像更小
  output: "standalone",
  reactStrictMode: true,
  // 后端 API rewrite，避免 CORS（部署时改成实际 backend URL）
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${
          process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"
        }/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
