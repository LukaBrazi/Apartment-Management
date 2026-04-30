import { leftNavLinks } from "@/constants";
import { useLogoutUserMutation } from "@/lib/redux/features/auth/authApiSlice";
import { setLogout } from "@/lib/redux/features/auth/authSlice";
import { useGetUserProfileQuery } from "@/lib/redux/features/users/usersApiSlice";
import { useAppDispatch, useAppSelector } from "@/lib/redux/hooks/typedHooks";
import { extractErrorMessage } from "@/utils";
import { deleteCookie } from "cookies-next";
import { useRouter } from "next/navigation";
import { toast } from "react-toastify";

export function useAuthNavigation() {
	const dispatch = useAppDispatch();
	const [logoutUser] = useLogoutUserMutation();
	const { isAuthenticated } = useAppSelector((state) => state.auth);
	const router = useRouter();

	const { data: profileData } = useGetUserProfileQuery(undefined, {
		skip: !isAuthenticated,
	});

	const occupation = profileData?.profile?.occupation;
	const isStaff = profileData?.profile?.is_staff ?? false;
	const isTenant = occupation === "tenant";
	const isGuard = occupation === "guard";

	const handleLogout = async () => {
		// Clear client-side auth state immediately — user must never be stuck
		// on a protected page even if the API call fails (rate-limit, network, etc.).
		dispatch(setLogout());
		// `logged_in` is not httpOnly so we can delete it from JS too.
		// This prevents ProtectedRoute from re-authenticating after a failed
		// server-side logout.
		deleteCookie("logged_in");
		router.push("/login");
		try {
			await logoutUser().unwrap();
			toast.success("До побачення!");
		} catch (e) {
			// Server-side tokens will expire on their own; client is logged out.
			const errorMessage = extractErrorMessage(e);
			if (errorMessage) toast.error(errorMessage);
		}
	};

	const filteredNavLinks = leftNavLinks.filter((link) => {
		// Require authentication for these paths
		const authRequired = [
			"/profile",
			"/report-issue",
			"/report-tenant",
			"/bookmark",
			"/add-post",
		];
		if (authRequired.includes(link.path) && !isAuthenticated) return false;

		// Admin-only: tenants list and ratings
		if (link.path === "/tenants" && !isStaff) return false;
		if (link.path === "/add-rating" && !isStaff) return false;
		if (link.path === "/technicians" && !isStaff) return false;
		if (link.path === "/admin" && !isStaff) return false;

		// Tenant-only: request pass
		if (link.path === "/request-pass" && !isAuthenticated) return false;
		if (link.path === "/request-pass" && !isTenant && !isStaff) return false;

		// PR-16: assigned issues — worker/staff/dispatcher/guard only.
		// Tenants don't get assignments, so hide it for them and for unauth.
		if (link.path === "/assigned-issues" && (isTenant || !isAuthenticated)) return false;

		// Guard-only: guard portal
		if (link.path === "/guard-portal" && !isGuard && !isStaff) return false;

		// Admin-only in nav: add post
		if (link.path === "/add-post" && !isStaff) return false;

		return true;
	});

	return { handleLogout, filteredNavLinks, isAuthenticated, isTenant, isStaff, isGuard };
}
