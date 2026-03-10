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
};

export default nextConfig;
