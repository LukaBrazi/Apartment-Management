import { createApi, fetchBaseQuery } from "@reduxjs/toolkit/query/react";
import { setAuth, setLogout } from "@/lib/redux/features/auth/authSlice";
import {
	BaseQueryFn,
	FetchArgs,
	FetchBaseQueryError,
} from "@reduxjs/toolkit/query";

import { Mutex } from "async-mutex";

const mutex = new Mutex();

const baseQuery = fetchBaseQuery({
	baseUrl: "/api/v1",
	credentials: "include",
});

/**
 * Belt-and-braces local cleanup after a session dies. The backend is
 * responsible for clearing the three auth cookies (access, refresh,
 * logged_in) via Set-Cookie, but if for any reason it doesn't, we wipe
 * the only cookie the client can see — `logged_in` — so that
 * `ProtectedRoute` stops treating the browser as authenticated.
 */
const clearLoggedInCookie = (): void => {
	if (typeof document === "undefined") return;
	const expired = "expires=Thu, 01 Jan 1970 00:00:00 GMT";
	document.cookie = `logged_in=; ${expired}; path=/`;
	document.cookie = `logged_in=; ${expired}; path=/; domain=${window.location.hostname}`;
};

/**
 * Auth bootstrap endpoints — login / refresh / logout / password-reset /
 * activation. A 401 from these does NOT mean "session expired" — it just
 * means the credentials were wrong (or the refresh token is dead). If we
 * naively trigger the refresh cycle for them, we end up:
 *   1. POST /auth/login/ → 401 (wrong password)
 *   2. baseQueryWithReauth fires POST /auth/refresh/ → 401 (no token yet)
 *   3. setLogout() runs and clears the `logged_in` cookie / Redux state
 *   4. The user is now in a corrupt state; subsequent login attempts may
 *      look "stuck" because the UI thinks logout is in progress.
 * Skipping the cycle keeps the original 401 visible to the LoginForm so
 * it can show the proper toast and let the user retry cleanly.
 */
const isAuthBootstrapEndpoint = (args: string | FetchArgs): boolean => {
	const url = typeof args === "string" ? args : args.url;
	if (!url) return false;
	return (
		url.startsWith("/auth/login") ||
		url.startsWith("/auth/refresh") ||
		url.startsWith("/auth/logout") ||
		url.startsWith("/auth/users/reset_password") ||
		url.startsWith("/auth/users/activation")
	);
};

const baseQueryWithReauth: BaseQueryFn<
	string | FetchArgs,
	unknown,
	FetchBaseQueryError
> = async (args, api, extraOptions) => {
	await mutex.waitForUnlock();

	let response = await baseQuery(args, api, extraOptions);

	if (
		response.error &&
		response.error.status === 401 &&
		!isAuthBootstrapEndpoint(args)
	) {
		if (!mutex.isLocked()) {
			const release = await mutex.acquire();
			try {
				const refreshResponse = await baseQuery(
					{
						url: "/auth/refresh/",
						method: "POST",
					},
					api,
					extraOptions,
				);

				if (refreshResponse?.data) {
					api.dispatch(setAuth());
					response = await baseQuery(args, api, extraOptions);

					// Ghost-session guard: the refresh succeeded (signed
					// refresh token is still valid) but the retried
					// request STILL returns 401. This happens when the
					// underlying user was deleted/anonymized (demo reseed,
					// GDPR erasure) while their refresh token was still
					// live. Without this guard we'd loop forever —
					// request 401 → refresh 200 → request 401 → … —
					// because every `refetchOnMountOrArgChange` kicks
					// off a new round. Force-logout breaks the loop.
					if (response.error && response.error.status === 401) {
						api.dispatch(setLogout());
						clearLoggedInCookie();
					}
				} else {
					api.dispatch(setLogout());
					clearLoggedInCookie();
				}
			} finally {
				release();
			}
		} else {
			await mutex.waitForUnlock();
			response = await baseQuery(args, api, extraOptions);
		}
	}
	return response;
};

export const baseApiSlice = createApi({
	reducerPath: "api",
	baseQuery: baseQueryWithReauth,
	tagTypes: ["User", "Apartment", "Issue", "Report", "Post", "VehiclePass", "Announcement", "AdminProfiles", "AdminWorkers", "AdminBuildings", "AdminEntrances", "News", "SiteSettings", "TelegramBot", "TelegramProfile", "Consent"],
	refetchOnFocus: true,
	refetchOnMountOrArgChange: true,
	endpoints: (builder) => ({}),
});
