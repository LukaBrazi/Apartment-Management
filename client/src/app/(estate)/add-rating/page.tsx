"use client";
import CreateRatingForm from "@/components/forms/add-rating/CreateRatingForm";
import { AuthFormHeader } from "@/components/forms/auth";
import ProtectedRoute from "@/components/shared/ProtectedRoutes";
import Spinner from "@/components/shared/Spinner";
import { useGetUserProfileQuery } from "@/lib/redux/features/users/usersApiSlice";
import { useAppSelector } from "@/lib/redux/hooks/typedHooks";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

function AddRatingContent() {
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
		<div className="mx-auto max-w-lg">
			<AuthFormHeader
				title="Оцінити технічного спеціаліста"
				staticText="Розкажіть нам, що ви думаєте про надані послуги"
				linkText="До списку спеціалістів"
				linkHref="/technicians"
			/>
			<div className="mt-8 sm:mx-auto sm:w-full sm:max-w-[480px]">
				<div className="rounded-2xl border border-[#E2E5E8] bg-white px-8 py-10 shadow-sm dark:border-[#2D3D4F] dark:bg-[#162032]">
					<CreateRatingForm />
				</div>
			</div>
		</div>
	);
}

export default function AddRatingPage() {
	return (
		<ProtectedRoute>
			<AddRatingContent />
		</ProtectedRoute>
	);
}
