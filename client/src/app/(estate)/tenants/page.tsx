"use client";
import TenantCard from "@/components/cards/TenantCard";
import ProtectedRoute from "@/components/shared/ProtectedRoutes";
import Spinner from "@/components/shared/Spinner";
import { useGetUserProfileQuery } from "@/lib/redux/features/users/usersApiSlice";
import { useAppSelector } from "@/lib/redux/hooks/typedHooks";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

function TenantsPageContent() {
	const router = useRouter();
	const { isAuthenticated } = useAppSelector((state) => state.auth);
	const { data: profileData, isLoading } = useGetUserProfileQuery(undefined, {
		skip: !isAuthenticated,
	});

	const isStaff = profileData?.profile?.is_staff ?? false;

	useEffect(() => {
		if (!isLoading && profileData && !isStaff) {
			router.replace("/welcome");
		}
	}, [isLoading, profileData, isStaff, router]);

	if (isLoading) {
		return (
			<div className="flex-center pt-32">
				<Spinner size="xl" />
			</div>
		);
	}

	if (!isStaff) return null;

	return (
		<div>
			<TenantCard />
		</div>
	);
}

export default function TenantsPage() {
	return (
		<ProtectedRoute>
			<TenantsPageContent />
		</ProtectedRoute>
	);
}
