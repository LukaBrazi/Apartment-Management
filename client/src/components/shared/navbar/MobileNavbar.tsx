"use client";
import { Button } from "@/components/ui/button";
import {
	Sheet,
	SheetClose,
	SheetContent,
	SheetFooter,
	SheetTrigger,
} from "@/components/ui/sheet";
import { leftNavLinks } from "@/constants";
import { useAuthNavigation } from "@/hooks";
import { HomeModernIcon } from "@heroicons/react/24/solid";
import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";

function LeftNavContent() {
	const pathname = usePathname();
	const { filteredNavLinks } = useAuthNavigation();
	return (
		<section className="flex h-full flex-col gap-1 pt-16">
			{filteredNavLinks.map((linkItem) => {
				const isActive =
					(pathname.includes(linkItem.path) && linkItem.path.length > 1) ||
					pathname === linkItem.path;
				return (
					<SheetClose asChild key={linkItem.path}>
						<Link
							href={linkItem.path}
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
							<p className={`${isActive ? "base-semibold" : "base-medium"}`}>
								{linkItem.label}
							</p>
						</Link>
					</SheetClose>
				);
			})}
		</section>
	);
}

export default function MobileNavbar() {
	const { handleLogout, isAuthenticated } = useAuthNavigation();
	return (
		<Sheet>
			<SheetTrigger asChild className="cursor-pointer">
				<Image
					src="/assets/icons/mobile-menu.svg"
					alt="Mobile Menu"
					width={36}
					height={36}
					className="invert-colors sm:hidden"
				/>
			</SheetTrigger>
			<SheetContent
				side="left"
				className="border-r border-[#E2E5E8] bg-white dark:border-[#2D3D4F] dark:bg-[#162032]"
			>
				<Link href="/" className="flex items-center gap-2">
					<HomeModernIcon className="size-9 text-[#3D7A8A]" />
					<p className="h2-semibold font-robotoSlab text-[#1C2B3A] dark:text-[#F0EDE6] tracking-tight">
						Skandi <span className="text-[#3D7A8A]">Apartments</span>
					</p>
				</Link>

				<div className="flex h-full flex-col justify-between pb-8">
					<LeftNavContent />

					<SheetClose asChild>
						<SheetFooter className="flex flex-col gap-3 border-t border-[#E2E5E8] pt-4 dark:border-[#2D3D4F]">
							{isAuthenticated ? (
								<Button
									onClick={handleLogout}
									className="small-medium w-full rounded-xl border border-[#E2E5E8] bg-transparent text-[#1C2B3A] shadow-none hover:bg-[#EBF3F5] hover:text-[#3D7A8A] dark:border-[#2D3D4F] dark:text-[#F0EDE6] dark:hover:bg-[#1A2E3A] dark:hover:text-[#5BA3B5]"
								>
									Вийти
								</Button>
							) : (
								<>
									<Link href="/register" className="w-full">
										<Button className="small-medium w-full rounded-xl bg-[#3D7A8A] text-white shadow-none hover:bg-[#2E6070] dark:bg-[#5BA3B5] dark:hover:bg-[#4A8FA0]">
											Реєстрація
										</Button>
									</Link>
									<Link href="/login" className="w-full">
										<Button className="small-medium w-full rounded-xl border border-[#3D7A8A] bg-transparent text-[#3D7A8A] shadow-none hover:bg-[#EBF3F5] dark:border-[#5BA3B5] dark:text-[#5BA3B5] dark:hover:bg-[#1A2E3A]">
											Увійти
										</Button>
									</Link>
								</>
							)}
						</SheetFooter>
					</SheetClose>
				</div>
			</SheetContent>
		</Sheet>
	);
}
