"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAppSelector } from "@/lib/redux/hooks/typedHooks";
import { useGetUserProfileQuery } from "@/lib/redux/features/users/usersApiSlice";
import ProtectedRoute from "@/components/shared/ProtectedRoutes";
import Spinner from "@/components/shared/Spinner";

type Role = "staff" | "guard";

interface RoleGuardContentProps {
	children: React.ReactNode;
	role: Role;
}

function RoleGuardContent({ children, role }: RoleGuardContentProps) {
	const router = useRouter();
	const { isAuthenticated } = useAppSelector((state) => state.auth);

	const { data: profileData, isLoading } = useGetUserProfileQuery(undefined, {
		skip: !isAuthenticated,
	});

	const isStaff = profileData?.profile?.is_staff ?? false;
	const occupation = profileData?.profile?.occupation;
	const isGuard = occupation === "guard";

	const isAuthorized =
		role === "staff" ? isStaff : isGuard || isStaff;

	useEffect(() => {
		if (!isLoading && profileData && !isAuthorized) {
			router.replace("/welcome");
		}
	}, [isLoading, profileData, isAuthorized, router]);

	if (isLoading) {
		return (
			<div className="flex-center pt-32">
				<Spinner size="xl" />
			</div>
		);
	}

	if (!isAuthorized) return null;

	return <>{children}</>;
}

export default function RoleGuard({
	children,
	role,
}: {
	children: React.ReactNode;
	role: Role;
}) {
	return (
		<ProtectedRoute>
			<RoleGuardContent role={role}>{children}</RoleGuardContent>
		</ProtectedRoute>
	);
}
