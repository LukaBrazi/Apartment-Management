"use client";

import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import {
	DropdownMenu,
	DropdownMenuContent,
	DropdownMenuItem,
	DropdownMenuLabel,
	DropdownMenuSeparator,
	DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useAuthNavigation } from "@/hooks";
import { useUserProfile } from "@/hooks/useUseProfile";
import { LogOut, User } from "lucide-react";
import Image from "next/image";
import Link from "next/link";
import React from "react";

export default function AuthAvatar() {
	const { handleLogout } = useAuthNavigation();

	const { profile, isLoading, isError } = useUserProfile();

	if (isLoading) {
		return null;
	}

	if (isError) {
		return null;
	}

	return (
		<div>
			{profile && (
				<DropdownMenu>
					<DropdownMenuTrigger asChild>
						<Avatar className="border-pumpkin cursor-pointer border-2">
							<AvatarImage alt="auth image" src={profile.avatar} />
							<AvatarFallback>
								<Image
									src="/assets/images/avatars/placeholder-neutral.svg"
									alt="Avatar"
									width={32}
									height={32}
									className="rounded-full"
								/>
							</AvatarFallback>
						</Avatar>
					</DropdownMenuTrigger>

					<DropdownMenuContent className="bg-white dark:bg-gray-800 border shadow-lg dark:text-platinum">
						<DropdownMenuLabel className="border-b-2">
							Мій акаунт
						</DropdownMenuLabel>
						<DropdownMenuSeparator />
						<DropdownMenuItem className="auth-nav">
							<Link href="/profile" className="flex-row-center">
								<User className="mr-1" /> Профіль
							</Link>
						</DropdownMenuItem>

						<DropdownMenuItem
							onClick={handleLogout}
							className="flex-row-center auth-nav cursor-pointer"
						>
							<LogOut className="mr-1" /> Вийти
						</DropdownMenuItem>
					</DropdownMenuContent>
				</DropdownMenu>
			)}
		</div>
	);
}
