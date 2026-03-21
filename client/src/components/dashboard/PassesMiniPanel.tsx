"use client";

import Link from "next/link";
import { Car, Plus } from "lucide-react";
import { useGetMyPassesQuery } from "@/lib/redux/features/passes/passApiSlice";

export default function PassesMiniPanel() {
	const { data, isLoading } = useGetMyPassesQuery();

	const activePasses = (data?.results ?? [])
		.filter((p) => p.status === "pending")
		.slice(0, 3);

	return (
		<div className="flex flex-col overflow-hidden rounded-2xl border border-[#E5E7EB] bg-white shadow-sm dark:border-[#2D3D4F] dark:bg-[#162032]">
			{/* Header */}
			<div className="flex items-center justify-between border-b border-[#E5E7EB] px-5 py-4 dark:border-[#2D3D4F]">
				<h2 className="flex items-center gap-2 text-base font-semibold text-[#111827] dark:text-[#F0EDE6]">
					<Car className="h-4 w-4 text-[#D6A14A]" />
					Перепустки
				</h2>
				<Link
					href="/request-pass"
					className="flex items-center gap-1 rounded-lg bg-[#FEF9EE] px-2.5 py-1 text-xs font-medium text-[#D6A14A] hover:bg-[#FEF3D0] transition-colors"
				>
					<Plus className="h-3 w-3" />
					Нова
				</Link>
			</div>

			{/* Body */}
			<div className="flex-1 divide-y divide-[#E5E7EB] dark:divide-[#2D3D4F]">
				{isLoading ? (
					<>
						{[1, 2].map((i) => (
							<div key={i} className="flex items-center gap-3 px-5 py-3">
								<div className="h-4 w-24 animate-pulse rounded bg-[#F3F4F6] dark:bg-[#1E2D3D]" />
								<div className="h-4 flex-1 animate-pulse rounded bg-[#F3F4F6] dark:bg-[#1E2D3D]" />
							</div>
						))}
					</>
				) : activePasses.length === 0 ? (
					<div className="flex flex-col items-center justify-center gap-1.5 py-8 text-[#6B7280]">
						<Car className="h-8 w-8 opacity-25" />
						<p className="text-sm">Немає активних перепусток</p>
					</div>
				) : (
					activePasses.map((pass) => (
						<div
							key={pass.id}
							className="flex items-center gap-3 px-5 py-3 hover:bg-[#F7F8FA] dark:hover:bg-[#1E2D3D] transition-colors"
						>
							<span className="font-mono text-sm font-semibold text-[#111827] dark:text-[#F0EDE6]">
								{pass.car_number}
							</span>
							<span className="flex-1 truncate text-xs text-[#6B7280] dark:text-[#8FA8B8]">
								{pass.comment || pass.visit_date}
							</span>
							<span className="flex-shrink-0 rounded-full bg-[#EDFAF6] px-2 py-0.5 text-xs font-medium text-[#2E7D6B]">
								Активна
							</span>
						</div>
					))
				)}
			</div>

			{/* Footer */}
			<div className="border-t border-[#E5E7EB] px-5 py-3 dark:border-[#2D3D4F]">
				<Link
					href="/request-pass"
					className="text-sm font-medium text-[#D6A14A] transition-opacity hover:opacity-75"
				>
					Всі перепустки →
				</Link>
			</div>
		</div>
	);
}
