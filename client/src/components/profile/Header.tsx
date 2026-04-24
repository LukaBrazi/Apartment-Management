"use client";
import ProtectedRoute from "@/components/shared/ProtectedRoutes";
import { useGetUserProfileQuery } from "@/lib/redux/features/users/usersApiSlice";

import { Avatar, AvatarImage } from "@/components/ui/avatar";

const occupationLabels: Record<string, string> = {
	mason: "Муляр",
	carpenter: "Тесляр",
	plumber: "Сантехнік",
	roofer: "Покрівельник",
	painter: "Маляр",
	electrician: "Електрик",
	hvac: "Вентиляція/Кліматизація",
	tenant: "Мешканець",
	guard: "Охоронець",
};

function HeaderContent() {
	const { data } = useGetUserProfileQuery();
	const profile = data?.profile;
	const occupationLabel =
		(profile?.occupation && occupationLabels[profile.occupation]) ||
		profile?.occupation ||
		"";

	// Mobile: horizontal card — avatar on left, name+username+role on right.
	// Desktop (md+): centered column (original hero layout).
	return (
		<div className="flex items-center gap-4 rounded-2xl border border-[#F1F5F9] bg-white p-4 shadow-sm md:flex-col md:items-center md:gap-3 md:p-6 dark:border-[#2D3D4F] dark:bg-[#162032]">
			<Avatar className="size-16 flex-shrink-0 overflow-hidden rounded-full border-2 border-[#CADCFC] md:size-24">
				<AvatarImage
					src={
						profile?.avatar ||
						"/assets/icons/user-profile-light-circle.svg"
					}
					alt="profile image"
					width={128}
					height={128}
				/>
			</Avatar>
			<div className="flex flex-col gap-0.5 md:items-center md:text-center">
				<h1 className="text-lg font-bold text-[#0F172A] md:text-3xl dark:text-[#F0EDE6]">
					{profile?.full_name}
				</h1>
				<p className="text-sm text-[#64748B]">@{profile?.username}</p>
				{profile?.occupation && (
					<span className="mt-1 inline-flex rounded-full bg-[#CADCFC] px-2.5 py-0.5 text-xs font-semibold text-[#1E2761]">
						{occupationLabel}
					</span>
				)}
			</div>
		</div>
	);
}

export default function Header() {
	return (
		<ProtectedRoute>
			<HeaderContent />
		</ProtectedRoute>
	);
}
