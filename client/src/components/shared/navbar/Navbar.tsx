"use client";

import Image from "next/image";
import Link from "next/link";
import MobileNavbar from "./MobileNavbar";
import NotificationBell from "./NotificationBell";
import ThemeSwitcher from "./ThemeSwitcher";
import AuthAvatar from "@/components/shared/navbar/AuthAvatar";
import { useGetSiteSettingsQuery } from "@/lib/redux/features/siteSettings/siteSettingsApiSlice";

/**
 * Navigation bar component with dynamic branding from site settings.
 * Falls back to Skandi Apartments logo if settings fetch fails.
 */
export default function Navbar() {
	const { data: siteSettingsData, isLoading, error } = useGetSiteSettingsQuery();

	// Fallback alt text
	const platformName = siteSettingsData?.settings?.platform_name || "Skandi Apartments";

	return (
		<nav className="flex-between fixed z-50 w-full gap-5 border-b border-[#E5E7EB] bg-white/95 backdrop-blur-sm p-4 sm:p-6 lg:px-12 shadow-sm dark:border-[#2D3D4F] dark:bg-[#162032]/90">
			<Link href="/" className="flex items-center gap-2">
				{/* Display custom logo if available, otherwise fall back to Skandi logo */}
				{!isLoading && siteSettingsData?.settings?.logo_url ? (
					<>
						{/* Light mode custom logo */}
						<img
							src={siteSettingsData.settings.logo_url}
							alt={platformName}
							className="h-10 dark:hidden"
							style={{ maxWidth: "140px" }}
						/>
						{/* Dark mode custom logo (if different) or same */}
						<img
							src={siteSettingsData.settings.logo_url}
							alt={platformName}
							className="hidden h-10 dark:block"
							style={{ maxWidth: "140px" }}
						/>
					</>
				) : (
					<>
						{/* Light mode logo */}
						<Image
							src="/assets/logos/skandi-logo-full.svg"
							alt="Skandi Apartments"
							width={140}
							height={40}
							className="block dark:hidden"
							priority
						/>
						{/* Dark mode logo */}
						<Image
							src="/assets/logos/skandi-logo-full-dark.svg"
							alt="Skandi Apartments"
							width={140}
							height={40}
							className="hidden dark:block"
							priority
						/>
					</>
				)}
			</Link>

			<div className="flex items-center gap-4 sm:gap-6 lg:gap-8">
				<ThemeSwitcher />
				<NotificationBell />
				<AuthAvatar />
				<MobileNavbar />
			</div>
		</nav>
	);
}
