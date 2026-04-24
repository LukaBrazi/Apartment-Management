"use client";

import Image from "next/image";
import Link from "next/link";
import { Car, Plus, Trash2 } from "lucide-react";
import { useGetMyPassesQuery, useDeletePassMutation } from "@/lib/redux/features/passes/passApiSlice";

export default function PassesMiniPanel() {
	const { data, isLoading } = useGetMyPassesQuery();
	const [deletePass, { isLoading: isDeleting }] = useDeletePassMutation();

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
					<div className="flex flex-col items-center justify-center gap-2 py-6 text-[#6B7280]">
						<Image
							src="/assets/images/empty-states/empty-passes.svg"
							alt=""
							width={100}
							height={100}
							className="opacity-60"
						/>
						<p className="text-sm">Немає активних перепусток</p>
					</div>
				) : (
					activePasses.map((pass) => (
						// Mobile-first row: two-tier layout that wraps gracefully
						// on 375px. Car number + status chip stay on the first
						// line; comment/date + delete button on the second.
						// On md+ everything collapses back to a single row.
						<div
							key={pass.id}
							className="flex flex-col gap-1.5 px-5 py-3 transition-colors hover:bg-[#F7F8FA] md:flex-row md:items-center md:gap-3 dark:hover:bg-[#1E2D3D]"
						>
							<div className="flex items-center gap-3 md:flex-1 md:min-w-0">
								<span className="font-mono text-sm font-semibold text-[#111827] dark:text-[#F0EDE6]">
									{pass.car_number}
								</span>
								<span className="min-w-0 flex-1 truncate text-xs text-[#6B7280] dark:text-[#8FA8B8]">
									{pass.comment || pass.visit_date}
								</span>
							</div>
							<div className="flex items-center justify-between gap-2 md:justify-start">
								<span className="flex-shrink-0 rounded-full bg-[#EDFAF6] px-2 py-0.5 text-xs font-medium text-[#2E7D6B]">
									Активна
								</span>
								<button
									onClick={() => {
										if (window.confirm("Видалити цю перепустку?")) {
											deletePass(pass.id);
										}
									}}
									disabled={isDeleting}
									aria-label={`Видалити перепустку ${pass.car_number}`}
									className="tap flex flex-shrink-0 items-center justify-center rounded-lg p-1.5 text-[#9CA3AF] transition-colors hover:bg-red-50 hover:text-red-500 disabled:opacity-50"
								>
									<Trash2 className="h-4 w-4" />
								</button>
							</div>
						</div>
					))
				)}
			</div>

			{/* Footer */}
			<div className="border-t border-[#E5E7EB] px-5 py-3 dark:border-[#2D3D4F]">
				<Link
					href="/my-passes"
					className="text-sm font-medium text-[#D6A14A] transition-opacity hover:opacity-75"
				>
					Всі перепустки →
				</Link>
			</div>
		</div>
	);
}
