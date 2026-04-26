/** @type {import('next').NextConfig} */

// ── Security headers (PR-8) ──────────────────────────────────────────────────
//
// Why CSP only on the frontend (Next.js) and not also on Django:
//   • Users only ever browse Vercel-served pages. Django admin is behind a
//     secret URL prefix, smaller surface, and adding django-csp would mean
//     fighting DRF browsable API + Django admin inline scripts.
//   • Next.js is the right layer for `script-src` / `connect-src` / etc.
//     because it owns the HTML response that the browser parses.
//
// `script-src 'unsafe-inline' 'unsafe-eval'`:
//   Next.js needs both for hydration, the dev `eval` overlay and React
//   Refresh.  This is intentionally a starting baseline — a future PR can
//   tighten to per-request nonces (Next.js middleware-driven) once we are
//   sure no analytics / CDN script silently relies on it.
//
// `connect-src` MUST include the API origin — RTK Query talks to it from
// the browser via fetch.  Without it every API call is blocked silently
// by the browser and the app breaks in confusing ways.  In dev (no
// NEXT_PUBLIC_API_URL) Next.js proxies `/api/*` itself so `'self'` is
// enough; in prod we additionally allow https://api.apartmentos.org and
// the matching wss:// origin for future real-time features.
//
// `img-src 'self' data: blob: https:` — broad on purpose: Cloudflare R2
// public URLs are randomised (`pub-<hash>.r2.dev`) and avatars can be
// hosted on multiple CDNs.  Tightening to a fixed allow-list once R2 is
// pinned to a custom domain.
const securityHeaders = [
	{
		key: "Content-Security-Policy",
		value: [
			"default-src 'self'",
			// Next.js needs unsafe-inline + unsafe-eval for hydration & React refresh.
			// Можна посилити через nonces у наступному PR — це starting baseline.
			"script-src 'self' 'unsafe-inline' 'unsafe-eval'",
			"style-src 'self' 'unsafe-inline'",
			// Дозволяємо media з нашого S3/R2 bucket + data: URLs (for inline SVGs)
			"img-src 'self' data: blob: https:",
			"font-src 'self' data:",
			// API + WebSocket для майбутніх real-time features.
			// `https:` / `wss:` schemes are NOT enough — CSP requires the
			// explicit host.  Railway preview domains *.up.railway.app are
			// included so that staging deploys also work without a separate
			// config flag.
			"connect-src 'self' https://api.apartmentos.org wss://api.apartmentos.org https://*.up.railway.app wss://*.up.railway.app",
			"frame-ancestors 'none'",
			"base-uri 'self'",
			"form-action 'self'",
			"object-src 'none'",
		].join("; "),
	},
	{ key: "X-Frame-Options", value: "DENY" },
	{ key: "X-Content-Type-Options", value: "nosniff" },
	{ key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
	{
		key: "Permissions-Policy",
		value: "camera=(), microphone=(), geolocation=()",
	},
];

const nextConfig = {
	async headers() {
		return [{ source: "/(.*)", headers: securityHeaders }];
	},
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
