import { ArrowRightIcon } from "@heroicons/react/24/solid";
import type { Metadata } from "next";
import Image from "next/image";
import Link from "next/link";

export const dynamic = "force-dynamic";

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
	hero_title: "Ласкаво просимо до Skandi Apartments",
	hero_subtitle: "Ви новий мешканець? Або вже зареєстровані?",
	hero_image_url: null,
	cta_text: "Створити акаунт",
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
		const data = (json.site_settings as SiteSettings) ?? DEFAULTS;
		return { ...DEFAULTS, ...data, links: data.links ?? [] };
	} catch {
		return DEFAULTS;
	}
}

export default async function HomePage() {
	const settings = await getSiteSettings();

	return (
		<div className="relative h-screen">
			{/* Full-screen background image */}
			<div className="absolute inset-0 z-0">
				{settings.hero_image_url ? (
					<img
						src={settings.hero_image_url}
						alt="Hero"
						className="h-full w-full object-cover object-center"
					/>
				) : (
					<Image
						src="/assets/images/hero/hero-welcome.png"
						alt="Skandi Apartments"
						fill
						style={{ objectFit: "cover", objectPosition: "center" }}
						priority
					/>
				)}
			</div>

			{/* Dark overlay */}
			<div className="absolute inset-0 z-10 bg-black/50" />

			{/* Content */}
			<main className="flex-center relative z-20 h-full">
				<div className="text-center">
					<h1 className="font-robotoSlab mb-4 text-4xl font-semibold text-cyan-400 antialiased sm:text-6xl md:text-8xl">
						{settings.hero_title}
					</h1>
					<p className="my-8 text-2xl text-teal-300 sm:text-4xl">
						{settings.hero_subtitle}
					</p>
					<Link href={settings.cta_url} prefetch={false}>
						<button className="bg-asparagus rounded-3xl px-4 py-2 text-lg font-semibold text-white hover:bg-lime-700 sm:px-6 sm:text-2xl">
							<span className="inline-flex items-center">
								{settings.cta_text}
								<ArrowRightIcon className="ml-2 size-6" />
							</span>
						</button>
					</Link>

					{/* Quick links from admin */}
					{settings.links.length > 0 && (
						<div className="mt-8 flex flex-wrap justify-center gap-4">
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
			</main>
		</div>
	);
}
