/** @type {import('next').NextConfig} */
const nextConfig = {
	async rewrites() {
		const apiUrl = process.env.NEXT_PUBLIC_API_URL;
		// In local dev NEXT_PUBLIC_API_URL is not set — Nginx handles /api/* directly
		if (!apiUrl) return [];
		return [
			{
				source: "/api/:path*",
				destination: `${apiUrl}/api/:path*`,
			},
		];
	},
	// Prevent Next.js from issuing a 308 redirect when the URL has a trailing
	// slash (default Next behaviour strips it). Django REST endpoints live at
	// `/api/v1/.../` *with* a trailing slash (APPEND_SLASH=True), and we need
	// the browser to POST straight to the rewrite destination instead of
	// bouncing through a 308 that drops the body and breaks login on prod.
	skipTrailingSlashRedirect: true,
};

export default nextConfig;
