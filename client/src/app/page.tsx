import { ArrowRightIcon } from "@heroicons/react/24/solid";
import type { Metadata } from "next";
import Image from "next/image";
import Link from "next/link";

export const metadata: Metadata = {
	title: "Home | Skandi Apartments",
	description:
		"Skandi Apartments Home Page. Create your account to get started.",
};

interface SiteLink {
	id: number;
	label: string;
	url: string;
	order: number;
	open_in_new_tab: boolean;
}

interface SiteSettings {
	hero_title: string;
	hero_subtitle: string;
	hero_image_url: string | null;
	cta_text: string;
	cta_url: string;
	links: SiteLink[];
}

const DEFAULTS: SiteSettings = {
	hero_title: "Welcome to Skandi Apartments",
	hero_subtitle: "Are you a new tenant? Or an existing tenant?",
	hero_image_url: null,
	cta_text: "Create Your Account",
	cta_url: "/register",
	links: [],
};

async function getSiteSettings(): Promise<SiteSettings> {
	const apiBase =
		process.env.NEXT_PUBLIC_API_URL ?? "http://nginx:80";
	try {
		const res = await fetch(`${apiBase}/api/v1/site-settings/`, {
			next: { revalidate: 60 },
		});
		if (!res.ok) return DEFAULTS;
		const json = await res.json();
		return (json.site_settings as SiteSettings) ?? DEFAULTS;
	} catch {
		return DEFAULTS;
	}
}

export default async function HomePage() {
	const settings = await getSiteSettings();

	return (
		<div className="relative h-screen w-full overflow-hidden bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
			{/* Full-screen photo fallback (CMS override) */}
			{settings.hero_image_url && (
				<>
					<img
						src={settings.hero_image_url}
						alt="Hero"
						className="absolute inset-0 h-full w-full object-cover object-center"
					/>
					<div className="absolute inset-0 z-10 bg-black/40" />
				</>
			)}

			{/* Split layout: text left, illustration right */}
			<main className="relative z-20 flex h-full items-center">
				{/* Left — text content */}
				<div className="flex w-full flex-col items-center justify-center px-6 text-center sm:w-1/2 sm:items-start sm:text-left sm:pl-12 lg:pl-20">
					<h1 className="font-robotoSlab mb-4 text-4xl font-semibold text-cyan-400 antialiased sm:text-5xl lg:text-7xl">
						{settings.hero_title}
					</h1>
					<p className="my-6 text-xl text-teal-300 sm:text-2xl">
						{settings.hero_subtitle}
					</p>
					<Link href={settings.cta_url} prefetch={false}>
						<button className="bg-asparagus rounded-3xl px-6 py-3 text-lg font-semibold text-white hover:bg-lime-700 sm:text-xl">
							<span className="inline-flex items-center">
								{settings.cta_text}
								<ArrowRightIcon className="ml-2 size-6" />
							</span>
						</button>
					</Link>

					{/* Quick links from admin */}
					{settings.links.length > 0 && (
						<div className="mt-8 flex flex-wrap justify-center gap-4 sm:justify-start">
							{settings.links.map((link) => (
								<Link
									key={link.id}
									href={link.url}
									target={link.open_in_new_tab ? "_blank" : undefined}
									rel={link.open_in_new_tab ? "noopener noreferrer" : undefined}
									className="rounded-xl bg-white/20 px-4 py-2 text-sm font-medium text-white backdrop-blur-sm hover:bg-white/30"
								>
									{link.label}
								</Link>
							))}
						</div>
					)}
				</div>

				{/* Right — illustration */}
				<div className="hidden sm:flex sm:w-1/2 items-center justify-center pr-8 lg:pr-16">
					<Image
						src="/assets/images/hero/hero-welcome.png"
						alt="Skandi Apartments building"
						width={600}
						height={500}
						className="w-full max-w-lg drop-shadow-2xl"
						priority
						unoptimized
					/>
				</div>
			</main>
		</div>
	);
}
