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

	// Mobile-first paddings: tight 4/4 on narrow screens, generous 6/5
	// at md+ (the pre-existing desktop look). `flex-wrap` lets the
	// building/unit pill bar fall onto its own line on narrow screens
	// instead of squeezing the name column.
	const shell =
		"flex flex-wrap items-center gap-3 rounded-2xl border border-[#E5E7EB] bg-white p-4 shadow-sm md:gap-4 md:px-6 md:py-5 dark:border-[#2D3D4F] dark:bg-[#162032]";

	if (isLoading) {
		return (
			<div className={shell}>
				<div className="h-11 w-11 animate-pulse rounded-full bg-[#EEF3FD] md:h-12 md:w-12" />
				<div className="min-w-0 flex-1 space-y-2">
					<div className="h-5 w-48 animate-pulse rounded bg-[#F3F4F6] dark:bg-[#1E2D3D]" />
					<div className="h-4 w-36 animate-pulse rounded bg-[#F3F4F6] dark:bg-[#1E2D3D]" />
				</div>
				<div className="h-7 w-28 animate-pulse rounded-lg bg-[#EEF3FD]" />
			</div>
		);
	}

	return (
		<div className={shell}>
			{/* Avatar */}
			<div className="flex h-11 w-11 flex-shrink-0 items-center justify-center rounded-full bg-[#EEF3FD] text-lg font-bold text-[#2F6FED] md:h-12 md:w-12">
				{initial}
			</div>

			{/* Name + date */}
			<div className="min-w-0 flex-1">
				<p className="text-lg font-bold text-[#111827] md:text-xl dark:text-[#F0EDE6]">
					{firstName ? `Вітаємо, ${firstName}!` : "Вітаємо!"}
				</p>
				<p className="mt-0.5 truncate text-xs text-[#6B7280] md:text-sm dark:text-[#8FA8B8]">
					{capitalizedDate}
				</p>
			</div>

			{/* Building + unit badges — wrap to a second row on narrow screens */}
			<div className="flex w-full flex-wrap items-center gap-2 md:w-auto">
				{buildingName && buildingName !== "—" && (
					<span className="flex min-w-0 items-center gap-1.5 rounded-lg bg-[#EEF3FD] px-3 py-1.5 text-xs font-medium text-[#2F6FED] md:text-sm">
						<Building2 className="h-4 w-4 flex-shrink-0" />
						<span className="truncate">{buildingName}</span>
					</span>
				)}
				{unitNumber && unitNumber !== "—" && (
					<span className="flex-shrink-0 rounded-lg bg-[#F3F4F6] px-3 py-1.5 text-xs font-semibold text-[#374151] md:text-sm dark:bg-[#1E2D3D] dark:text-[#D1D5DB]">
						кв. {unitNumber}
					</span>
				)}
			</div>
		</div>
	);
}
