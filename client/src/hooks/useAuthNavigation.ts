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
		try {
			await logoutUser().unwrap();
			dispatch(setLogout());
			router.push("/login");
			toast.success("До побачення!");
		} catch (e) {
			const errorMessage = extractErrorMessage(e);
			toast.error(errorMessage || "An error occurred");
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
