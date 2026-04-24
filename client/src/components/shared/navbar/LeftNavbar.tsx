"use client";

import { NavIcon } from "@/components/shared/NavIcon";
import { useAuthNavigation } from "@/hooks";
import { useGetMyIssuesQuery } from "@/lib/redux/features/issues/issueApiSlice";
import { useGetMyPassesQuery } from "@/lib/redux/features/passes/passApiSlice";
import { useGetTenantAnnouncementsQuery } from "@/lib/redux/features/posts/postApiSlice";
import { useUserProfile } from "@/hooks/useUseProfile";
import { Building2, LogOut } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAppSelector } from "@/lib/redux/hooks/typedHooks";

export default function LeftNavbar() {
	const pathname = usePathname();
	const { handleLogout, filteredNavLinks, isAuthenticated } = useAuthNavigation();
	const { profile } = useUserProfile();
	const { isAuthenticated: authState } = useAppSelector((state) => state.auth);

	const { data: issuesData } = useGetMyIssuesQuery(undefined, { skip: !authState });
	const { data: passesData } = useGetMyPassesQuery(undefined, { skip: !authState });
	const { data: announcementsData } = useGetTenantAnnouncementsQuery(undefined, { skip: !authState });

	// Use total `.count` from the paginated API response — filtering paginated
	// `.results` (max 10 per page) would give wrong counts for users with many items.
	const openIssuesCount = issuesData?.my_issues?.count ?? 0;
	const pendingPassesCount = passesData?.count ?? 0;
	const announcementsCount = announcementsData?.count ?? 0;

	const getBadgeCount = (path: string): number => {
		if (path === "/profile?tab=my-issues" || path === "/report-issue") return openIssuesCount;
		if (path === "/request-pass" || path === "/my-passes") return pendingPassesCount;
		if (path === "/news") return announcementsCount;
		return 0;
	};

	const fullName =
		[profile?.first_name, profile?.last_name].filter(Boolean).join(" ") || "Мешканець";
	const initial = profile?.first_name?.charAt(0)?.toUpperCase() ?? "?";
	const roleLabel =
		profile?.occupation === "tenant"
			? "Орендар"
			: profile?.occupation === "guard"
			? "Охорона"
			: profile?.occupation
			? "Персонал"
			: "";

	return (
		<section
			className="custom-scrollbar sticky left-0 top-0 flex h-screen flex-col overflow-y-auto max-sm:hidden lg:w-[240px]"
			style={{ backgroundColor: "#1E2761" }}
		>
			{/* Header — logo */}
			<div className="flex items-center gap-3 px-5 py-5">
				<div
					className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-xl"
					style={{ backgroundColor: "#CADCFC" }}
				>
					<Building2 className="h-5 w-5" style={{ color: "#1E2761" }} />
				</div>
				<span className="text-xl font-bold text-white">ApartmentOS</span>
			</div>

			{/* Apartment chip */}
			<div
				className="mx-3 mb-2 rounded-xl px-4 py-3"
				style={{ backgroundColor: "rgba(255,255,255,0.1)" }}
			>
				<p
					className="text-[10px] uppercase tracking-widest"
					style={{ color: "#CADCFC" }}
				>
					Ваша квартира
				</p>
				<p className="text-sm font-semibold text-white">
					{profile?.unit_number ?? "—"}
				</p>
				<p className="text-xs" style={{ color: "rgba(255,255,255,0.6)" }}>
					{profile?.building_name ?? "—"}
				</p>
			</div>

			{/* Nav items */}
			<nav className="flex flex-1 flex-col gap-1 px-3 py-2">
				{filteredNavLinks.map((linkItem) => {
					const isActive =
						(pathname.includes(linkItem.path) && linkItem.path.length > 1) ||
						pathname === linkItem.path;
					const badgeCount = getBadgeCount(linkItem.path);

					return (
						<Link
							href={linkItem.path}
							key={linkItem.label}
							className="flex items-center justify-between gap-3 rounded-xl px-4 py-3 transition-all duration-150"
							style={
								isActive
									? { backgroundColor: "#CADCFC" }
									: undefined
							}
							onMouseEnter={(e) => {
								if (!isActive) {
									(e.currentTarget as HTMLElement).style.backgroundColor =
										"rgba(255,255,255,0.08)";
								}
							}}
							onMouseLeave={(e) => {
								if (!isActive) {
									(e.currentTarget as HTMLElement).style.backgroundColor =
										"transparent";
								}
							}}
						>
							<div className="flex items-center gap-3">
								<NavIcon
									path={linkItem.path}
									className="size-5"
									style={{ color: isActive ? "#1E2761" : "rgba(255,255,255,0.7)" }}
								/>
								<p
									className="max-lg:hidden text-sm"
									style={{
										color: isActive ? "#1E2761" : "rgba(255,255,255,0.7)",
										fontWeight: isActive ? 600 : 400,
									}}
								>
									{linkItem.label}
								</p>
							</div>
							{badgeCount > 0 && (
								<span
									className="flex h-5 min-w-[20px] items-center justify-center rounded-full px-1.5 text-[11px] font-semibold"
									style={
										isActive
											? { backgroundColor: "#1E2761", color: "#ffffff" }
											: {
													backgroundColor: "rgba(255,255,255,0.15)",
													color: "rgba(255,255,255,0.9)",
											  }
									}
								>
									{badgeCount}
								</span>
							)}
						</Link>
					);
				})}
			</nav>

			{/* User footer */}
			<div
				className="mx-0 px-4 py-4"
				style={{ borderTop: "1px solid rgba(255,255,255,0.1)" }}
			>
				{isAuthenticated ? (
					<div className="flex items-center justify-between">
						<div className="flex items-center gap-2.5">
							<div
								className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-full text-sm font-bold"
								style={{ backgroundColor: "#CADCFC", color: "#1E2761" }}
							>
								{initial}
							</div>
							<div className="max-lg:hidden">
								<p className="text-[13px] font-semibold text-white leading-tight">
									{fullName}
								</p>
								<p
									className="text-[11px] leading-tight"
									style={{ color: "rgba(255,255,255,0.6)" }}
								>
									{roleLabel}
								</p>
							</div>
						</div>
						<button
							onClick={handleLogout}
							className="max-lg:hidden flex items-center justify-center rounded-lg p-1.5 transition-colors"
							title="Вийти"
							onMouseEnter={(e) => {
								(e.currentTarget as HTMLElement).style.color = "#ffffff";
							}}
							onMouseLeave={(e) => {
								(e.currentTarget as HTMLElement).style.color =
									"rgba(255,255,255,0.5)";
							}}
							style={{ color: "rgba(255,255,255,0.5)" }}
						>
							<LogOut className="h-4 w-4" />
						</button>
					</div>
				) : (
					<Link
						href="/login"
						className="flex items-center justify-center rounded-xl px-4 py-2 text-sm font-semibold text-white transition-all duration-150"
						style={{ backgroundColor: "rgba(255,255,255,0.15)" }}
					>
						Увійти
					</Link>
				)}
			</div>
		</section>
	);
}
