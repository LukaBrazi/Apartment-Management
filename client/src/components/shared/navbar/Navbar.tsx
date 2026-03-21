import Image from "next/image";
import Link from "next/link";
import MobileNavbar from "./MobileNavbar";
import ThemeSwitcher from "./ThemeSwitcher";
import AuthAvatar from "@/components/shared/navbar/AuthAvatar";

export default function Navbar() {
	return (
		<nav className="flex-between fixed z-50 w-full gap-5 border-b border-[#E5E7EB] bg-white/95 backdrop-blur-sm p-4 sm:p-6 lg:px-12 shadow-sm dark:border-[#2D3D4F] dark:bg-[#162032]/90">
			<Link href="/" className="flex items-center gap-2">
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
			</Link>

			<div className="flex items-center gap-4 sm:gap-6 lg:gap-8">
				<ThemeSwitcher />
				<AuthAvatar />
				<MobileNavbar />
			</div>
		</nav>
	);
}
