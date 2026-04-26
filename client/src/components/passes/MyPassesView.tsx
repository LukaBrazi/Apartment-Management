"use client";

import { useState } from "react";
import Link from "next/link";
import { Car, Calendar, Clock, X, ChevronLeft, ChevronRight, Plus } from "lucide-react";
import { format } from "date-fns";
import { uk } from "date-fns/locale";
import Spinner from "@/components/shared/Spinner";
import {
	useGetMyPassesQuery,
	useDeletePassMutation,
} from "@/lib/redux/features/passes/passApiSlice";
import { VehiclePass } from "@/types";
import { toast } from "react-toastify";

const PAGE_SIZE = 10;

type FilterType = "active" | "closed";

function FilterTab({
	active,
	count,
	onClick,
	children,
}: {
	active: boolean;
	count?: number;
	onClick: () => void;
	children: React.ReactNode;
}) {
	return (
		<button
			onClick={onClick}
			className={`flex items-center gap-2 rounded-xl px-4 py-2 text-sm font-medium transition-all duration-150 ${
				active
					? "bg-[#1E2761] text-white shadow-sm"
					: "bg-transparent text-[#475569] hover:bg-white"
			}`}
		>
			{children}
			{count != null && (
				<span
					className={`rounded-full px-2 py-0.5 text-xs font-semibold ${
						active ? "bg-white/20 text-white" : "bg-[#F1F5F9] text-[#64748B]"
					}`}
				>
					{count}
				</span>
			)}
		</button>
	);
}

function ResidentPassCard({ pass }: { pass: VehiclePass }) {
	const isClosed = pass.status === "closed";
	const [deletePass, { isLoading }] = useDeletePassMutation();

	const handleDelete = async () => {
		if (!confirm("Видалити перепустку? Цю дію не можна скасувати.")) return;
		try {
			await deletePass(pass.id).unwrap();
			toast.success("Перепустку видалено.");
		} catch {
			toast.error("Не вдалося видалити перепустку.");
		}
	};

	return (
		<div className="rounded-2xl border border-[#F1F5F9] bg-white p-5 shadow-[0_1px_2px_rgba(0,0,0,0.05)]">
			{/* Header row: car icon + plate + badge */}
			<div className="flex items-center justify-between mb-3">
				<div className="flex items-center gap-3">
					<div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[#FEF3C7] text-[#B45309]">
						<Car className="h-5 w-5" />
					</div>
					<div>
						<div className="font-mono text-lg font-bold tracking-widest text-[#0F172A]">
							{pass.car_number || "—"}
						</div>
						<div className="text-xs text-[#64748B]">Гостьове авто</div>
					</div>
				</div>
				<span
					className={`rounded-full px-3 py-1 text-xs font-semibold ${
						isClosed
							? "bg-[#F1F5F9] text-[#64748B]"
							: "bg-[#FEF9C3] text-[#A16207]"
					}`}
				>
					{isClosed ? "Закрита" : "Активна"}
				</span>
			</div>

			{/* Details */}
			<div className="space-y-2 mb-4">
				<div className="flex items-center gap-2 text-sm text-[#475569]">
					<Calendar className="h-3.5 w-3.5 text-[#94A3B8]" />
					{pass.visit_date
						? format(new Date(pass.visit_date), "d MMMM yyyy", { locale: uk })
						: "—"}
				</div>
				<div className="flex items-center gap-2 text-xs text-[#94A3B8]">
					<Clock className="h-3 w-3" />
					Створено{" "}
					{pass.created_at
						? format(new Date(pass.created_at), "d MMM yyyy 'о' HH:mm", { locale: uk })
						: "—"}
				</div>
			</div>

			{!isClosed && (
				<button
					onClick={handleDelete}
					disabled={isLoading}
					className="flex w-full items-center justify-center gap-2 rounded-xl border border-[#C0392B] bg-[#FEE2E2] py-2 text-sm font-medium text-[#C0392B] transition-colors hover:bg-[#FECACA] disabled:opacity-50"
				>
					<X className="h-3.5 w-3.5" />
					{isLoading ? "Видаляємо…" : "Видалити перепустку"}
				</button>
			)}
		</div>
	);
}

export default function MyPassesView() {
	const [page, setPage] = useState(1);
	const [filter, setFilter] = useState<FilterType>("active");

	const { data, isLoading, isFetching } = useGetMyPassesQuery({ page });

	const passes = data?.results ?? [];
	const totalCount = data?.count ?? 0;
	const totalPages = Math.ceil(totalCount / PAGE_SIZE);
	const hasPrev = page > 1;
	const hasNext = page < totalPages;

	const activePasses = passes.filter((p) => p.status !== "closed");
	const closedPasses = passes.filter((p) => p.status === "closed");
	const displayedPasses = filter === "active" ? activePasses : closedPasses;

	return (
		<div className="max-w-3xl mx-auto">
			{/* Header */}
			<div className="flex items-center justify-between mb-6">
				<div className="flex items-center gap-3">
					<div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[#FEF3C7] text-[#B45309]">
						<Car className="h-5 w-5" />
					</div>
					<h1 className="text-xl font-bold text-[#0F172A]">Мої перепустки</h1>
				</div>
				<Link
					href="/request-pass"
					className="flex items-center gap-1.5 rounded-xl bg-[#1E2761] px-4 py-2 text-sm font-medium text-white hover:bg-[#16204f] transition-colors"
				>
					<Plus className="h-4 w-4" />
					Нова перепустка
				</Link>
			</div>

			{/* Content */}
			{isLoading ? (
				<div className="flex justify-center py-16">
					<Spinner size="md" />
				</div>
			) : passes.length === 0 && !isFetching ? (
				<div className="flex flex-col items-center justify-center py-16 text-[#64748B]">
					<div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-[#FEF3C7] text-[#B45309] mb-4">
						<Car className="h-8 w-8 opacity-60" />
					</div>
					<p className="text-base font-medium mb-1">Перепусток ще немає</p>
					<p className="text-sm mb-6">Створіть першу заявку на в&apos;їзд авто</p>
					<Link
						href="/request-pass"
						className="flex items-center gap-1.5 rounded-xl bg-[#1E2761] px-4 py-2 text-sm font-medium text-white hover:bg-[#16204f] transition-colors"
					>
						<Plus className="h-4 w-4" />
						Подати заявку
					</Link>
				</div>
			) : (
				<>
					{/* Filter tabs */}
					<div className="mb-4 inline-flex items-center gap-1 rounded-xl bg-[#F8FAFC] p-1">
						<FilterTab
							active={filter === "active"}
							count={activePasses.length}
							onClick={() => setFilter("active")}
						>
							Активні
						</FilterTab>
						<FilterTab
							active={filter === "closed"}
							count={closedPasses.length}
							onClick={() => setFilter("closed")}
						>
							Архів
						</FilterTab>
					</div>

					{/* Pass grid */}
					<div className="grid grid-cols-1 sm:grid-cols-2 gap-4 relative">
						{isFetching && (
							<div className="absolute inset-0 flex items-center justify-center bg-white/60 rounded-xl z-10">
								<Spinner size="sm" />
							</div>
						)}
						{displayedPasses.length === 0 ? (
							<div className="col-span-full flex flex-col items-center justify-center py-10 text-[#94A3B8]">
								<p className="text-sm">
									{filter === "active" ? "Активних перепусток немає" : "Архів порожній"}
								</p>
							</div>
						) : (
							displayedPasses.map((pass) => (
								<ResidentPassCard key={pass.id} pass={pass} />
							))
						)}
					</div>

					{/* Pagination */}
					{totalPages > 1 && (
						<div className="flex items-center justify-center gap-4 mt-8">
							<button
								onClick={() => setPage((p) => p - 1)}
								disabled={!hasPrev || isFetching}
								className="flex items-center gap-1 rounded-xl border border-[#E2E8F0] px-3 py-2 text-sm font-medium text-[#475569] hover:bg-[#F8FAFC] disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
							>
								<ChevronLeft className="h-4 w-4" />
								Попередня
							</button>

							<span className="text-sm text-[#64748B]">
								Сторінка{" "}
								<span className="font-semibold text-[#0F172A]">{page}</span>{" "}
								з{" "}
								<span className="font-semibold text-[#0F172A]">{totalPages}</span>
							</span>

							<button
								onClick={() => setPage((p) => p + 1)}
								disabled={!hasNext || isFetching}
								className="flex items-center gap-1 rounded-xl border border-[#E2E8F0] px-3 py-2 text-sm font-medium text-[#475569] hover:bg-[#F8FAFC] disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
							>
								Наступна
								<ChevronRight className="h-4 w-4" />
							</button>
						</div>
					)}
				</>
			)}
		</div>
	);
}
