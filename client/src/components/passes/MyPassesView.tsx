"use client";

import { useState } from "react";
import Link from "next/link";
import { Car, ChevronLeft, ChevronRight, Plus } from "lucide-react";
import Spinner from "@/components/shared/Spinner";
import VehiclePassCard from "@/components/cards/VehiclePassCard";
import { useGetMyPassesQuery } from "@/lib/redux/features/passes/passApiSlice";

const PAGE_SIZE = 10;

export default function MyPassesView() {
	const [page, setPage] = useState(1);

	const { data, isLoading, isFetching } = useGetMyPassesQuery({ page });

	const passes = data?.results ?? [];
	const totalCount = data?.count ?? 0;
	const totalPages = Math.ceil(totalCount / PAGE_SIZE);
	const hasPrev = page > 1;
	const hasNext = page < totalPages;

	return (
		<div className="max-w-3xl mx-auto">
			{/* Header */}
			<div className="flex items-center justify-between mb-6">
				<div className="flex items-center gap-3">
					<Car className="size-7 text-pumpkin" />
					<h1 className="h2-bold dark:text-babyPowder">Мої перепустки</h1>
				</div>
				<Link
					href="/request-pass"
					className="flex items-center gap-1.5 rounded-lg bg-pumpkin px-4 py-2 text-sm font-medium text-white hover:opacity-90 transition-opacity"
				>
					<Plus className="size-4" />
					Нова перепустка
				</Link>
			</div>

			{/* Content */}
			{isLoading ? (
				<div className="flex justify-center py-16">
					<Spinner size="md" />
				</div>
			) : passes.length === 0 && !isFetching ? (
				<div className="flex flex-col items-center justify-center py-16 text-gray-500 dark:text-gray-400">
					<Car className="size-14 mb-4 opacity-25" />
					<p className="text-base font-medium mb-1">Перепусток ще немає</p>
					<p className="text-sm mb-6">Створіть першу заявку на в&apos;їзд авто</p>
					<Link
						href="/request-pass"
						className="flex items-center gap-1.5 rounded-lg bg-pumpkin px-4 py-2 text-sm font-medium text-white hover:opacity-90 transition-opacity"
					>
						<Plus className="size-4" />
						Подати заявку
					</Link>
				</div>
			) : (
				<>
					{/* Summary */}
					<p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
						Всього:{" "}
						<span className="font-semibold dark:text-babyPowder">{totalCount}</span>{" "}
						перепуст{totalCount === 1 ? "ка" : totalCount < 5 ? "ки" : "ок"}
					</p>

					{/* Pass list */}
					<div className="flex flex-col gap-4 relative">
						{isFetching && (
							<div className="absolute inset-0 flex items-center justify-center bg-white/60 dark:bg-gray-900/60 rounded-xl z-10">
								<Spinner size="sm" />
							</div>
						)}
						{passes.map((pass) => (
							<VehiclePassCard key={pass.id} pass={pass} />
						))}
					</div>

					{/* Pagination */}
					{totalPages > 1 && (
						<div className="flex items-center justify-center gap-4 mt-8">
							<button
								onClick={() => setPage((p) => p - 1)}
								disabled={!hasPrev || isFetching}
								className="flex items-center gap-1 rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
							>
								<ChevronLeft className="size-4" />
								Попередня
							</button>

							<span className="text-sm text-gray-600 dark:text-gray-400">
								Сторінка{" "}
								<span className="font-semibold dark:text-babyPowder">{page}</span>{" "}
								з{" "}
								<span className="font-semibold dark:text-babyPowder">{totalPages}</span>
							</span>

							<button
								onClick={() => setPage((p) => p + 1)}
								disabled={!hasNext || isFetching}
								className="flex items-center gap-1 rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
							>
								Наступна
								<ChevronRight className="size-4" />
							</button>
						</div>
					)}
				</>
			)}
		</div>
	);
}
