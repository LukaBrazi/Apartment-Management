/** @type {import('next').NextConfig} */
const nextConfig = {
	async rewrites() {
		const apiUrl = process.env.NEXT_PUBLIC_API_URL;
		// In local dev NEXT_PUBLIC_API_URL is not set — Nginx handles /api/* directly
		if (!apiUrl) return [];
		return [
			{
				// Next.js normalises the incoming URL before matching rewrites
				// and strips a trailing slash regardless of `skipTrailingSlashRedirect`.
				// That meant `/api/v1/auth/login/` was proxied to Django as
				// `/api/v1/auth/login` (no slash); Django APPEND_SLASH=True then
				// 301'd back to `/api/v1/auth/login/`, the browser followed as
				// GET (POST body dropped), Next stripped the slash again — infinite
				// loop, "ERR_TOO_MANY_REDIRECTS" on login.
				//
				// Explicitly re-append the slash in the destination so Django
				// always receives the canonical `/api/.../` form and never has
				// to redirect. Safe because every Django REST endpoint lives at
				// a path with a trailing slash (APPEND_SLASH=True is the project
				// convention).
				source: "/api/:path*",
				destination: `${apiUrl}/api/:path*/`,
			},
		];
	},
	// Kept for belt-and-braces: if any non-/api route ends with a slash we
	// don't want Next.js issuing its own 308 either.
	skipTrailingSlashRedirect: true,
};

export default nextConfig;
