"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { ColumnDef } from "@tanstack/react-table";
import { toast } from "react-toastify";
import { Pencil } from "lucide-react";

import { DataTable } from "@/components/admin/DataTable";
import StatusBadge from "@/components/admin/StatusBadge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
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
} from "@/lib/redux/features/admin/adminApiSlice";
import { Issue } from "@/types";
import { extractErrorMessage } from "@/utils";

const editSchema = z.object({
	status: z.string().min(1),
	priority: z.string().min(1),
	assigned_to_username: z.string().optional(),
});

type EditFormValues = z.infer<typeof editSchema>;

export default function AdminIssuesPage() {
	const { data, isLoading } = useGetAdminIssuesQuery();
	const [updateIssue, { isLoading: isUpdating }] = useAdminUpdateIssueMutation();

	const [selectedIssue, setSelectedIssue] = useState<Issue | null>(null);
	const [dialogOpen, setDialogOpen] = useState(false);

	const { register, handleSubmit, setValue, reset } = useForm<EditFormValues>({
		resolver: zodResolver(editSchema),
	});

	const openEdit = (issue: Issue) => {
		setSelectedIssue(issue);
		reset({
			status: issue.status,
			priority: issue.priority,
			assigned_to_username: issue.assigned_to ?? "",
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
				assigned_to_username: values.assigned_to_username || null,
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
				<span className="font-medium text-[#1C2B3A] dark:text-white max-w-[200px] truncate block">
					{row.original.title}
				</span>
			),
		},
		{
			accessorKey: "reported_by",
			header: "Подав",
			cell: ({ row }) => (
				<span className="text-[#6B7F8C]">{row.original.reported_by}</span>
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
					<span className="text-[#6B7F8C] text-sm">Не призначено</span>
				),
		},
		{
			id: "actions",
			header: "Дії",
			cell: ({ row }) => (
				<Button
					variant="outline"
					size="sm"
					onClick={() => openEdit(row.original)}
					className="border-[#E2E5E8] dark:border-[#2D3D4F] text-[#3D7A8A] hover:bg-[#EBF3F5] dark:hover:bg-[#1A2E3A]"
				>
					<Pencil className="h-3.5 w-3.5 mr-1" />
					Редагувати
				</Button>
			),
		},
	];

	return (
		<div className="space-y-6">
			<div>
				<h2 className="text-2xl font-bold text-[#1C2B3A] dark:text-white">
					Заявки
				</h2>
				<p className="text-[#6B7F8C] text-sm mt-1">
					Усі заявки на обслуговування
				</p>
			</div>

			<div className="bg-white dark:bg-[#162032] rounded-xl border border-[#E2E5E8] dark:border-[#2D3D4F] p-6 shadow-sm">
				<DataTable
					columns={columns}
					data={issues}
					isLoading={isLoading}
					searchPlaceholder="Пошук заявок..."
				/>
			</div>

			{/* Edit Dialog */}
			<Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
				<DialogContent className="bg-white dark:bg-[#162032] border-[#E2E5E8] dark:border-[#2D3D4F] max-w-md">
					<DialogHeader>
						<DialogTitle className="text-[#1C2B3A] dark:text-white">
							Редагувати заявку
						</DialogTitle>
					</DialogHeader>

					{selectedIssue && (
						<p className="text-sm text-[#6B7F8C] -mt-2 truncate">
							{selectedIssue.title}
						</p>
					)}

					<form onSubmit={handleSubmit(onSubmit)} className="space-y-4 mt-2">
						<div className="space-y-1">
							<label className="text-xs font-medium text-[#6B7F8C]">
								Статус
							</label>
							<Select
								defaultValue={selectedIssue?.status}
								onValueChange={(val) => setValue("status", val)}
							>
								<SelectTrigger className="border-[#E2E5E8] dark:border-[#2D3D4F] bg-[#F7F6F2] dark:bg-[#1C2B3A]">
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

						<div className="space-y-1">
							<label className="text-xs font-medium text-[#6B7F8C]">
								Пріоритет
							</label>
							<Select
								defaultValue={selectedIssue?.priority}
								onValueChange={(val) => setValue("priority", val)}
							>
								<SelectTrigger className="border-[#E2E5E8] dark:border-[#2D3D4F] bg-[#F7F6F2] dark:bg-[#1C2B3A]">
									<SelectValue placeholder="Оберіть пріоритет" />
								</SelectTrigger>
								<SelectContent>
									<SelectItem value="low">Низький</SelectItem>
									<SelectItem value="medium">Середній</SelectItem>
									<SelectItem value="high">Високий</SelectItem>
								</SelectContent>
							</Select>
						</div>

						<div className="space-y-1">
							<label className="text-xs font-medium text-[#6B7F8C]">
								Виконавець (нікнейм, порожньо — зняти призначення)
							</label>
							<Input
								{...register("assigned_to_username")}
								placeholder="username або порожньо"
								className="border-[#E2E5E8] dark:border-[#2D3D4F] bg-[#F7F6F2] dark:bg-[#1C2B3A]"
							/>
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
								className="bg-[#3D7A8A] hover:bg-[#336678] text-white"
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
