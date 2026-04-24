"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { ColumnDef } from "@tanstack/react-table";
import { DataTable } from "./DataTable";
import StatusBadge from "./StatusBadge";
import { Issue } from "@/types";
import {
	useGetAdminIssuesQuery,
	useAdminUpdateIssueMutation,
	useGetAdminWorkersQuery,
} from "@/lib/redux/features/admin/adminApiSlice";
import { toast } from "react-toastify";
import { ChevronDown, ExternalLink } from "lucide-react";
import {
	Select,
	SelectContent,
	SelectItem,
	SelectTrigger,
	SelectValue,
} from "@/components/ui/select";
import { occupationOptions } from "@/constants";

const OCCUPATION_LABELS: Record<string, string> = Object.fromEntries(
	occupationOptions.map((o) => [o.value, o.label]),
);

const STATUS_OPTIONS = [
	{ value: "reported", label: "Подано" },
	{ value: "accepted", label: "Прийнято" },
	{ value: "in_progress", label: "В роботі" },
	{ value: "done", label: "Виконано" },
	{ value: "rejected", label: "Відхилено" },
];

const PRIORITY_OPTIONS = [
	{ value: "low", label: "Низький" },
	{ value: "medium", label: "Середній" },
	{ value: "high", label: "Високий" },
];

/** Compact native select — used for status & priority (few options, always visible) */
function InlineSelect({
	value,
	options,
	onChange,
}: {
	value: string;
	options: { value: string; label: string }[];
	onChange: (val: string) => void;
}) {
	return (
		<div
			className="relative inline-flex items-center"
			onClick={(e) => e.stopPropagation()}
		>
			<select
				value={value}
				onChange={(e) => onChange(e.target.value)}
				className="appearance-none rounded-lg border border-[#E2E5E8] bg-white py-1 pl-2 pr-6 text-xs font-medium text-[#1C2B3A] transition hover:border-[#3D7A8A] focus:outline-none focus:ring-1 focus:ring-[#3D7A8A] dark:border-[#2D3D4F] dark:bg-[#1E2D3D] dark:text-white"
			>
				{options.map((o) => (
					<option key={o.value} value={o.value}>
						{o.label}
					</option>
				))}
			</select>
			<ChevronDown className="pointer-events-none absolute right-1 top-1/2 h-3 w-3 -translate-y-1/2 text-[#6B7F8C]" />
		</div>
	);
}

export default function AdminIssues() {
	const router = useRouter();
	const { data: issuesData, isLoading } = useGetAdminIssuesQuery();
	const { data: workersData } = useGetAdminWorkersQuery();
	const [updateIssue] = useAdminUpdateIssueMutation();

	const issues = issuesData?.issues?.results ?? [];
	const workers = workersData?.non_tenant_profiles?.results ?? [];

	const workerOptions = [
		{ value: "__none__", label: "Не призначено" },
		...workers.map((w) => ({
			value: w.username,
			label: `${w.full_name || w.username} (${OCCUPATION_LABELS[w.occupation] ?? w.occupation})`,
		})),
	];

	const handleUpdate = async (
		issueId: string,
		field: "status" | "priority" | "assigned_to_username",
		value: string | null,
	) => {
		try {
			await updateIssue({ issueId, [field]: value }).unwrap();
			toast.success("Заявку оновлено");
		} catch {
			toast.error("Помилка оновлення заявки");
		}
	};

	const columns: ColumnDef<Issue>[] = [
		{
			accessorKey: "title",
			header: "Заявка",
			cell: ({ row }) => (
				<div className="max-w-[220px]">
					<p className="truncate font-medium text-[#1C2B3A] dark:text-white">
						{row.original.title}
					</p>
					<p className="text-xs text-[#6B7F8C]">
						{row.original.unit_number ?? "—"}
					</p>
				</div>
			),
		},
		{
			accessorKey: "reported_by",
			header: "Від",
			cell: ({ getValue }) => (
				<span className="text-sm text-[#6B7F8C]">
					{getValue<string>() || "—"}
				</span>
			),
		},
		{
			accessorKey: "status",
			header: "Статус",
			cell: ({ row }) => (
				<InlineSelect
					value={row.original.status}
					options={STATUS_OPTIONS}
					onChange={(val) => handleUpdate(row.original.id, "status", val)}
				/>
			),
		},
		{
			accessorKey: "priority",
			header: "Пріоритет",
			cell: ({ row }) => (
				<InlineSelect
					value={row.original.priority}
					options={PRIORITY_OPTIONS}
					onChange={(val) => handleUpdate(row.original.id, "priority", val)}
				/>
			),
		},
		{
			accessorKey: "assigned_to",
			header: "Виконавець",
			cell: ({ row }) => (
				<div onClick={(e) => e.stopPropagation()}>
					<Select
						value={row.original.assigned_to ?? "__none__"}
						onValueChange={(val) =>
							handleUpdate(
								row.original.id,
								"assigned_to_username",
								val === "__none__" ? null : val,
							)
						}
					>
						<SelectTrigger className="h-7 w-40 rounded-lg border-[#E2E5E8] bg-white px-2 text-xs text-[#1C2B3A] hover:border-[#3D7A8A] focus:ring-[#3D7A8A] dark:border-[#2D3D4F] dark:bg-[#1E2D3D] dark:text-white">
							<SelectValue placeholder="Не призначено" />
						</SelectTrigger>
						<SelectContent>
							{workerOptions.map((o) => (
								<SelectItem key={o.value} value={o.value} className="text-xs">
									{o.label}
								</SelectItem>
							))}
						</SelectContent>
					</Select>
				</div>
			),
		},
		{
			id: "open",
			header: "",
			cell: ({ row }) => (
				<button
					onClick={(e) => {
						e.stopPropagation();
						router.push(`/issue/${row.original.id}`);
					}}
					title="Відкрити заявку"
					className="rounded p-1 text-[#6B7F8C] hover:bg-[#EBF3F5] hover:text-[#3D7A8A] dark:hover:bg-[#1A2E3A] dark:hover:text-[#5BA3B5]"
				>
					<ExternalLink className="h-4 w-4" />
				</button>
			),
		},
	];

	return (
		<div className="rounded-2xl border border-[#E2E5E8] bg-white p-6 dark:border-[#2D3D4F] dark:bg-[#162032]">
			<div className="mb-6">
				<h2 className="text-lg font-semibold text-[#1C2B3A] dark:text-white">
					Заявки
					<span className="ml-2 rounded-full bg-[#EBF3F5] px-2.5 py-0.5 text-xs font-medium text-[#3D7A8A] dark:bg-[#1A2E3A] dark:text-[#5BA3B5]">
						{issues.length}
					</span>
				</h2>
				<p className="mt-1 text-sm text-[#6B7F8C]">
					Клік по рядку — відкриває заявку. Статус, пріоритет та виконавець
					змінюються прямо в таблиці.
				</p>
			</div>
			<DataTable
				columns={columns}
				data={issues}
				isLoading={isLoading}
				searchPlaceholder="Пошук заявок..."
				onRowClick={(issue) => router.push(`/issue/${issue.id}`)}
			/>
		</div>
	);
}
