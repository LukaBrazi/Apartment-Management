"use client";
import { AuthFormHeader, LoginForm } from "@/components/forms/auth";
import { useRedirectIfAuthenticated } from "@/hooks";

export default function LoginPage() {
	useRedirectIfAuthenticated();
	return (
		<div className="flex min-h-[calc(100vh-10rem)] w-full items-center justify-center py-8">
			<div className="w-full sm:mx-auto sm:max-w-[460px]">
				<div className="relative overflow-hidden rounded-3xl border border-[#E2E5E8]/80 bg-white/95 px-6 py-10 shadow-xl shadow-[#0F1923]/5 backdrop-blur sm:px-10 sm:py-12 dark:border-[#2D3D4F]/80 dark:bg-[#1E2D3D]/95 dark:shadow-black/30">
					{/* Decorative glows — purely cosmetic, pointer-events-none
					    so they never intercept clicks on the form. */}
					<div
						aria-hidden
						className="pointer-events-none absolute -right-24 -top-24 size-56 rounded-full bg-gradient-to-br from-[#5BA3B5]/25 to-transparent blur-3xl"
					/>
					<div
						aria-hidden
						className="pointer-events-none absolute -bottom-28 -left-24 size-56 rounded-full bg-gradient-to-tr from-[#3D7A8A]/15 to-transparent blur-3xl"
					/>

					<div className="relative">
						<AuthFormHeader
							title="Вхід до акаунту"
							staticText=""
							linkText=""
							linkHref="/login"
						/>
						<div className="mt-8">
							<LoginForm />
						</div>
					</div>
				</div>
			</div>
		</div>
	);
}
