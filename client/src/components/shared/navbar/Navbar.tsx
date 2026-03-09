import { HomeModernIcon } from "@heroicons/react/24/solid";
import Link from "next/link";
import MobileNavbar from "./MobileNavbar";
import ThemeSwitcher from "./ThemeSwitcher";
import AuthAvatar from "@/components/shared/navbar/AuthAvatar";

export default function Navbar() {
	return (
		<nav className="flex-between fixed z-50 w-full gap-5 border-b border-[#E2E5E8] bg-white/90 backdrop-blur-sm p-4 sm:p-6 lg:px-12 shadow-sm dark:border-[#2D3D4F] dark:bg-[#162032]/90">
			<Link href="/" className="flex items-center gap-2">
				<HomeModernIcon className="size-9 text-[#3D7A8A]" />
				<p className="h2-semibold font-robotoSlab text-[#1C2B3A] dark:text-[#F0EDE6] hidden sm:block tracking-tight">
					Skandi <span className="text-[#3D7A8A]">Apartments</span>
				</p>
			</Link>

			<div className="flex items-center gap-4 sm:gap-6 lg:gap-8">
				<ThemeSwitcher />
				<AuthAvatar />
				<MobileNavbar />
			</div>
		</nav>
	);
}
