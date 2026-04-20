"use client";

import { useAppSelector } from "@/lib/redux/hooks/typedHooks";
import { useGetUserProfileQuery } from "@/lib/redux/features/users/usersApiSlice";
import Spinner from "@/components/shared/Spinner";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

interface SuperAdminGuardProps {
	children: React.ReactNode;
}

/**
 * Gate a page behind ``profile.is_superuser``.
 *
 * The platform has three layers of admin:
 *   - ``is_staff``           → per-org admins / directors (``/admin/*``)
 *   - ``is_staff`` + DIRECTOR/ADMIN role → org-scoped control
 *   - ``is_superuser``       → platform operators (us)
 *
 * The Telegram bot management page is platform-wide — one bot per org,
 * credentials that span tenants, webhook secrets — so it belongs to the
 * third tier.  This guard sends anyone without ``is_superuser`` back to
 * the regular admin dashboard instead of ``/welcome`` so a director
 * clicking a deep link doesn't get punted out of the admin surface
 * entirely; they just see "not found here" from their perspective.
 */
export default function SuperAdminGuard({ children }: SuperAdminGuardProps) {
	const router = useRouter();
	const { isAuthenticated, isInitialized } = useAppSelector(
		(state) => state.auth,
	);

	const { data: profileData, isLoading } = useGetUserProfileQuery(undefined, {
		skip: !isAuthenticated,
	});

	const isSuperuser = profileData?.profile?.is_superuser ?? false;

	useEffect(() => {
		if (!isInitialized) return;
		if (!isLoading) {
			if (!isAuthenticated) {
				router.push("/login");
				return;
			}
			if (profileData && !isSuperuser) {
				router.push("/admin");
			}
		}
	}, [
		isAuthenticated,
		isInitialized,
		isLoading,
		isSuperuser,
		profileData,
		router,
	]);

	if (!isInitialized || isLoading || (isAuthenticated && !profileData)) {
		return (
			<div className="flex min-h-[60vh] items-center justify-center">
				<Spinner size="lg" />
			</div>
		);
	}

	if (!isAuthenticated || !isSuperuser) {
		return null;
	}

	return <>{children}</>;
}
