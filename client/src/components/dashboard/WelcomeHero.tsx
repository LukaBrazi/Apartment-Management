"use client";

import { Building2 } from "lucide-react";
import { format } from "date-fns";
import { uk } from "date-fns/locale";

interface WelcomeHeroProps {
	firstName?: string;
	buildingName?: string;
	unitNumber?: string;
	isLoading?: boolean;
}

export default function WelcomeHero({
	firstName,
	buildingName,
	unitNumber,
	isLoading,
}: WelcomeHeroProps) {
	const today = format(new Date(), "EEEE, d MMMM yyyy", { locale: uk });
	const capitalizedDate = today.charAt(0).toUpperCase() + today.slice(1);
	const initial = firstName ? firstName.charAt(0).toUpperCase() : "?";

	if (isLoading) {
		return (
			<div className="flex flex-wrap items-center gap-4 rounded-2xl border border-[#E5E7EB] bg-white px-6 py-5 shadow-sm dark:border-[#2D3D4F] dark:bg-[#162032]">
				<div className="h-12 w-12 animate-pulse rounded-full bg-[#EEF3FD]" />
				<div className="flex-1 space-y-2">
					<div className="h-5 w-48 animate-pulse rounded bg-[#F3F4F6] dark:bg-[#1E2D3D]" />
					<div className="h-4 w-36 animate-pulse rounded bg-[#F3F4F6] dark:bg-[#1E2D3D]" />
				</div>
				<div className="h-7 w-28 animate-pulse rounded-lg bg-[#EEF3FD]" />
			</div>
		);
	}

	return (
		<div className="flex flex-wrap items-center gap-4 rounded-2xl border border-[#E5E7EB] bg-white px-6 py-5 shadow-sm dark:border-[#2D3D4F] dark:bg-[#162032]">
			{/* Avatar */}
			<div className="flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-full bg-[#EEF3FD] text-lg font-bold text-[#2F6FED]">
				{initial}
			</div>

			{/* Name + date */}
			<div className="flex-1 min-w-0">
				<p className="text-xl font-bold text-[#111827] dark:text-[#F0EDE6]">
					{firstName ? `Вітаємо, ${firstName}!` : "Вітаємо!"}
				</p>
				<p className="mt-0.5 text-sm text-[#6B7280] dark:text-[#8FA8B8]">
					{capitalizedDate}
				</p>
			</div>

			{/* Building + unit badges */}
			<div className="flex flex-wrap items-center gap-2">
				{buildingName && buildingName !== "—" && (
					<span className="flex items-center gap-1.5 rounded-lg bg-[#EEF3FD] px-3 py-1.5 text-sm font-medium text-[#2F6FED]">
						<Building2 className="h-4 w-4" />
						{buildingName}
					</span>
				)}
				{unitNumber && unitNumber !== "—" && (
					<span className="rounded-lg bg-[#F3F4F6] px-3 py-1.5 text-sm font-semibold text-[#374151] dark:bg-[#1E2D3D] dark:text-[#D1D5DB]">
						кв. {unitNumber}
					</span>
				)}
			</div>
		</div>
	);
}
