import { HomeModernIcon } from "@heroicons/react/24/solid";
import Link from "next/link";

type FormHeaderProps = {
	title?: string;
	staticText?: string;
	linkText?: string;
	linkHref?: string;
};

export default function AuthFormHeader({
	title,
	staticText,
	linkHref,
	linkText,
}: FormHeaderProps) {
	return (
		<div className="px-4 sm:mx-auto sm:w-full sm:max-w-md sm:px-6 lg:px-8">
			<HomeModernIcon className="mx-auto size-14 text-[#3D7A8A] dark:text-[#5BA3B5]" />
			<h2 className="mt-4 text-center text-[22px] font-semibold tracking-tight text-[#1C2B3A] dark:text-[#F0EDE6] font-robotoSlab">
				{title}
			</h2>
			{(staticText || linkText) && linkHref && (
				<p className="mt-3 text-center text-sm text-[#6B7F8C] dark:text-[#8FA8B8]">
					{staticText && <span>{staticText}</span>}
					{linkText && (
						<Link
							href={linkHref}
							className="ml-1 font-medium text-[#3D7A8A] hover:text-[#2E6070] dark:text-[#5BA3B5] dark:hover:text-[#4A8FA0] underline-offset-4 hover:underline"
						>
							{linkText}
						</Link>
					)}
				</p>
			)}
		</div>
	);
}
