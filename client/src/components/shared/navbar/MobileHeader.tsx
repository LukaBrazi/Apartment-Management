"use client";

/**
 * Mobile-only top header.
 *
 * Rendered below the `md` breakpoint. Above `md` the existing desktop
 * `<Navbar />` takes over (see `(estate)/layout.tsx`).
 *
 * Structure:
 *   [ ApartmentOS logo ]                    [ 🔔 notif ] [ avatar ]
 *
 * The header deliberately omits the `MobileNavbar` hamburger — the
 * bottom tab bar replaces it. Keeping the logo tappable (links home),
 * the notification bell, and the avatar preserves the three actions a
 * tenant actually uses from the top of the screen.
 */

import Image from "next/image";
import Link from "next/link";
import AuthAvatar from "./AuthAvatar";
import { useGetSiteSettingsQuery } from "@/lib/redux/features/siteSettings/siteSettingsApiSlice";

export default function MobileHeader() {
	const { data: siteSettingsData, isLoading } = useGetSiteSettingsQuery();
	const platformName = siteSettingsData?.settings?.platform_name || "ApartmentOS";
	const customLogo = siteSettingsData?.settings?.logo_url;

	return (
		<header
			className="fixed inset-x-0 top-0 z-40 flex h-14 items-center justify-between border-b border-saas-border bg-white/95 px-4 backdrop-blur-md safe-area-pt md:hidden dark:border-[#2D3D4F] dark:bg-[#162032]/95"
		>
			<Link href="/welcome" className="tap flex items-center" aria-label={platformName}>
				{!isLoading && customLogo ? (
					<img
						src={customLogo}
						alt={platformName}
						className="h-8 w-auto"
						style={{ maxWidth: "120px" }}
					/>
				) : (
					<>
						<Image
							src="/assets/logos/apartmentos-logo-full.svg"
							alt="ApartmentOS"
							width={112}
							height={32}
							className="block h-8 w-auto dark:hidden"
							priority
						/>
						<Image
							src="/assets/logos/apartmentos-logo-full-dark.svg"
							alt="ApartmentOS"
							width={112}
							height={32}
							className="hidden h-8 w-auto dark:block"
							priority
						/>
					</>
				)}
			</Link>

			<div className="flex items-center gap-2">
				<AuthAvatar />
			</div>
		</header>
	);
}
