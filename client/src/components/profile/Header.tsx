"use client";
import ProtectedRoute from "@/components/shared/ProtectedRoutes";
import { useGetUserProfileQuery } from "@/lib/redux/features/users/usersApiSlice";
import { useTheme } from "next-themes";

import { Avatar, AvatarImage } from "@/components/ui/avatar";

function HeaderContent() {
	const { data } = useGetUserProfileQuery();
	const { theme } = useTheme();
	const profile = data?.profile;
	// Mobile-first: compact avatar (80px) + readable name (text-2xl) on phones.
	// Desktop (md+) keeps the original hero-size avatar + 5xl name.
	return (
		<div className="flex flex-col items-center gap-2 md:gap-3">
			<Avatar className="mx-auto size-20 overflow-hidden rounded-full border-4 border-pumpkin object-cover md:size-32">
				<AvatarImage
					src={
						profile?.avatar ||
						(theme === "dark"
							? "/assets/icons/user-profile-circle.svg"
							: "/assets/icons/user-profile-light-circle.svg")
					}
					alt="profile image"
					width={128}
					height={128}
				/>
			</Avatar>
			<div className="flex flex-col items-center justify-center gap-1 md:space-y-3">
				<h1 className="font-robotoSlab text-2xl font-semibold text-center md:text-5xl dark:text-platinum">
					{profile?.full_name}
				</h1>
				<p className="text-sm md:text-base dark:text-lime-500">
					@{profile?.username}
				</p>
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
