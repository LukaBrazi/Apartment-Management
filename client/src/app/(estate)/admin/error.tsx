"use client";

import { useEffect } from "react";
import { AlertTriangle } from "lucide-react";

export default function AdminError({
	error,
	reset,
}: {
	error: Error & { digest?: string };
	reset: () => void;
}) {
	useEffect(() => {
		console.error("Admin page error:", error);
	}, [error]);

	return (
		<div className="flex min-h-screen items-center justify-center bg-[#F9FAFB] dark:bg-[#0F1419] px-4">
			<div className="max-w-md w-full">
				<div className="rounded-2xl border border-[#E5E7EB] bg-white shadow-sm dark:border-[#2D3D4F] dark:bg-[#162032] p-8">
					<div className="flex justify-center mb-4">
						<div className="rounded-full bg-red-100 dark:bg-red-900 p-3">
							<AlertTriangle className="h-6 w-6 text-red-600 dark:text-red-300" />
						</div>
					</div>
					<h1 className="text-center text-xl font-semibold text-[#111827] dark:text-[#F0EDE6] mb-2">
						Помилка на сторінці адміна
					</h1>
					<p className="text-center text-sm text-[#6B7280] dark:text-[#8FA8B8] mb-6">
						{error.message || "Виникла невідома помилка при завантаженні панелі адміністратора"}
					</p>
					<button
						onClick={() => reset()}
						className="w-full rounded-lg bg-[#2F6FED] px-4 py-2.5 text-sm font-medium text-white hover:bg-[#2460d4] transition-colors"
					>
						Спробувати ще раз
					</button>
				</div>
			</div>
		</div>
	);
}
