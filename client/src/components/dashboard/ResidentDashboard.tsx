"use client";

import Link from "next/link";
import {
	Building2,
	CreditCard,
	ClipboardList,
	Megaphone,
	Phone,
	Plus,
	ChevronRight,
	FileText,
} from "lucide-react";
import { useGetMyIssuesQuery } from "@/lib/redux/features/issues/issueApiSlice";
import { useGetUserProfileQuery } from "@/lib/redux/features/users/usersApiSlice";
import { useGetTenantAnnouncementsQuery } from "@/lib/redux/features/posts/postApiSlice";
import StatusChip from "./StatusChip";
import KpiCard from "./KpiCard";
import Spinner from "@/components/shared/Spinner";

export default function ResidentDashboard() {
	const { data: profileData, isLoading: profileLoading } = useGetUserProfileQuery();
	const { data: issuesData, isLoading: issuesLoading } = useGetMyIssuesQuery();
	const { data: announcementsData, isLoading: announcementsLoading } = useGetTenantAnnouncementsQuery();

	if (profileLoading || issuesLoading || announcementsLoading) {
		return (
			<div className="flex items-center justify-center py-32">
				<Spinner size="md" />
			</div>
		);
	}

	const profile = profileData?.profile;
	const issues = issuesData?.my_issues?.results ?? [];
	const issueCount = issuesData?.my_issues?.count ?? 0;
	const announcements = announcementsData?.results ?? [];
	const announcementCount = announcementsData?.count ?? 0;

	// building_name comes from issues (more readable), fallback to apartment.building UUID
	const buildingName =
		(issues[0] as any)?.building_name ??
		profile?.apartment?.building ??
		"—";
	const unitNumber = profile?.apartment?.unit_number ?? "—";
	const firstName = profile?.first_name ?? "";

	const previewIssues = issues.slice(0, 5);
	const previewAnnouncements = announcements.slice(0, 4);

	return (
		<div className="space-y-6">

			{/* Building header */}
			<div className="flex flex-wrap items-center gap-3 rounded-2xl border border-[#E5E7EB] bg-white px-6 py-4 shadow-[0_1px_3px_rgba(0,0,0,0.06)] dark:border-[#2D3D4F] dark:bg-[#162032]">
				<div className="flex items-center gap-2 flex-1 min-w-0">
					<Building2 className="h-5 w-5 flex-shrink-0 text-[#2F6FED]" />
					<span className="text-sm text-[#6B7280] dark:text-[#8FA8B8]">
						Будинок:{" "}
						<span className="font-semibold text-[#111827] dark:text-[#F0EDE6]">
							{buildingName}
						</span>
					</span>
				</div>
				{unitNumber !== "—" && (
					<span className="rounded-lg bg-[#EEF3FD] px-3 py-1 text-sm font-semibold text-[#2F6FED]">
						кв. {unitNumber}
					</span>
				)}
				{firstName && (
					<h1 className="w-full text-xl font-bold text-[#111827] dark:text-[#F0EDE6] mt-1">
						Вітаємо, {firstName}!
					</h1>
				)}
			</div>

			{/* KPI row */}
			<div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
				<KpiCard
					label="Мої платіжки"
					value="В розробці"
					icon={<CreditCard className="h-5 w-5" />}
					iconBg="bg-[#FEF9EE]"
					iconColor="text-[#D6A14A]"
				/>
				<KpiCard
					label="Мої заявки"
					value={issueCount}
					icon={<ClipboardList className="h-5 w-5" />}
					iconBg="bg-[#EEF3FD]"
					iconColor="text-[#2F6FED]"
					href="/profile"
				/>
				<KpiCard
					label="Оголошення"
					value={announcementCount}
					icon={<Megaphone className="h-5 w-5" />}
					iconBg="bg-[#EDFAF6]"
					iconColor="text-[#2E7D6B]"
					href="/announcements"
				/>
				<KpiCard
					label="Контакти"
					value="В розробці"
					icon={<Phone className="h-5 w-5" />}
					iconBg="bg-[#F3F4F6]"
					iconColor="text-[#6B7280]"
					href="/contacts"
				/>
			</div>

			{/* Two-column panels */}
			<div className="grid grid-cols-1 gap-6 lg:grid-cols-12">

				{/* Issues panel — 7/12 */}
				<div className="lg:col-span-7 flex flex-col overflow-hidden rounded-2xl border border-[#E5E7EB] bg-white shadow-[0_1px_3px_rgba(0,0,0,0.06)] dark:border-[#2D3D4F] dark:bg-[#162032]">
					<div className="flex items-center justify-between border-b border-[#E5E7EB] px-5 py-4 dark:border-[#2D3D4F]">
						<h2 className="text-base font-semibold text-[#111827] dark:text-[#F0EDE6]">
							Мої заявки
						</h2>
						<Link
							href="/report-issue"
							className="flex items-center gap-1.5 rounded-lg bg-[#2F6FED] px-3 py-1.5 text-xs font-medium text-white transition-colors hover:bg-[#2460d4]"
						>
							<Plus className="h-3.5 w-3.5" />
							Нова заявка
						</Link>
					</div>

					<div className="flex-1 divide-y divide-[#E5E7EB] dark:divide-[#2D3D4F]">
						{previewIssues.length === 0 ? (
							<div className="flex flex-col items-center justify-center gap-2 py-14 text-[#6B7280]">
								<FileText className="h-10 w-10 opacity-30" />
								<p className="text-sm">Заявок немає</p>
								<Link
									href="/report-issue"
									className="mt-2 rounded-lg bg-[#2F6FED] px-4 py-2 text-sm font-medium text-white hover:bg-[#2460d4]"
								>
									Подати першу заявку
								</Link>
							</div>
						) : (
							previewIssues.map((issue) => (
								<Link
									key={issue.id}
									href={`/issue/${issue.id}`}
									className="flex items-center gap-3 px-5 py-3.5 transition-colors hover:bg-[#F7F8FA] dark:hover:bg-[#1E2D3D]"
								>
									<ClipboardList className="h-4 w-4 flex-shrink-0 text-[#9CA3AF]" />
									<span className="flex-1 truncate text-sm font-medium text-[#111827] dark:text-[#F0EDE6]">
										{issue.title}
									</span>
									<StatusChip status={issue.status as any} />
									<ChevronRight className="h-4 w-4 flex-shrink-0 text-[#9CA3AF]" />
								</Link>
							))
						)}
					</div>

					<div className="border-t border-[#E5E7EB] px-5 py-3 dark:border-[#2D3D4F]">
						<Link
							href="/profile"
							className="text-sm font-medium text-[#2F6FED] transition-colors hover:text-[#2460d4]"
						>
							Всі заявки →
						</Link>
					</div>
				</div>

				{/* Announcements panel — 5/12 */}
				<div className="lg:col-span-5 flex flex-col overflow-hidden rounded-2xl border border-[#E5E7EB] bg-white shadow-[0_1px_3px_rgba(0,0,0,0.06)] dark:border-[#2D3D4F] dark:bg-[#162032]">
					<div className="flex items-center justify-between border-b border-[#E5E7EB] px-5 py-4 dark:border-[#2D3D4F]">
						<h2 className="text-base font-semibold text-[#111827] dark:text-[#F0EDE6]">
							Оголошення
						</h2>
						<Megaphone className="h-4 w-4 text-[#2E7D6B]" />
					</div>

					<div className="flex-1 divide-y divide-[#E5E7EB] dark:divide-[#2D3D4F]">
						{previewAnnouncements.length === 0 ? (
							<div className="flex flex-col items-center justify-center gap-2 py-14 text-[#6B7280]">
								<Megaphone className="h-10 w-10 opacity-30" />
								<p className="text-sm">Оголошень немає</p>
								<span className="rounded-full bg-[#F3F4F6] px-3 py-1 text-xs text-[#9CA3AF] dark:bg-[#1E2D3D]">
									В розробці
								</span>
							</div>
						) : (
							previewAnnouncements.map((ann) => (
								<div key={ann.id} className="px-5 py-3.5 hover:bg-[#F7F8FA] dark:hover:bg-[#1E2D3D] transition-colors">
									<p className="text-sm font-medium leading-snug text-[#111827] dark:text-[#F0EDE6]">
										{ann.title}
									</p>
									<p className="mt-0.5 text-xs text-[#6B7280] dark:text-[#8FA8B8]">
										{new Date(ann.created_at).toLocaleDateString("uk-UA", {
											day: "numeric",
											month: "long",
										})}
									</p>
								</div>
							))
						)}
					</div>

					<div className="border-t border-[#E5E7EB] px-5 py-3 dark:border-[#2D3D4F]">
						<Link
							href="/announcements"
							className="text-sm font-medium text-[#2E7D6B] transition-opacity hover:opacity-75"
						>
							Всі оголошення →
						</Link>
					</div>
				</div>

			</div>
		</div>
	);
}
