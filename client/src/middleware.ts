/**
 * Edge middleware: force unauthenticated users to the login form.
 *
 * Why this exists
 * ---------------
 * Next.js route groups (`(estate)/...`) share one layout — so a user who
 * lands on `/welcome`, `/news`, a non-existent path (404) or any protected
 * page without auth would otherwise see the navbars and shell scaffolding
 * of the app (see bug report: "404 → /welcome shows structure"). That leaks
 * UI and triggers client-side API calls that 401.
 *
 * The single source of truth for auth state on the client is the non-HttpOnly
 * ``logged_in`` cookie set by the backend (``apps.users.views``). If it's not
 * ``"true"``, this middleware short-circuits the request and redirects to
 * ``/login`` before any React / layout / RSC fetch runs.
 *
 * Public surface (accessible without auth):
 *   - /login
 *   - /forgot-password
 *   - /password-reset/** (token links from reset emails)
 *
 * Everything else is treated as protected. If you add a new genuinely public
 * page (a marketing landing, a public invite link, …), add it to
 * ``PUBLIC_PATHS`` or ``PUBLIC_PREFIXES`` below.
 *
 * Note: this is the first line of defense only — the backend still enforces
 * auth on every API endpoint. Middleware exists to stop the UI flash and to
 * match the UX contract "unauthenticated users see ONLY the login form".
 */
import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const LOGIN_PATH = "/login";

/** Exact paths that are reachable without authentication. */
const PUBLIC_PATHS = new Set<string>([
	LOGIN_PATH,
	"/forgot-password",
]);

/**
 * Path prefixes that are reachable without authentication.
 *
 * Password reset links contain ``uid/token`` segments and must stay public
 * (the whole point is that the user is locked out). Static assets under
 * ``/assets`` follow the same logic.
 */
const PUBLIC_PREFIXES: readonly string[] = [
	"/password-reset/",
	"/assets/",
];

function isPublicPath(pathname: string): boolean {
	if (PUBLIC_PATHS.has(pathname)) return true;
	return PUBLIC_PREFIXES.some((prefix) => pathname.startsWith(prefix));
}

export function middleware(request: NextRequest) {
	const { pathname, search } = request.nextUrl;

	// Cookie is non-HttpOnly by design (see backend ``logged_in_cookie_settings``).
	const loggedIn = request.cookies.get("logged_in")?.value === "true";

	if (loggedIn) {
		// Authenticated users are routed by page-level hooks
		// (``useRedirectIfAuthenticated`` keeps them away from /login).
		return NextResponse.next();
	}

	if (isPublicPath(pathname)) {
		return NextResponse.next();
	}

	// Unauthenticated + protected path → back to login.
	// Preserve the originally requested URL so we can optionally honor it
	// after login (not wired up today, but cheap to carry).
	const url = request.nextUrl.clone();
	url.pathname = LOGIN_PATH;
	url.search = "";
	if (pathname !== "/" && pathname !== LOGIN_PATH) {
		url.searchParams.set("next", pathname + search);
	}
	return NextResponse.redirect(url);
}

/**
 * Skip middleware for Next.js internals, Next image optimizer, and anything
 * with a file extension (favicons, opengraph images, robots.txt, etc.).
 *
 * The negative lookahead keeps the matcher cheap and avoids double-running
 * on assets — matcher is evaluated on every request.
 */
export const config = {
	matcher: [
		"/((?!_next/static|_next/image|favicon.ico|.*\\..*).*)",
	],
};
