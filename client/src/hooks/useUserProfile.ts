import { useGetUserProfileQuery } from "@/lib/redux/features/users/usersApiSlice";
import { useAppSelector } from "@/lib/redux/hooks/typedHooks";

export function useUserProfile() {
	const { isAuthenticated } = useAppSelector((state) => state.auth);

	const { data, isLoading, isError } = useGetUserProfileQuery(undefined, {
		skip: !isAuthenticated,
	});

	// When not authenticated return undefined explicitly — RTK Query keeps the
	// last cached value even after skip=true, which would show a stale name in
	// the topbar after logout.
	return { profile: isAuthenticated ? data?.profile : undefined, isLoading, isError };
}
