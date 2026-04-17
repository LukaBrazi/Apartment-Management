"use client";
import { AuthFormHeader, LoginForm } from "@/components/forms/auth";
import { useRedirectIfAuthenticated } from "@/hooks";

export default function LoginPage() {
	useRedirectIfAuthenticated();
	return (
		<div>
			<AuthFormHeader
				title="Вхід до акаунту"
				staticText=""
				linkText=""
				linkHref="/login"
			/>
			<div className="mt-7 sm:mx-auto sm:w-full sm:max-w-[480px]">
				<div className="bg-lightGrey dark:bg-deepBlueGrey rounded-xl px-6 py-12 shadow sm:rounded-lg sm:px-12 md:rounded-3xl">
					<LoginForm />
				</div>
			</div>
		</div>
	);
}
