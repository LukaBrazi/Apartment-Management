"use client";

import Spinner from "@/components/shared/Spinner";
import VehiclePassCard from "@/components/cards/VehiclePassCard";
import { useGetAllPassesQuery } from "@/lib/redux/features/passes/passApiSlice";
import { useGetAllIssuesQuery } from "@/lib/redux/features/issues/issueApiSlice";
import { useGetTenantAnnouncementsQuery } from "@/lib/redux/features/posts/postApiSlice";
import { ShieldIcon, AlertTriangle, ClipboardList, Megaphone } from "lucide-react";
import { useState } from "react";

export default function GuardPortalView() {
	const today = new Date().toISOString().split("T")[0];
	const [selectedDate, setSelectedDate] = useState<string>(today);
	const [statusFilter, setStatusFilter] = useState<string>("");

	const { data, isLoading, isFetching, isError } = useGetAllPassesQuery(
		{
			visit_date: selectedDate || undefined,
			status: statusFilter || undefined,
		},
		{ skip: !selectedDate },
	);

	const {
		data: issuesData,
		isLoading: issuesLoading,
	} = useGetAllIssuesQuery();

	const {
		data: announcementsData,
		isLoading: announcementsLoading,
	} = useGetTenantAnnouncementsQuery();

	const passes = data?.results ?? [];
	const issues = (issuesData as any)?.issues ?? (issuesData as any)?.results ?? [];
	const announcements = (announcementsData as any)?.results ?? (announcementsData as any) ?? [];

	return (
		<div className="max-w-4xl mx-auto">
			<div className="flex items-center gap-3 mb-6">
				<ShieldIcon className="size-8 text-pumpkin" />
				<h1 className="h2-bold dark:text-babyPowder">Портал охорони</h1>
			</div>

			{/* Announcements Panel */}
			<div className="bg-lightGrey dark:bg-deepBlueGrey rounded-xl p-4 mb-6">
				<div className="flex items-center gap-2 mb-3">
					<Megaphone className="size-5 text-blue-500" />
					<h2 className="text-lg font-semibold dark:text-babyPowder">Оголошення ЖК</h2>
				</div>
				{announcementsLoading ? (
					<div className="flex justify-center py-4">
						<Spinner size="sm" />
					</div>
				) : announcements.length === 0 ? (
					<p className="text-sm text-gray-500 dark:text-gray-400">Оголошень немає.</p>
				) : (
					<div className="space-y-2">
						{announcements.slice(0, 5).map((ann: any) => (
							<div
								key={ann.id}
								className="bg-white dark:bg-gray-800 rounded-lg p-3 border border-gray-200 dark:border-gray-700"
							>
								<div className="flex items-start justify-between">
									<div>
										<h3 className="font-medium dark:text-babyPowder text-sm">{ann.title}</h3>
										{ann.building_name && (
											<span className="text-xs text-gray-500 dark:text-gray-400">
												{ann.building_name}
											</span>
										)}
									</div>
									<span className="text-xs text-gray-400 whitespace-nowrap ml-2">
										{new Date(ann.created_at).toLocaleDateString("uk-UA")}
									</span>
								</div>
								{ann.body && (
									<p className="text-sm text-gray-600 dark:text-gray-300 mt-1 line-clamp-2">
										{ann.body}
									</p>
								)}
							</div>
						))}
					</div>
				)}
			</div>

			{/* Recent Issues Panel */}
			<div className="bg-lightGrey dark:bg-deepBlueGrey rounded-xl p-4 mb-6">
				<div className="flex items-center gap-2 mb-3">
					<ClipboardList className="size-5 text-amber-500" />
					<h2 className="text-lg font-semibold dark:text-babyPowder">Останні заявки</h2>
				</div>
				{issuesLoading ? (
					<div className="flex justify-center py-4">
						<Spinner size="sm" />
					</div>
				) : issues.length === 0 ? (
					<p className="text-sm text-gray-500 dark:text-gray-400">Заявок немає.</p>
				) : (
					<div className="space-y-2">
						{issues.slice(0, 5).map((issue: any) => (
							<div
								key={issue.id}
								className="bg-white dark:bg-gray-800 rounded-lg p-3 border border-gray-200 dark:border-gray-700"
							>
								<div className="flex items-start justify-between">
									<div>
										<h3 className="font-medium dark:text-babyPowder text-sm">{issue.title}</h3>
										<span className="text-xs text-gray-500 dark:text-gray-400">
											{issue.reported_by_username} • {issue.status}
										</span>
									</div>
									<span className="text-xs text-gray-400 whitespace-nowrap ml-2">
										{new Date(issue.created_at).toLocaleDateString("uk-UA")}
									</span>
								</div>
							</div>
						))}
					</div>
				)}
			</div>

			{/* Passes Section */}
			<h2 className="text-lg font-semibold dark:text-babyPowder mb-3">Перепустки</h2>

			{/* Filters */}
			<div className="bg-lightGrey dark:bg-deepBlueGrey rounded-xl p-4 mb-6 flex flex-wrap gap-4">
				<div className="flex flex-col gap-1">
					<label className="text-sm font-medium dark:text-babyPowder">
						Дата відвідування
					</label>
					<input
						type="date"
						value={selectedDate}
						onChange={(e) => setSelectedDate(e.target.value)}
						className="rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 dark:text-babyPowder px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-pumpkin"
					/>
				</div>

				<div className="flex flex-col gap-1">
					<label className="text-sm font-medium dark:text-babyPowder">
						Статус
					</label>
					<select
						value={statusFilter}
						onChange={(e) => setStatusFilter(e.target.value)}
						className="rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 dark:text-babyPowder px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-pumpkin"
					>
						<option value="">Усі</option>
						<option value="pending">Очікує</option>
						<option value="closed">Закрита</option>
					</select>
				</div>
			</div>

			{/* Summary */}
			{selectedDate && (
				<p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
					Перепустки на{" "}
					<span className="font-semibold dark:text-babyPowder">
						{new Date(selectedDate + "T00:00:00").toLocaleDateString("uk-UA", {
							weekday: "long",
							year: "numeric",
							month: "long",
							day: "numeric",
						})}
					</span>{" "}
					— {data?.count ?? 0} результат(ів)
				</p>
			)}

			{/* Content */}
			{isLoading || isFetching ? (
				<div className="flex justify-center py-12">
					<Spinner size="md" />
				</div>
			) : isError ? (
				<div className="flex flex-col items-center justify-center py-12 px-4">
					<div className="rounded-full bg-red-100 dark:bg-red-900 p-3 mb-4">
						<AlertTriangle className="h-8 w-8 text-red-600 dark:text-red-300" />
					</div>
					<h3 className="text-center text-lg font-semibold text-red-600 dark:text-red-400 mb-2">
						Помилка при завантаженні
					</h3>
					<p className="text-center text-sm text-gray-600 dark:text-gray-400 max-w-sm">
						Не вдалося завантажити перепустки. Переконайтеся, що у вас є доступ охоронця або адміна.
					</p>
				</div>
			) : passes.length === 0 ? (
				<div className="text-center py-12 text-gray-500 dark:text-gray-400">
					<ShieldIcon className="size-12 mx-auto mb-3 opacity-30" />
					<p>Заявок на цю дату немає.</p>
				</div>
			) : (
				<div className="flex flex-col gap-4">
					{passes.map((pass) => (
						<VehiclePassCard key={pass.id} pass={pass} />
					))}
				</div>
			)}
		</div>
	);
}
