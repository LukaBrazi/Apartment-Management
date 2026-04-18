"use client";

import { useGetTenantAnnouncementsQuery } from "@/lib/redux/features/posts/postApiSlice";
import Spinner from "@/components/shared/Spinner";
import { formatDate } from "@/utils";
import { Megaphone } from "lucide-react";

export default function AnnouncementsPage() {
	const { data, isLoading, isError } = useGetTenantAnnouncementsQuery();
	const announcements = data?.results ?? [];

	if (isLoading) {
		return (
			<div className="flex flex-col gap-6">
				<div>
					<h1 className="text-2xl font-bold text-[#111827] dark:text-[#F0EDE6]">Оголошення</h1>
					<p className="text-sm text-[#6B7280] mt-1 dark:text-[#8FA8B8]">Новини та повідомлення від управителя</p>
				</div>
				<div className="flex-center pt-16">
					<Spinner size="xl" />
				</div>
			</div>
		);
	}

	if (isError) {
		return (
			<div className="flex flex-col gap-6">
				<div>
					<h1 className="text-2xl font-bold text-[#111827] dark:text-[#F0EDE6]">Оголошення</h1>
					<p className="text-sm text-[#6B7280] mt-1 dark:text-[#8FA8B8]">Новини та повідомлення від управителя</p>
				</div>
				<div className="rounded-2xl border border-red-200 bg-red-50 p-8 text-center shadow-sm dark:border-red-800 dark:bg-red-900/20">
					<p className="text-sm text-red-600 dark:text-red-400">Не вдалося завантажити оголошення. Спробуйте пізніше.</p>
				</div>
			</div>
		);
	}

	return (
		<div className="flex flex-col gap-6">
			<div>
				<h1 className="text-2xl font-bold text-[#111827] dark:text-[#F0EDE6]">Оголошення</h1>
				<p className="text-sm text-[#6B7280] mt-1 dark:text-[#8FA8B8]">
					Новини та повідомлення від управителя
					{announcements.length > 0 && (
						<span className="ml-2 inline-flex items-center rounded-full bg-[#EEF3FD] px-2 py-0.5 text-xs font-medium text-[#2F6FED] dark:bg-[#1A2E3A] dark:text-[#5BA3B5]">
							{announcements.length}
						</span>
					)}
				</p>
			</div>

			{announcements.length === 0 ? (
				<div className="rounded-2xl border border-[#E5E7EB] bg-white p-8 text-center shadow-sm dark:border-[#2D3D4F] dark:bg-[#162032]">
					<div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-[#EEF3FD] dark:bg-[#1A2E3A]">
						<Megaphone className="h-8 w-8 text-[#2F6FED] dark:text-[#5BA3B5]" />
					</div>
					<h2 className="text-lg font-semibold text-[#111827] dark:text-[#F0EDE6]">Оголошень поки немає</h2>
					<p className="mt-2 text-sm text-[#6B7280] dark:text-[#8FA8B8]">Нових оголошень від управителя поки не надходило.</p>
				</div>
			) : (
				<div className="flex flex-col gap-4">
					{announcements.map((announcement) => (
						<div
							key={announcement.id}
							className="rounded-2xl border border-[#E5E7EB] bg-white p-6 shadow-sm transition-shadow hover:shadow-md dark:border-[#2D3D4F] dark:bg-[#162032]"
						>
							<div className="flex items-start gap-4">
								<div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-[#EEF3FD] dark:bg-[#1A2E3A]">
									<Megaphone className="h-5 w-5 text-[#2F6FED] dark:text-[#5BA3B5]" />
								</div>
								<div className="min-w-0 flex-1">
									<div className="flex items-center justify-between gap-3">
										<h3 className="text-base font-semibold text-[#111827] dark:text-[#F0EDE6]">
											{announcement.title}
										</h3>
										<span className="shrink-0 text-xs text-[#6B7280] dark:text-[#8FA8B8]">
											{formatDate(announcement.created_at).toString()}
										</span>
									</div>
									<p className="mt-2 text-sm text-[#374151] leading-relaxed dark:text-[#C5D0D8]">
										{announcement.body}
									</p>
									<div className="mt-3 flex items-center gap-3">
										<span className="inline-flex items-center rounded-full bg-[#F3F4F6] px-2.5 py-0.5 text-xs font-medium text-[#6B7280] dark:bg-[#1A2E3A] dark:text-[#8FA8B8]">
											{announcement.building_name}
										</span>
									</div>
								</div>
							</div>
						</div>
					))}
				</div>
			)}
		</div>
	);
}
