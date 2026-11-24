// The browser calls /api/* on the same origin; Next.js forwards it to FastAPI.
// This works locally, in GitHub Codespaces and in Docker without CORS/port issues.
const API_INTERNAL_URL = process.env.API_INTERNAL_URL || "http://localhost:8000";

export default {
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${API_INTERNAL_URL}/:path*` }];
  },
};
