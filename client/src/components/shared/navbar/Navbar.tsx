import { HomeModernIcon } from "@heroicons/react/24/solid";
import Link from "next/link";
import MobileNavbar from "./MobileNavbar";
import ThemeSwitcher from "./ThemeSwitcher";
import AuthAvatar from "@/components/shared/navbar/AuthAvatar";

export default function Navbar() {
	return (
		<nav className="flex-between fixed z-50 w-full gap-5 border-b border-[#E5E7EB] bg-white/95 backdrop-blur-sm p-4 sm:p-6 lg:px-12 shadow-sm dark:border-[#2D3D4F] dark:bg-[#162032]/90">
			<Link href="/" className="flex items-center gap-2">
				<HomeModernIcon className="size-9 text-[#2F6FED]" />
				<p className="h2-semibold font-robotoSlab text-[#111827] dark:text-[#F0EDE6] hidden sm:block tracking-tight">
					Skandi <span className="text-[#2F6FED]">Apartments</span>
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
