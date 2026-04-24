"use client";
// CabinetTopbar: breadcrumbs + search + bell + user chip
// Desktop only (hidden on mobile via parent layout)

import { usePathname } from "next/navigation";
import { Search } from "lucide-react";
import { useUserProfile } from "@/hooks/useUseProfile";
import NotificationBell from "./NotificationBell";
import Link from "next/link";

// Route → breadcrumb label map
const CRUMB_MAP: Record<string, string> = {
	"/welcome": "Dashboard",
	"/profile": "Профіль",
	"/my-passes": "Перепустки",
	"/news": "Оголошення",
	"/payments": "Платежі",
	"/contacts": "Контакти",
	"/report-issue": "Нова заявка",
	"/request-pass": "Нова перепустка",
	"/admin": "Адміністрування",
	"/guard-portal": "Портал охорони",
};

export default function CabinetTopbar() {
	const pathname = usePathname();
	const { profile } = useUserProfile();

	const label =
		CRUMB_MAP[pathname] ??
		CRUMB_MAP[Object.keys(CRUMB_MAP).find((k) => pathname.startsWith(k)) ?? ""] ??
		"Кабінет";
	const initial = profile?.first_name?.charAt(0)?.toUpperCase() ?? "?";
	const fullName =
		[profile?.first_name, profile?.last_name].filter(Boolean).join(" ") || "Мешканець";
	const role =
		profile?.occupation === "tenant"
			? "Орендар"
			: profile?.occupation === "guard"
			? "Охорона"
			: profile?.occupation
			? "Персонал"
			: "Мешканець";

	return (
		<div className="hidden md:flex h-16 items-center justify-between gap-6 border-b border-[#F1F5F9] bg-white px-8">
			{/* Breadcrumbs */}
			<div className="flex items-center gap-2 text-sm">
				<span className="text-[#64748B]">ApartmentOS</span>
				<svg
					width="14"
					height="14"
					viewBox="0 0 24 24"
					fill="none"
					stroke="#CBD5E1"
					strokeWidth="2"
					strokeLinecap="round"
					strokeLinejoin="round"
				>
					<path d="M9 18l6-6-6-6" />
				</svg>
				<span className="font-semibold text-[#0F172A]">{label}</span>
			</div>

			{/* Search */}
			<div className="relative flex-1 max-w-md">
				<Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-[#94A3B8]" />
				<input
					placeholder="Пошук по заявках, перепустках…"
					className="w-full rounded-xl border border-[#E2E8F0] bg-[#F8FAFC] py-2.5 pl-9 pr-4 text-[13px] text-[#0F172A] outline-none placeholder:text-[#94A3B8] focus:border-[#CADCFC] focus:ring-2 focus:ring-[#CADCFC]/30"
				/>
			</div>

			{/* Right: bell + user */}
			<div className="flex items-center gap-3">
				<NotificationBell />
				<Link
					href="/profile"
					className="flex items-center gap-2.5 rounded-xl px-2 py-1.5 transition-colors hover:bg-[#F1F5F9]"
				>
					<div className="flex h-8 w-8 items-center justify-center rounded-full bg-[#1E2761] text-[13px] font-semibold text-white">
						{initial}
					</div>
					<div className="hidden lg:block">
						<p className="text-[13px] font-semibold text-[#0F172A]">{fullName}</p>
						<p className="text-[11px] text-[#64748B]">{role}</p>
					</div>
				</Link>
			</div>
		</div>
	);
}
