import shockedFace from "@/../public/assets/icons/shocked face.svg";
import Image from "next/image";
import { cookies } from "next/headers";
import Link from "next/link";

export default function NotFound() {
	// Source of truth mirrors ``src/middleware.ts`` — the non-HttpOnly
	// ``logged_in`` cookie. Reading it here avoids a double redirect
	// (404 → /login → /welcome) for authenticated users who follow the CTA.
	const isLoggedIn = cookies().get("logged_in")?.value === "true";
	const ctaHref = isLoggedIn ? "/welcome" : "/login";
	const ctaLabel = isLoggedIn ? "На головну" : "До входу";
	return (
		<>
			<main className="flex h-screen flex-col items-center justify-center bg-black px-6 py-16 sm:py-24 lg:scroll-px-28">
				<Image
					src={shockedFace}
					alt="shocked face 404"
					height={200}
					width={200}
					priority
				/>
				<div className="mx-auto max-w-md text-center">
					<h1 className="text-platinum text-4xl font-bold tracking-tight sm:text-5xl">
						Сторінку не знайдено
					</h1>
					<p className="mt-6 text-xl leading-7 text-white sm:text-2xl">
						На жаль, сторінку, яку ви шукаєте, не знайдено.
					</p>
					<div className="mt-10 flex justify-center gap-x-6">
						<Link
							href={ctaHref}
							className="bg-electricIndigo rounded-3xl px-3 py-2 text-lg font-semibold text-white shadow-sm hover:bg-lime-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600 sm:px-3.5 sm:py-2.5 sm:text-2xl"
						>
							{ctaLabel}
						</Link>
					</div>
				</div>
			</main>
		</>
	);
}
