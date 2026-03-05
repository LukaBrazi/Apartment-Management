"use client";

import { useActivateUserMutation } from "@/lib/redux/features/auth/authApiSlice";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { toast } from "react-toastify";

interface ActivationProps {
	params: {
		uid: string;
		token: string;
	};
}

export default function ActivationPage({ params }: ActivationProps) {
	const router = useRouter();
	const [activateUser, { isLoading, isSuccess, isError, error }] =
		useActivateUserMutation();

	useEffect(() => {
		const { uid, token } = params;
		activateUser({ uid, token });
	}, [activateUser, params]);

	useEffect(() => {
		if (isSuccess) {
			toast.success("Акаунт успішно активовано!");
			router.push("/login");
		} else if (isError && error) {
			toast.error("Не вдалося активувати акаунт");
		}
	}, [isSuccess, isError, error, router]);

	return (
		<div className="flex min-h-screen items-center justify-center">
			<div className="text-center">
				<h3 className="dark:text-platinum font-robotoSlab text-2xl font-bold text-gray-800 sm:text-4xl md:text-5xl">
					{isLoading ? (
						<div className="flex-center">
							<span className="mr-2">⏰</span>
							<span>Активуємо ваш акаунт... Будь ласка, зачекайте</span>
							<span className="ml-2">🥱</span>
						</div>
					) : isSuccess ? (
						<div>
							<span className="mr-2">✅</span>
							<span>Account Activated successfully!</span>
						</div>
					) : (
						isError && (
							<div>
								<span className="mr-2">❌</span>
								<span>Ваш акаунт вже було активовано або виникла помилка...</span>
							</div>
						)
					)}
				</h3>
			</div>
		</div>
	);
}
