"use client";

import AdminGuard from "@/components/admin/AdminGuard";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
	LayoutDashboard,
	Users,
	Wrench,
	ClipboardList,
	Car,
	Newspaper,
	Building2,
	ExternalLink,
	Bot,
} from "lucide-react";

import { useAppSelector } from "@/lib/redux/hooks/typedHooks";
import { useGetUserProfileQuery } from "@/lib/redux/features/users/usersApiSlice";

const adminNavLinks = [
	{ path: "/admin", label: "Дашборд", icon: LayoutDashboard },
	{ path: "/admin/residents", label: "Мешканці", icon: Users },
	{ path: "/admin/workers", label: "Працівники", icon: Wrench },
	{ path: "/admin/issues", label: "Заявки", icon: ClipboardList },
	{ path: "/admin/passes", label: "Перепустки", icon: Car },
	{ path: "/admin/buildings", label: "Будинки", icon: Building2 },
	{ path: "/admin/posts", label: "Новини", icon: Newspaper },
	{ path: "/admin/news", label: "Новини (портал)", icon: Newspaper },
];

// Super_admin-only entries — kept separate so we can render them as a
// visually distinct group (platform-wide controls, not org-scoped).
const superAdminNavLinks = [
	{ path: "/admin/telegram-bot", label: "Telegram боти", icon: Bot },
];

export default function AdminLayout({
	children,
}: {
	children: React.ReactNode;
}) {
	const pathname = usePathname();
	const { isAuthenticated } = useAppSelector((state) => state.auth);
	const { data: profileData } = useGetUserProfileQuery(undefined, {
		skip: !isAuthenticated,
	});
	const isSuperuser = profileData?.profile?.is_superuser ?? false;

	return (
		<AdminGuard>
			<div className="flex min-h-screen bg-[#F7F6F2] dark:bg-[#0F1923]">
				{/* Sidebar */}
				<aside className="fixed left-0 top-0 h-full w-60 bg-[#1C2B3A] flex flex-col z-40 shadow-xl">
					{/* Logo / Brand */}
					<div className="px-6 py-5 border-b border-[#2D3D4F]">
						<h1 className="text-white font-semibold text-sm leading-tight">
							ApartmentOS
						</h1>
						<p className="text-[#5BA3B5] text-xs mt-0.5">Адмін панель</p>
					</div>

					{/* Nav Links */}
					<nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
						{adminNavLinks.map(({ path, label, icon: Icon }) => {
							const isActive =
								path === "/admin"
									? pathname === "/admin"
									: pathname.startsWith(path);

							return (
								<Link
									key={path}
									href={path}
									className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
										isActive
											? "bg-[#EBF3F5] text-[#3D7A8A]"
											: "text-[#A8BFCC] hover:bg-[#243548] hover:text-white"
									}`}
								>
									<Icon className="h-4 w-4 flex-shrink-0" />
									{label}
								</Link>
							);
						})}

						{isSuperuser && (
							<>
								<div className="pt-4 pb-1 px-3 text-[10px] font-semibold uppercase tracking-wider text-[#5BA3B5]">
									Платформа
								</div>
								{superAdminNavLinks.map(({ path, label, icon: Icon }) => {
									const isActive = pathname.startsWith(path);
									return (
										<Link
											key={path}
											href={path}
											className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
												isActive
													? "bg-[#EBF3F5] text-[#3D7A8A]"
													: "text-[#A8BFCC] hover:bg-[#243548] hover:text-white"
											}`}
										>
											<Icon className="h-4 w-4 flex-shrink-0" />
											{label}
										</Link>
									);
								})}
							</>
						)}
					</nav>

					{/* Back to site */}
					<div className="px-3 py-4 border-t border-[#2D3D4F]">
						<Link
							href="/"
							className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium text-[#A8BFCC] hover:bg-[#243548] hover:text-white transition-colors"
						>
							<ExternalLink className="h-4 w-4 flex-shrink-0" />
							На сайт
						</Link>
					</div>
				</aside>

				{/* Main Content */}
				<div className="ml-60 flex-1 flex flex-col min-h-screen">
					{/* Top Bar */}
					<header className="sticky top-0 z-30 h-14 bg-white dark:bg-[#162032] border-b border-[#E2E5E8] dark:border-[#2D3D4F] flex items-center px-6 shadow-sm">
						<span className="text-sm font-medium text-[#1C2B3A] dark:text-white">
							ApartmentOS —{" "}
							<span className="text-[#3D7A8A]">Адмін панель</span>
						</span>
					</header>

					{/* Page Content */}
					<main className="flex-1 p-6 overflow-y-auto">{children}</main>
				</div>
			</div>
		</AdminGuard>
	);
}
