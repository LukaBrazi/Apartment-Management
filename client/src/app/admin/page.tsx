"use client";

import { useMemo } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { DataTable } from "@/components/admin/DataTable";
import StatusBadge from "@/components/admin/StatusBadge";
import {
	useGetAdminAllProfilesQuery,
	useGetAdminIssuesQuery,
	useGetAdminPassesQuery,
	useGetAdminAnnouncementsQuery,
} from "@/lib/redux/features/admin/adminApiSlice";
import { ColumnDef } from "@tanstack/react-table";
import { Issue } from "@/types";
import { Users, ClipboardList, Car, Newspaper } from "lucide-react";
import { format } from "date-fns";
import Link from "next/link";

const recentIssueColumns: ColumnDef<Issue, unknown>[] = [
	{
		accessorKey: "title",
		header: "Назва",
		cell: ({ row }) => (
			<span className="font-medium text-[#1C2B3A] dark:text-white">
				{row.original.title}
			</span>
		),
	},
	{
		accessorKey: "reported_by",
		header: "Подав",
	},
	{
		accessorKey: "status",
		header: "Статус",
		cell: ({ row }) => <StatusBadge value={row.original.status} />,
	},
	{
		accessorKey: "priority",
		header: "Пріоритет",
		cell: ({ row }) => (
			<StatusBadge value={row.original.priority} type="priority" />
		),
	},
];

export default function AdminDashboardPage() {
	const { data: profilesData, isLoading: profilesLoading } =
		useGetAdminAllProfilesQuery();
	const { data: issuesData, isLoading: issuesLoading } =
		useGetAdminIssuesQuery();
	const { data: passesData, isLoading: passesLoading } =
		useGetAdminPassesQuery();
	const { data: announcementsData, isLoading: announcementsLoading } =
		useGetAdminAnnouncementsQuery();

	const totalResidents = profilesData?.profiles?.count ?? 0;

	const activeIssues = useMemo(() => {
		const issues = issuesData?.issues?.results ?? [];
		return issues.filter(
			(i) => i.status !== "done" && i.status !== "rejected",
		).length;
	}, [issuesData]);

	const pendingPasses = useMemo(() => {
		const passes = passesData?.results ?? [];
		return passes.filter((p) => p.status === "pending").length;
	}, [passesData]);

	const totalAnnouncements = announcementsData?.results?.length ?? 0;

	const recentIssues = useMemo(() => {
		return (issuesData?.issues?.results ?? []).slice(0, 5);
	}, [issuesData]);

	const statsCards = [
		{
			label: "Мешканців",
			value: profilesLoading ? "..." : totalResidents,
			icon: Users,
			color: "text-[#3D7A8A]",
			bg: "bg-[#EBF3F5] dark:bg-[#1A2E3A]",
			href: "/admin/residents",
		},
		{
			label: "Активних заявок",
			value: issuesLoading ? "..." : activeIssues,
			icon: ClipboardList,
			color: "text-amber-600 dark:text-amber-400",
			bg: "bg-amber-50 dark:bg-amber-900/20",
			href: "/admin/issues",
		},
		{
			label: "Перепусток (очікують)",
			value: passesLoading ? "..." : pendingPasses,
			icon: Car,
			color: "text-indigo-600 dark:text-indigo-400",
			bg: "bg-indigo-50 dark:bg-indigo-900/20",
			href: "/admin/passes",
		},
		{
			label: "Новин",
			value: announcementsLoading ? "..." : totalAnnouncements,
			icon: Newspaper,
			color: "text-green-600 dark:text-green-400",
			bg: "bg-green-50 dark:bg-green-900/20",
			href: "/admin/posts",
		},
	];

	return (
		<div className="space-y-6">
			<div>
				<h2 className="text-2xl font-bold text-[#1C2B3A] dark:text-white">
					Дашборд
				</h2>
				<p className="text-[#6B7F8C] text-sm mt-1">
					Загальна статистика системи
				</p>
			</div>

			{/* Stats Cards */}
			<div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
				{statsCards.map(({ label, value, icon: Icon, color, bg, href }) => (
					<Link key={label} href={href}>
						<Card className="border-[#E2E5E8] dark:border-[#2D3D4F] bg-white dark:bg-[#162032] shadow-sm cursor-pointer hover:shadow-md hover:border-[#3D7A8A] dark:hover:border-[#3D7A8A] transition-all">
							<CardContent className="p-5 flex items-center gap-4">
								<div className={`p-3 rounded-xl ${bg}`}>
									<Icon className={`h-5 w-5 ${color}`} />
								</div>
								<div>
									<p className="text-2xl font-bold text-[#1C2B3A] dark:text-white">
										{value}
									</p>
									<p className="text-xs text-[#6B7F8C] mt-0.5">{label}</p>
								</div>
							</CardContent>
						</Card>
					</Link>
				))}
			</div>

			{/* Recent Issues */}
			<Card className="border-[#E2E5E8] dark:border-[#2D3D4F] bg-white dark:bg-[#162032] shadow-sm">
				<CardHeader className="pb-4">
					<CardTitle className="text-base font-semibold text-[#1C2B3A] dark:text-white">
						Останні заявки
					</CardTitle>
				</CardHeader>
				<CardContent>
					<DataTable
						columns={recentIssueColumns}
						data={recentIssues}
						isLoading={issuesLoading}
						searchPlaceholder="Пошук заявок..."
					/>
				</CardContent>
			</Card>
		</div>
	);
}
