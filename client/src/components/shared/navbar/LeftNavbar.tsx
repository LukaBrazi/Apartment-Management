"use client";
import { Button } from "@/components/ui/button";
import { NavIcon } from "@/components/shared/NavIcon";
import { leftNavLinks } from "@/constants";
import { useAuthNavigation } from "@/hooks";
import Link from "next/link";
import { usePathname } from "next/navigation";

export default function LeftNavbar() {
	const pathname = usePathname();
	const { handleLogout, filteredNavLinks, isAuthenticated } =
		useAuthNavigation();
	return (
		<section className="custom-scrollbar sticky left-0 top-0 flex h-screen flex-col justify-between overflow-y-auto border-r border-[#E5E7EB] bg-[#FFFFFF] p-6 pt-36 max-sm:hidden lg:w-[240px] dark:border-[#2D3D4F] dark:bg-[#162032]">
			<div className="flex flex-1 flex-col gap-1">
				{filteredNavLinks.map((linkItem) => {
					const isActive =
						(pathname.includes(linkItem.path) && linkItem.path.length > 1) ||
						pathname === linkItem.path;
					return (
						<Link
							href={linkItem.path}
							key={linkItem.label}
							className={`flex items-center justify-start gap-3 rounded-xl px-4 py-3 transition-all duration-150 ${
								isActive
									? "bg-[#EEF3FD] text-[#2F6FED] dark:bg-[#1A2E3A] dark:text-[#5BA3B5]"
									: "text-[#6B7280] hover:bg-[#F7F8FA] hover:text-[#111827] dark:text-[#8FA8B8] dark:hover:bg-[#1E2D3D] dark:hover:text-[#F0EDE6]"
							}`}
						>
							<NavIcon
								path={linkItem.path}
								className={`size-5 ${isActive ? "text-[#2F6FED] dark:text-[#5BA3B5]" : "text-[#6B7280] dark:text-[#8FA8B8]"}`}
							/>
							<p className={`${isActive ? "base-semibold" : "base-medium"} max-lg:hidden`}>
								{linkItem.label}
							</p>
						</Link>
					);
				})}
			</div>

			{isAuthenticated ? (
				<div className="flex flex-col gap-3 pt-4 border-t border-[#E5E7EB] dark:border-[#2D3D4F]">
					<Button
						onClick={handleLogout}
						className="small-medium w-full rounded-xl border border-[#E5E7EB] bg-transparent px-4 py-3 text-[#111827] shadow-none transition-colors hover:bg-[#EEF3FD] hover:text-[#2F6FED] dark:border-[#2D3D4F] dark:text-[#F0EDE6] dark:hover:bg-[#1A2E3A] dark:hover:text-[#5BA3B5]"
					>
						Вийти
					</Button>
				</div>
			) : (
				<div className="flex flex-col gap-3 pt-4 border-t border-[#E5E7EB] dark:border-[#2D3D4F]">
					<Link href="/login">
						<Button className="small-medium w-full rounded-xl border border-[#2F6FED] bg-transparent px-4 py-3 text-[#2F6FED] shadow-none transition-colors hover:bg-[#EEF3FD] dark:border-[#5BA3B5] dark:text-[#5BA3B5] dark:hover:bg-[#1A2E3A]">
							Увійти
						</Button>
					</Link>
				</div>
			)}
		</section>
	);
}
