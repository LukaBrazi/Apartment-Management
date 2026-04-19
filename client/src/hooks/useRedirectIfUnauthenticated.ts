import { useAppSelector } from "@/lib/redux/hooks/typedHooks";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

/**
 * Client-side guard that mirrors the edge middleware.
 *
 * The middleware (``src/middleware.ts``) is the primary line of defense: it
 * runs on the edge and never ships protected HTML to an unauthenticated user.
 * This hook is the second line: it covers the case where the ``logged_in``
 * cookie gets cleared mid-session (manual logout in another tab, backend
 * rotation, cookie expiry) and the user is sitting on a protected page.
 *
 * Behaviour
 * ---------
 * Waits for ``PersistAuth`` to hydrate Redux (``isInitialized``) to avoid a
 * redirect flash on first paint, then pushes to ``/login`` if the user is not
 * authenticated.
 */
const useRedirectIfUnauthenticated = () => {
	const router = useRouter();
	const { isAuthenticated, isInitialized } = useAppSelector(
		(state) => state.auth,
	);

	useEffect(() => {
		if (!isInitialized) return;
		if (!isAuthenticated) {
			router.push("/login");
		}
	}, [isAuthenticated, isInitialized, router]);

	return { isAuthenticated, isInitialized };
};

export default useRedirectIfUnauthenticated;
