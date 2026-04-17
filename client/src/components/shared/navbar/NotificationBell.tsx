"use client";

import { Bell, Inbox } from "lucide-react";
import {
	DropdownMenu,
	DropdownMenuContent,
	DropdownMenuLabel,
	DropdownMenuSeparator,
	DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import Image from "next/image";

export default function NotificationBell() {
	// TODO: Replace with RTK Query hook when backend API is ready
	// const { data } = useGetNotificationsQuery();
	const notifications: {
		id: string;
		title: string;
		message: string;
		is_read: boolean;
		created_at: string;
	}[] = [];
	const unreadCount = notifications.filter((n) => !n.is_read).length;

	return (
		<DropdownMenu>
			<DropdownMenuTrigger asChild>
				<button
					className="relative rounded-full p-2 text-[#64748B] transition-colors hover:bg-[#F7F8FA] hover:text-[#111827] dark:text-[#E2E5E8] dark:hover:bg-[#1E2D3D] dark:hover:text-white"
					aria-label="Сповіщення"
				>
					<Bell className="h-5 w-5" />
					{unreadCount > 0 && (
						<span className="absolute -right-0.5 -top-0.5 flex h-4 w-4 items-center justify-center rounded-full bg-[#C0392B] text-[10px] font-bold text-white">
							{unreadCount > 9 ? "9+" : unreadCount}
						</span>
					)}
				</button>
			</DropdownMenuTrigger>

			<DropdownMenuContent className="w-80 bg-white dark:bg-gray-800 border shadow-lg dark:text-[#F0EDE6]" align="end">
				<DropdownMenuLabel className="flex items-center justify-between border-b pb-2">
					<span className="text-sm font-semibold">Сповіщення</span>
					{unreadCount > 0 && (
						<span className="rounded-full bg-[#C0392B] px-2 py-0.5 text-[10px] font-bold text-white">
							{unreadCount} нових
						</span>
					)}
				</DropdownMenuLabel>
				<DropdownMenuSeparator />

				{notifications.length === 0 ? (
					<div className="flex flex-col items-center gap-3 py-8 px-4">
						<Image
							src="/assets/images/empty-states/empty-announcements.svg"
							alt=""
							width={120}
							height={120}
							className="opacity-60"
						/>
						<p className="text-sm text-[#6B7280] dark:text-[#8FA8B8]">
							Немає нових сповіщень
						</p>
					</div>
				) : (
					<div className="max-h-80 overflow-y-auto">
						{notifications.map((n) => (
							<div
								key={n.id}
								className={`flex flex-col gap-1 px-3 py-2.5 text-sm transition-colors hover:bg-[#F7F8FA] dark:hover:bg-[#1E2D3D] ${
									!n.is_read
										? "border-l-2 border-[#2F6FED] bg-[#EEF3FD]/50 dark:bg-[#1A2E3A]/50"
										: ""
								}`}
							>
								<span className="font-medium text-[#111827] dark:text-[#F0EDE6]">
									{n.title}
								</span>
								<span className="text-xs text-[#6B7280] dark:text-[#8FA8B8] line-clamp-2">
									{n.message}
								</span>
							</div>
						))}
					</div>
				)}
			</DropdownMenuContent>
		</DropdownMenu>
	);
}
