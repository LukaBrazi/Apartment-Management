"use client";

import Image from "next/image";
import Link from "next/link";
import {
	CreditCard,
	ClipboardList,
	Megaphone,
	Phone,
	Plus,
	ChevronRight,
	FileText,
	Car,
} from "lucide-react";
import { useGetMyIssuesQuery } from "@/lib/redux/features/issues/issueApiSlice";
import { useGetUserProfileQuery } from "@/lib/redux/features/users/usersApiSlice";
import { useGetTenantAnnouncementsQuery } from "@/lib/redux/features/posts/postApiSlice";
import { useGetMyPassesQuery } from "@/lib/redux/features/passes/passApiSlice";
import StatusChip from "./StatusChip";
import KpiCard from "./KpiCard";
import WelcomeHero from "./WelcomeHero";
import QuickActions from "./QuickActions";
import SlaChip from "./SlaChip";
import PassesMiniPanel from "./PassesMiniPanel";

export default function ResidentDashboard() {
	const { data: profileData, isLoading: profileLoading, isError: profileError } = useGetUserProfileQuery();
	const { data: issuesData, isLoading: issuesLoading, isError: issuesError } = useGetMyIssuesQuery();
	const { data: announcementsData, isLoading: announcementsLoading } = useGetTenantAnnouncementsQuery();
	const { data: passesData } = useGetMyPassesQuery();

	const profile = profileData?.profile;
	const issues = issuesData?.my_issues?.results ?? [];
	const issueCount = issuesData?.my_issues?.count ?? 0;
	const announcements = announcementsData?.results ?? [];
	const announcementCount = announcementsData?.count ?? 0;
	const activePassCount = (passesData?.results ?? []).filter((p) => p.status === "pending").length;

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

			{/* Welcome Hero */}
			<WelcomeHero
				firstName={firstName}
				buildingName={buildingName}
				unitNumber={unitNumber}
				isLoading={profileLoading}
			/>

			{/* KPI row */}
			<div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
				<KpiCard
					label="Мої заявки"
					value={issuesLoading ? "—" : issueCount}
					icon={<ClipboardList className="h-5 w-5" />}
					iconBg="bg-[#EEF3FD]"
					iconColor="text-[#2F6FED]"
					href="/profile"
				/>
				<KpiCard
					label="Перепустки"
					value={activePassCount > 0 ? activePassCount : "—"}
					icon={<Car className="h-5 w-5" />}
					iconBg="bg-[#FEF9EE]"
					iconColor="text-[#D6A14A]"
					href="/request-pass"
				/>
				<KpiCard
					label="Оголошення"
					value={announcementsLoading ? "—" : announcementCount}
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

			{/* Quick Actions */}
			<QuickActions />

			{/* Two-column panels */}
			<div className="grid grid-cols-1 gap-6 lg:grid-cols-12">

				{/* Issues panel — 7/12 */}
				<div className="lg:col-span-7 flex flex-col overflow-hidden rounded-2xl border border-[#E5E7EB] bg-white shadow-sm dark:border-[#2D3D4F] dark:bg-[#162032]">
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
						{issuesLoading ? (
							<>
								{[1, 2, 3].map((i) => (
									<div key={i} className="mx-5 my-3 h-10 animate-pulse rounded-lg bg-[#F3F4F6] dark:bg-[#1E2D3D]" />
								))}
							</>
						) : issuesError ? (
							<div className="flex flex-col items-center justify-center gap-3 py-10 text-[#6B7280]">
								<p className="text-sm font-medium text-red-500">Помилка при завантаженні заявок</p>
								<p className="text-xs text-[#6B7280]">Спробуйте оновити сторінку</p>
							</div>
						) : previewIssues.length === 0 ? (
							<div className="flex flex-col items-center justify-center gap-3 py-10 text-[#6B7280]">
								<Image
									src="/assets/images/empty-states/empty-issues.svg"
									alt=""
									width={120}
									height={120}
									className="opacity-70"
								/>
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
									<StatusChip status={issue.status} />
									<SlaChip slaDeadline={(issue as any).sla_deadline} />
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

				{/* Right column — 5/12 */}
				<div className="lg:col-span-5 flex flex-col gap-4">

					{/* Announcements */}
					<div className="flex flex-col overflow-hidden rounded-2xl border border-[#E5E7EB] bg-white shadow-sm dark:border-[#2D3D4F] dark:bg-[#162032]">
						<div className="flex items-center justify-between border-b border-[#E5E7EB] px-5 py-4 dark:border-[#2D3D4F]">
							<h2 className="text-base font-semibold text-[#111827] dark:text-[#F0EDE6]">
								Оголошення
							</h2>
							<Megaphone className="h-4 w-4 text-[#2E7D6B]" />
						</div>

						<div className="flex-1 divide-y divide-[#E5E7EB] dark:divide-[#2D3D4F]">
							{announcementsLoading ? (
								<>
									{[1, 2].map((i) => (
										<div key={i} className="mx-5 my-3 h-10 animate-pulse rounded-lg bg-[#F3F4F6] dark:bg-[#1E2D3D]" />
									))}
								</>
							) : previewAnnouncements.length === 0 ? (
								<div className="flex flex-col items-center justify-center gap-3 py-8 text-[#6B7280]">
									<Image
										src="/assets/images/empty-states/empty-announcements.svg"
										alt=""
										width={100}
										height={100}
										className="opacity-60"
									/>
									<p className="text-sm">Оголошень немає</p>
								</div>
							) : (
								previewAnnouncements.map((ann) => (
									<div
										key={ann.id}
										className="block px-5 py-3.5 hover:bg-[#F7F8FA] dark:hover:bg-[#1E2D3D] transition-colors"
									>
										<p className="text-sm font-medium leading-snug text-[#111827] dark:text-[#F0EDE6] line-clamp-2">
											{ann.title}
										</p>
										{ann.body && (
											<p className="mt-1 text-xs text-[#374151] dark:text-[#A0B3C1] line-clamp-2">
												{ann.body}
											</p>
										)}
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

					{/* Passes mini panel */}
					<PassesMiniPanel />

				</div>
			</div>
		</div>
	);
}
