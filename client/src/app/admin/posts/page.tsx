"use client";

import { useState } from "react";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { ColumnDef } from "@tanstack/react-table";
import { toast } from "react-toastify";
import { format } from "date-fns";
import { Plus, Pencil, Trash2 } from "lucide-react";

import { DataTable } from "@/components/admin/DataTable";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
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
	useGetAdminAnnouncementsQuery,
	useCreateAnnouncementMutation,
	useUpdateAnnouncementMutation,
	useDeleteAnnouncementMutation,
} from "@/lib/redux/features/admin/adminApiSlice";
import { useGetBuildingsQuery } from "@/lib/redux/features/apartment/apartmentApiSlice";
import { Announcement } from "@/types";
import { extractErrorMessage } from "@/utils";

const announcementSchema = z.object({
	building: z.string().min(1, "Оберіть будинок"),
	title: z.string().min(1, "Назва обов'язкова").max(200),
	body: z.string().min(1, "Текст обов'язковий"),
	is_active: z.boolean(),
});

type AnnouncementFormValues = z.infer<typeof announcementSchema>;

type DialogMode = "create" | "edit" | "delete" | null;

export default function AdminPostsPage() {
	const { data: announcementsData, isLoading } =
		useGetAdminAnnouncementsQuery();
	const { data: buildingsData } = useGetBuildingsQuery();
	const [createAnnouncement, { isLoading: isCreating }] =
		useCreateAnnouncementMutation();
	const [updateAnnouncement, { isLoading: isUpdating }] =
		useUpdateAnnouncementMutation();
	const [deleteAnnouncement, { isLoading: isDeleting }] =
		useDeleteAnnouncementMutation();

	const [dialogMode, setDialogMode] = useState<DialogMode>(null);
	const [selectedAnnouncement, setSelectedAnnouncement] =
		useState<Announcement | null>(null);

	const { register, handleSubmit, setValue, control, reset, formState: { errors } } =
		useForm<AnnouncementFormValues>({
			resolver: zodResolver(announcementSchema),
			defaultValues: { is_active: true },
		});

	const buildings = buildingsData?.buildings ?? [];
	const announcements = announcementsData?.results ?? [];

	const openCreate = () => {
		reset({ building: "", title: "", body: "", is_active: true });
		setSelectedAnnouncement(null);
		setDialogMode("create");
	};

	const openEdit = (announcement: Announcement) => {
		setSelectedAnnouncement(announcement);
		reset({
			building: announcement.building,
			title: announcement.title,
			body: announcement.body,
			is_active: announcement.is_active,
		});
		setDialogMode("edit");
	};

	const openDelete = (announcement: Announcement) => {
		setSelectedAnnouncement(announcement);
		setDialogMode("delete");
	};

	const closeDialog = () => {
		setDialogMode(null);
		setSelectedAnnouncement(null);
	};

	const onSubmit = async (values: AnnouncementFormValues) => {
		try {
			if (dialogMode === "create") {
				await createAnnouncement(values).unwrap();
				toast.success("Новину створено");
			} else if (dialogMode === "edit" && selectedAnnouncement) {
				await updateAnnouncement({
					id: selectedAnnouncement.id,
					...values,
				}).unwrap();
				toast.success("Новину оновлено");
			}
			closeDialog();
		} catch (e) {
			toast.error(extractErrorMessage(e) || "Помилка збереження");
		}
	};

	const onDelete = async () => {
		if (!selectedAnnouncement) return;
		try {
			await deleteAnnouncement(selectedAnnouncement.id).unwrap();
			toast.success("Новину видалено");
			closeDialog();
		} catch (e) {
			toast.error(extractErrorMessage(e) || "Помилка видалення");
		}
	};

	const columns: ColumnDef<Announcement, unknown>[] = [
		{
			accessorKey: "building_name",
			header: "Будинок",
			cell: ({ row }) => (
				<span className="text-sm">{row.original.building_name}</span>
			),
		},
		{
			accessorKey: "title",
			header: "Назва",
			cell: ({ row }) => (
				<span className="font-medium text-[#1C2B3A] dark:text-white max-w-[240px] truncate block">
					{row.original.title}
				</span>
			),
		},
		{
			accessorKey: "is_active",
			header: "Статус",
			cell: ({ row }) =>
				row.original.is_active ? (
					<span className="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300">
						Активна
					</span>
				) : (
					<span className="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium bg-slate-100 text-slate-600 dark:bg-slate-800/40 dark:text-slate-400">
						Неактивна
					</span>
				),
		},
		{
			accessorKey: "created_at",
			header: "Дата",
			cell: ({ row }) => {
				try {
					return (
						<span className="text-sm text-[#6B7F8C]">
							{format(new Date(row.original.created_at), "dd.MM.yyyy")}
						</span>
					);
				} catch {
					return row.original.created_at;
				}
			},
		},
		{
			id: "actions",
			header: "Дії",
			cell: ({ row }) => (
				<div className="flex items-center gap-2">
					<Button
						variant="outline"
						size="sm"
						onClick={() => openEdit(row.original)}
						className="border-[#E2E5E8] dark:border-[#2D3D4F] text-[#3D7A8A] hover:bg-[#EBF3F5] dark:hover:bg-[#1A2E3A]"
					>
						<Pencil className="h-3.5 w-3.5 mr-1" />
						Редагувати
					</Button>
					<Button
						variant="outline"
						size="sm"
						onClick={() => openDelete(row.original)}
						className="border-red-200 dark:border-red-900 text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20"
					>
						<Trash2 className="h-3.5 w-3.5" />
					</Button>
				</div>
			),
		},
	];

	const isFormOpen = dialogMode === "create" || dialogMode === "edit";

	return (
		<div className="space-y-6">
			<div className="flex items-center justify-between">
				<div>
					<h2 className="text-2xl font-bold text-[#1C2B3A] dark:text-white">
						Новини
					</h2>
					<p className="text-[#6B7F8C] text-sm mt-1">
						Оголошення для мешканців будинків
					</p>
				</div>
				<Button
					onClick={openCreate}
					className="bg-[#3D7A8A] hover:bg-[#336678] text-white gap-2"
				>
					<Plus className="h-4 w-4" />
					Нова новина
				</Button>
			</div>

			<div className="bg-white dark:bg-[#162032] rounded-xl border border-[#E2E5E8] dark:border-[#2D3D4F] p-6 shadow-sm">
				<DataTable
					columns={columns}
					data={announcements}
					isLoading={isLoading}
					searchPlaceholder="Пошук новин..."
				/>
			</div>

			{/* Create / Edit Dialog */}
			<Dialog open={isFormOpen} onOpenChange={(open) => !open && closeDialog()}>
				<DialogContent className="bg-white dark:bg-[#162032] border-[#E2E5E8] dark:border-[#2D3D4F] max-w-lg">
					<DialogHeader>
						<DialogTitle className="text-[#1C2B3A] dark:text-white">
							{dialogMode === "create" ? "Нова новина" : "Редагувати новину"}
						</DialogTitle>
					</DialogHeader>

					<form onSubmit={handleSubmit(onSubmit)} className="space-y-4 mt-2">
						<div className="space-y-1">
							<label className="text-xs font-medium text-[#6B7F8C]">
								Будинок
							</label>
							<Controller
								name="building"
								control={control}
								render={({ field }) => (
									<Select
										value={field.value}
										onValueChange={field.onChange}
									>
										<SelectTrigger className="border-[#E2E5E8] dark:border-[#2D3D4F] bg-[#F7F6F2] dark:bg-[#1C2B3A]">
											<SelectValue placeholder="Оберіть будинок" />
										</SelectTrigger>
										<SelectContent>
											{buildings.map((b) => (
												<SelectItem key={b.id} value={b.id}>
													{b.name} — {b.address}
												</SelectItem>
											))}
										</SelectContent>
									</Select>
								)}
							/>
							{errors.building && (
								<p className="text-xs text-red-500">{errors.building.message}</p>
							)}
						</div>

						<div className="space-y-1">
							<label className="text-xs font-medium text-[#6B7F8C]">
								Назва
							</label>
							<Input
								{...register("title")}
								placeholder="Заголовок оголошення"
								className="border-[#E2E5E8] dark:border-[#2D3D4F] bg-[#F7F6F2] dark:bg-[#1C2B3A]"
							/>
							{errors.title && (
								<p className="text-xs text-red-500">{errors.title.message}</p>
							)}
						</div>

						<div className="space-y-1">
							<label className="text-xs font-medium text-[#6B7F8C]">
								Текст
							</label>
							<Textarea
								{...register("body")}
								rows={5}
								placeholder="Текст оголошення..."
								className="border-[#E2E5E8] dark:border-[#2D3D4F] bg-[#F7F6F2] dark:bg-[#1C2B3A] resize-none"
							/>
							{errors.body && (
								<p className="text-xs text-red-500">{errors.body.message}</p>
							)}
						</div>

						<div className="flex items-center gap-3">
							<Controller
								name="is_active"
								control={control}
								render={({ field }) => (
									<button
										type="button"
										role="switch"
										aria-checked={field.value}
										onClick={() => field.onChange(!field.value)}
										className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#3D7A8A] ${
											field.value
												? "bg-[#3D7A8A]"
												: "bg-[#E2E5E8] dark:bg-[#2D3D4F]"
										}`}
									>
										<span
											className={`inline-block h-3.5 w-3.5 transform rounded-full bg-white transition-transform ${
												field.value ? "translate-x-[18px]" : "translate-x-0.5"
											}`}
										/>
									</button>
								)}
							/>
							<label className="text-sm text-[#1C2B3A] dark:text-[#D1DCE5]">
								Активна (видима мешканцям)
							</label>
						</div>

						<DialogFooter className="pt-2">
							<Button
								type="button"
								variant="outline"
								onClick={closeDialog}
								className="border-[#E2E5E8] dark:border-[#2D3D4F]"
							>
								Скасувати
							</Button>
							<Button
								type="submit"
								disabled={isCreating || isUpdating}
								className="bg-[#3D7A8A] hover:bg-[#336678] text-white"
							>
								{isCreating || isUpdating
									? "Збереження..."
									: dialogMode === "create"
									? "Створити"
									: "Зберегти"}
							</Button>
						</DialogFooter>
					</form>
				</DialogContent>
			</Dialog>

			{/* Delete Confirmation Dialog */}
			<Dialog
				open={dialogMode === "delete"}
				onOpenChange={(open) => !open && closeDialog()}
			>
				<DialogContent className="bg-white dark:bg-[#162032] border-[#E2E5E8] dark:border-[#2D3D4F] max-w-sm">
					<DialogHeader>
						<DialogTitle className="text-[#1C2B3A] dark:text-white">
							Видалити новину?
						</DialogTitle>
					</DialogHeader>
					<p className="text-sm text-[#6B7F8C]">
						Ви впевнені, що хочете видалити новину{" "}
						<span className="font-medium text-[#1C2B3A] dark:text-white">
							&ldquo;{selectedAnnouncement?.title}&rdquo;
						</span>
						? Цю дію не можна скасувати.
					</p>
					<DialogFooter className="pt-2">
						<Button
							type="button"
							variant="outline"
							onClick={closeDialog}
							className="border-[#E2E5E8] dark:border-[#2D3D4F]"
						>
							Скасувати
						</Button>
						<Button
							onClick={onDelete}
							disabled={isDeleting}
							className="bg-red-600 hover:bg-red-700 text-white"
						>
							{isDeleting ? "Видалення..." : "Видалити"}
						</Button>
					</DialogFooter>
				</DialogContent>
			</Dialog>
		</div>
	);
}
