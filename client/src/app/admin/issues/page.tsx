"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { ColumnDef } from "@tanstack/react-table";
import { toast } from "react-toastify";
import { ExternalLink, Pencil } from "lucide-react";

import { DataTable } from "@/components/admin/DataTable";
import StatusBadge from "@/components/admin/StatusBadge";
import { Button } from "@/components/ui/button";
import {
	Select,
	SelectContent,
	SelectItem,
	SelectTrigger,
	SelectValue,
} from "@/components/ui/select";
import {
	Dialog,
	DialogContent,
	DialogHeader,
	DialogTitle,
	DialogFooter,
} from "@/components/ui/dialog";
import {
	useGetAdminIssuesQuery,
	useAdminUpdateIssueMutation,
	useGetAdminWorkersQuery,
} from "@/lib/redux/features/admin/adminApiSlice";
import { Issue } from "@/types";
import { extractErrorMessage } from "@/utils";
import { occupationOptions } from "@/constants";

const OCCUPATION_LABELS: Record<string, string> = Object.fromEntries(
	occupationOptions.map((o) => [o.value, o.label]),
);

const editSchema = z.object({
	status: z.string().min(1),
	priority: z.string().min(1),
	assigned_to_username: z.string().optional(),
});

type EditFormValues = z.infer<typeof editSchema>;

const NO_ASSIGNEE = "__none__";

export default function AdminIssuesPage() {
	const router = useRouter();
	const { data, isLoading } = useGetAdminIssuesQuery();
	const { data: workersData } = useGetAdminWorkersQuery();
	const [updateIssue, { isLoading: isUpdating }] = useAdminUpdateIssueMutation();

	const [selectedIssue, setSelectedIssue] = useState<Issue | null>(null);
	const [dialogOpen, setDialogOpen] = useState(false);

	const workers = workersData?.non_tenant_profiles?.results ?? [];

	const { handleSubmit, setValue, reset } = useForm<EditFormValues>({
		resolver: zodResolver(editSchema),
	});

	const openEdit = (issue: Issue, e: React.MouseEvent) => {
		e.stopPropagation();
		setSelectedIssue(issue);
		reset({
			status: issue.status,
			priority: issue.priority,
			assigned_to_username: issue.assigned_to ?? NO_ASSIGNEE,
		});
		setDialogOpen(true);
	};

	const onSubmit = async (values: EditFormValues) => {
		if (!selectedIssue) return;
		try {
			await updateIssue({
				issueId: selectedIssue.id,
				status: values.status,
				priority: values.priority,
				assigned_to_username:
					values.assigned_to_username === NO_ASSIGNEE ||
					!values.assigned_to_username
						? null
						: values.assigned_to_username,
			}).unwrap();
			toast.success("Заявку оновлено");
			setDialogOpen(false);
		} catch (e) {
			toast.error(extractErrorMessage(e) || "Помилка оновлення");
		}
	};

	const issues = data?.issues?.results ?? [];

	const columns: ColumnDef<Issue, unknown>[] = [
		{
			accessorKey: "title",
			header: "Назва",
			cell: ({ row }) => (
				<div className="max-w-[240px]">
					<span className="block truncate font-medium text-[#1C2B3A] dark:text-white">
						{row.original.title}
					</span>
					{row.original.unit_number && (
						<span className="text-xs text-[#6B7F8C]">
							кв. {row.original.unit_number}
						</span>
					)}
				</div>
			),
		},
		{
			accessorKey: "reported_by",
			header: "Подав",
			cell: ({ row }) => (
				<span className="text-sm text-[#6B7F8C]">{row.original.reported_by}</span>
			),
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
		{
			accessorKey: "assigned_to",
			header: "Виконавець",
			cell: ({ row }) =>
				row.original.assigned_to ? (
					<span className="text-sm">@{row.original.assigned_to}</span>
				) : (
					<span className="text-sm text-[#6B7F8C]">Не призначено</span>
				),
		},
		{
			id: "actions",
			header: "",
			cell: ({ row }) => (
				<div className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
					<Button
						variant="ghost"
						size="sm"
						onClick={(e) => openEdit(row.original, e)}
						className="h-7 px-2 text-[#3D7A8A] hover:bg-[#EBF3F5] dark:hover:bg-[#1A2E3A]"
						title="Редагувати"
					>
						<Pencil className="h-3.5 w-3.5" />
					</Button>
					<Button
						variant="ghost"
						size="sm"
						onClick={(e) => {
							e.stopPropagation();
							router.push(`/issue/${row.original.id}`);
						}}
						className="h-7 px-2 text-[#6B7F8C] hover:bg-[#EBF3F5] dark:hover:bg-[#1A2E3A]"
						title="Відкрити заявку"
					>
						<ExternalLink className="h-3.5 w-3.5" />
					</Button>
				</div>
			),
		},
	];

	return (
		<div className="space-y-6">
			<div>
				<h2 className="text-2xl font-bold text-[#1C2B3A] dark:text-white">
					Заявки
				</h2>
				<p className="mt-1 text-sm text-[#6B7F8C]">
					Клік по рядку відкриває заявку. Кнопка олівця — редагування.
				</p>
			</div>

			<div className="rounded-xl border border-[#E2E5E8] bg-white p-6 shadow-sm dark:border-[#2D3D4F] dark:bg-[#162032]">
				<DataTable
					columns={columns}
					data={issues}
					isLoading={isLoading}
					searchPlaceholder="Пошук заявок..."
					onRowClick={(issue) => router.push(`/issue/${issue.id}`)}
				/>
			</div>

			{/* Edit Dialog */}
			<Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
				<DialogContent className="max-w-md border-[#E2E5E8] bg-white dark:border-[#2D3D4F] dark:bg-[#162032]">
					<DialogHeader>
						<DialogTitle className="text-[#1C2B3A] dark:text-white">
							Редагувати заявку
						</DialogTitle>
					</DialogHeader>

					{selectedIssue && (
						<p className="-mt-2 truncate text-sm text-[#6B7F8C]">
							{selectedIssue.title}
						</p>
					)}

					<form onSubmit={handleSubmit(onSubmit)} className="mt-2 space-y-4">
						{/* Status */}
						<div className="space-y-1">
							<label className="text-xs font-medium text-[#6B7F8C]">
								Статус
							</label>
							<Select
								defaultValue={selectedIssue?.status}
								onValueChange={(val) => setValue("status", val)}
							>
								<SelectTrigger className="border-[#E2E5E8] bg-[#F7F6F2] dark:border-[#2D3D4F] dark:bg-[#1C2B3A]">
									<SelectValue placeholder="Оберіть статус" />
								</SelectTrigger>
								<SelectContent>
									<SelectItem value="reported">Подано</SelectItem>
									<SelectItem value="accepted">Прийнято</SelectItem>
									<SelectItem value="in_progress">В роботі</SelectItem>
									<SelectItem value="done">Виконано</SelectItem>
									<SelectItem value="rejected">Відхилено</SelectItem>
								</SelectContent>
							</Select>
						</div>

						{/* Priority */}
						<div className="space-y-1">
							<label className="text-xs font-medium text-[#6B7F8C]">
								Пріоритет
							</label>
							<Select
								defaultValue={selectedIssue?.priority}
								onValueChange={(val) => setValue("priority", val)}
							>
								<SelectTrigger className="border-[#E2E5E8] bg-[#F7F6F2] dark:border-[#2D3D4F] dark:bg-[#1C2B3A]">
									<SelectValue placeholder="Оберіть пріоритет" />
								</SelectTrigger>
								<SelectContent>
									<SelectItem value="low">Низький</SelectItem>
									<SelectItem value="medium">Середній</SelectItem>
									<SelectItem value="high">Високий</SelectItem>
								</SelectContent>
							</Select>
						</div>

						{/* Assignee */}
						<div className="space-y-1">
							<label className="text-xs font-medium text-[#6B7F8C]">
								Виконавець
							</label>
							<Select
								defaultValue={selectedIssue?.assigned_to ?? NO_ASSIGNEE}
								onValueChange={(val) => setValue("assigned_to_username", val)}
							>
								<SelectTrigger className="border-[#E2E5E8] bg-[#F7F6F2] dark:border-[#2D3D4F] dark:bg-[#1C2B3A]">
									<SelectValue placeholder="Оберіть виконавця" />
								</SelectTrigger>
								<SelectContent>
									<SelectItem value={NO_ASSIGNEE}>— Не призначено —</SelectItem>
									{workers.map((w) => (
										<SelectItem key={w.username} value={w.username}>
											{w.full_name || w.username}
											<span className="ml-1 text-xs text-[#6B7F8C]">
												{OCCUPATION_LABELS[w.occupation] ?? w.occupation}
											</span>
										</SelectItem>
									))}
								</SelectContent>
							</Select>
						</div>

						<DialogFooter className="pt-2">
							<Button
								type="button"
								variant="outline"
								onClick={() => setDialogOpen(false)}
								className="border-[#E2E5E8] dark:border-[#2D3D4F]"
							>
								Скасувати
							</Button>
							<Button
								type="submit"
								disabled={isUpdating}
								className="bg-[#3D7A8A] text-white hover:bg-[#336678]"
							>
								{isUpdating ? "Збереження..." : "Зберегти"}
							</Button>
						</DialogFooter>
					</form>
				</DialogContent>
			</Dialog>
		</div>
	);
}
