"use client";
import { Button } from "@/components/ui/button";
import {
	DropdownMenu,
	DropdownMenuContent,
	DropdownMenuItem,
	DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { MoonIcon, SunIcon } from "@radix-ui/react-icons";
import { useTheme } from "next-themes";

const themeOptions = [
	{ value: "light", label: "Світла" },
	{ value: "dark", label: "Темна" },
	{ value: "system", label: "Системна" },
];

export default function ThemeSwitcher() {
	const { theme, setTheme } = useTheme();

	return (
		<DropdownMenu>
			<DropdownMenuTrigger
				asChild
				className="cursor-pointer border-none bg-transparent shadow-none"
			>
				<Button size="icon" variant="ghost" className="rounded-xl text-[#6B7F8C] hover:bg-[#EBF3F5] hover:text-[#3D7A8A] dark:text-[#8FA8B8] dark:hover:bg-[#1A2E3A] dark:hover:text-[#5BA3B5]">
					<SunIcon
						className="size-5 rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0"
						suppressHydrationWarning
					/>
					<MoonIcon
						className="absolute size-5 rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100"
						suppressHydrationWarning
					/>
					<span className="sr-only">Змінити тему</span>
				</Button>
			</DropdownMenuTrigger>
			<DropdownMenuContent
				align="end"
				className="rounded-xl border border-[#E2E5E8] bg-white p-1 shadow-md dark:border-[#2D3D4F] dark:bg-[#1E2D3D]"
			>
				{themeOptions.map(({ value, label }) => (
					<DropdownMenuItem
						key={value}
						onClick={() => setTheme(value)}
						className={`cursor-pointer rounded-lg px-3 py-2 text-sm transition-colors ${
							theme === value
								? "bg-[#EBF3F5] text-[#3D7A8A] dark:bg-[#1A2E3A] dark:text-[#5BA3B5]"
								: "text-[#1C2B3A] hover:bg-[#F7F6F2] dark:text-[#F0EDE6] dark:hover:bg-[#162032]"
						}`}
					>
						{label}
					</DropdownMenuItem>
				))}
			</DropdownMenuContent>
		</DropdownMenu>
	);
}
