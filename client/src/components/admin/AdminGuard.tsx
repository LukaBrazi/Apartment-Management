"use client";

import { useAppSelector } from "@/lib/redux/hooks/typedHooks";
import { useGetUserProfileQuery } from "@/lib/redux/features/users/usersApiSlice";
import Spinner from "@/components/shared/Spinner";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

interface AdminGuardProps {
	children: React.ReactNode;
}

export default function AdminGuard({ children }: AdminGuardProps) {
	const router = useRouter();
	const { isAuthenticated } = useAppSelector((state) => state.auth);

	const { data: profileData, isLoading } = useGetUserProfileQuery(undefined, {
		skip: !isAuthenticated,
	});

	const isStaff = profileData?.profile?.is_staff ?? false;

	useEffect(() => {
		if (!isLoading) {
			if (!isAuthenticated || (!isLoading && profileData && !isStaff)) {
				router.push("/welcome");
			}
		}
	}, [isAuthenticated, isLoading, isStaff, profileData, router]);

	if (isLoading || !profileData) {
		return (
			<div className="flex min-h-screen items-center justify-center bg-[#F7F6F2] dark:bg-[#0F1923]">
				<Spinner size="lg" />
			</div>
		);
	}

	if (!isAuthenticated || !isStaff) {
		return null;
	}

	return <>{children}</>;
}
