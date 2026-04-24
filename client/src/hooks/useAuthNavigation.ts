import { leftNavLinks } from "@/constants";
import { useLogoutUserMutation } from "@/lib/redux/features/auth/authApiSlice";
import { setLogout } from "@/lib/redux/features/auth/authSlice";
import { useGetUserProfileQuery } from "@/lib/redux/features/users/usersApiSlice";
import { useAppDispatch, useAppSelector } from "@/lib/redux/hooks/typedHooks";
import { extractErrorMessage } from "@/utils";
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
		// Always clear client-side auth state first so the user is never
		// stuck on a protected page if the API call is rate-limited (429)
		// or fails for any other reason.
		dispatch(setLogout());
		router.push("/login");
		try {
			await logoutUser().unwrap();
			toast.success("До побачення!");
		} catch (e) {
			// Session cleared client-side; server-side token may persist until
			// expiry but the user is effectively logged out locally.
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

		// Guard-only: guard portal
		if (link.path === "/guard-portal" && !isGuard && !isStaff) return false;

		// Admin-only in nav: add post
		if (link.path === "/add-post" && !isStaff) return false;

		return true;
	});

	return { handleLogout, filteredNavLinks, isAuthenticated, isTenant, isStaff, isGuard };
}
