"use client";
import { Button } from "@/components/ui/button";
import { leftNavLinks } from "@/constants";
import { useAuthNavigation } from "@/hooks";
import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";

export default function LeftNavbar() {
	const pathname = usePathname();
	const { handleLogout, filteredNavLinks, isAuthenticated } =
		useAuthNavigation();
	return (
		<section className="custom-scrollbar sticky left-0 top-0 flex h-screen flex-col justify-between overflow-y-auto border-r border-[#E2E5E8] bg-white p-6 pt-36 max-sm:hidden lg:w-[280px] dark:border-[#2D3D4F] dark:bg-[#162032]">
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
									? "bg-[#EBF3F5] text-[#3D7A8A] dark:bg-[#1A2E3A] dark:text-[#5BA3B5]"
									: "text-[#6B7F8C] hover:bg-[#F7F6F2] hover:text-[#1C2B3A] dark:text-[#8FA8B8] dark:hover:bg-[#1E2D3D] dark:hover:text-[#F0EDE6]"
							}`}
						>
							<Image
								src={linkItem.imgLocation}
								alt={linkItem.label}
								width={20}
								height={20}
								className={`${isActive ? "opacity-100" : "opacity-60 dark:invert"}`}
							/>
							<p className={`${isActive ? "base-semibold" : "base-medium"} max-lg:hidden`}>
								{linkItem.label}
							</p>
						</Link>
					);
				})}
			</div>

			{isAuthenticated ? (
				<div className="flex flex-col gap-3 pt-4 border-t border-[#E2E5E8] dark:border-[#2D3D4F]">
					<Button
						onClick={handleLogout}
						className="small-medium w-full rounded-xl border border-[#E2E5E8] bg-transparent px-4 py-3 text-[#1C2B3A] shadow-none transition-colors hover:bg-[#EBF3F5] hover:text-[#3D7A8A] dark:border-[#2D3D4F] dark:text-[#F0EDE6] dark:hover:bg-[#1A2E3A] dark:hover:text-[#5BA3B5]"
					>
						Вийти
					</Button>
				</div>
			) : (
				<div className="flex flex-col gap-3 pt-4 border-t border-[#E2E5E8] dark:border-[#2D3D4F]">
					<Link href="/login">
						<Button className="small-medium w-full rounded-xl border border-[#3D7A8A] bg-transparent px-4 py-3 text-[#3D7A8A] shadow-none transition-colors hover:bg-[#EBF3F5] dark:border-[#5BA3B5] dark:text-[#5BA3B5] dark:hover:bg-[#1A2E3A]">
							Увійти
						</Button>
					</Link>
					<Link href="/register">
						<Button className="small-medium w-full rounded-xl bg-[#3D7A8A] px-4 py-3 text-white shadow-none transition-colors hover:bg-[#2E6070] dark:bg-[#5BA3B5] dark:hover:bg-[#4A8FA0]">
							Реєстрація
						</Button>
					</Link>
				</div>
			)}
		</section>
	);
}
