"use client";

import { useState } from "react";
import { Announcement, AnnouncementCreateData } from "@/types";
import {
	useGetAdminAnnouncementsQuery,
	useCreateAnnouncementMutation,
	useUpdateAnnouncementMutation,
	useDeleteAnnouncementMutation,
} from "@/lib/redux/features/admin/adminApiSlice";
import { useGetBuildingsQuery } from "@/lib/redux/features/apartment/apartmentApiSlice";
import { toast } from "react-toastify";
import { Plus, Pencil, Trash2, X, Check, Eye, EyeOff } from "lucide-react";
import { Button } from "@/components/ui/button";

interface AnnouncementFormState {
	building: string;
	title: string;
	body: string;
	is_active: boolean;
	notify_subscribers: boolean;
}

const emptyForm: AnnouncementFormState = {
	building: "",
	title: "",
	body: "",
	is_active: true,
	notify_subscribers: false,
};

export default function AdminPosts() {
	const { data: announcementsData, isLoading } = useGetAdminAnnouncementsQuery();
	const { data: buildingsData } = useGetBuildingsQuery();
	const [createAnnouncement] = useCreateAnnouncementMutation();
	const [updateAnnouncement] = useUpdateAnnouncementMutation();
	const [deleteAnnouncement] = useDeleteAnnouncementMutation();

	const [showForm, setShowForm] = useState(false);
	const [editingId, setEditingId] = useState<string | null>(null);
	const [form, setForm] = useState<AnnouncementFormState>(emptyForm);

	const announcements = announcementsData?.results ?? [];
	const buildings = Array.isArray(buildingsData?.buildings) ? buildingsData.buildings : [];

	const handleOpenCreate = () => {
		setEditingId(null);
		setForm({ ...emptyForm, building: buildings[0]?.id ?? "" });
		setShowForm(true);
	};

	const handleOpenEdit = (a: Announcement) => {
		setEditingId(a.id);
		setForm({
			building: a.building,
			title: a.title,
			body: a.body,
			is_active: a.is_active,
			notify_subscribers: false, // reset on edit — don't re-send notifications
		});
		setShowForm(true);
	};

	const handleSubmit = async () => {
		if (!form.building || !form.title.trim() || !form.body.trim()) {
			toast.error("Заповніть всі поля");
			return;
		}

		try {
			if (editingId) {
				await updateAnnouncement({ id: editingId, ...form }).unwrap();
				toast.success("Новину оновлено");
			} else {
				await createAnnouncement(form as AnnouncementCreateData).unwrap();
				toast.success("Новину створено");
			}
			setShowForm(false);
			setForm(emptyForm);
		} catch {
			toast.error("Помилка збереження");
		}
	};

	const handleDelete = async (id: string) => {
		if (!window.confirm("Видалити новину?")) return;
		try {
			await deleteAnnouncement(id).unwrap();
			toast.success("Новину видалено");
		} catch {
			toast.error("Помилка видалення");
		}
	};

	const handleToggleActive = async (a: Announcement) => {
		try {
			await updateAnnouncement({ id: a.id, is_active: !a.is_active }).unwrap();
			toast.success(a.is_active ? "Новину приховано" : "Новину опубліковано");
		} catch {
			toast.error("Помилка оновлення");
		}
	};

	return (
		<div className="space-y-4">
			{/* Form panel */}
			{showForm && (
				<div className="rounded-2xl border border-[#3D7A8A] bg-white p-6 dark:border-[#5BA3B5] dark:bg-[#162032]">
					<div className="mb-4 flex items-center justify-between">
						<h3 className="font-semibold text-[#1C2B3A] dark:text-white">
							{editingId ? "Редагувати новину" : "Нова новина"}
						</h3>
						<button
							onClick={() => setShowForm(false)}
							className="rounded-lg p-1 text-[#6B7F8C] hover:bg-[#F7F6F2] dark:hover:bg-[#1E2D3D]"
						>
							<X className="h-4 w-4" />
						</button>
					</div>

					<div className="space-y-4">
						{/* Building */}
						<div>
							<label className="mb-1 block text-xs font-medium text-[#6B7F8C]">
								Будинок
							</label>
							<select
								value={form.building}
								onChange={(e) => setForm({ ...form, building: e.target.value })}
								className="w-full rounded-xl border border-[#E2E5E8] bg-white px-3 py-2 text-sm text-[#1C2B3A] focus:border-[#3D7A8A] focus:outline-none focus:ring-1 focus:ring-[#3D7A8A] dark:border-[#2D3D4F] dark:bg-[#1E2D3D] dark:text-white"
							>
								<option value="">Оберіть будинок</option>
								{buildings.map((b) => (
									<option key={b.id} value={b.id}>
										{b.name}
									</option>
								))}
							</select>
						</div>

						{/* Title */}
						<div>
							<label className="mb-1 block text-xs font-medium text-[#6B7F8C]">
								Заголовок
							</label>
							<input
								type="text"
								value={form.title}
								onChange={(e) => setForm({ ...form, title: e.target.value })}
								placeholder="Заголовок новини..."
								className="w-full rounded-xl border border-[#E2E5E8] bg-white px-3 py-2 text-sm text-[#1C2B3A] placeholder:text-[#6B7F8C] focus:border-[#3D7A8A] focus:outline-none focus:ring-1 focus:ring-[#3D7A8A] dark:border-[#2D3D4F] dark:bg-[#1E2D3D] dark:text-white dark:placeholder:text-[#6B7F8C]"
							/>
						</div>

						{/* Body */}
						<div>
							<label className="mb-1 block text-xs font-medium text-[#6B7F8C]">
								Зміст
							</label>
							<textarea
								value={form.body}
								onChange={(e) => setForm({ ...form, body: e.target.value })}
								placeholder="Текст новини..."
								rows={5}
								className="w-full rounded-xl border border-[#E2E5E8] bg-white px-3 py-2 text-sm text-[#1C2B3A] placeholder:text-[#6B7F8C] focus:border-[#3D7A8A] focus:outline-none focus:ring-1 focus:ring-[#3D7A8A] dark:border-[#2D3D4F] dark:bg-[#1E2D3D] dark:text-white dark:placeholder:text-[#6B7F8C]"
							/>
						</div>

						{/* Active toggle */}
						<label className="flex cursor-pointer items-center gap-3">
							<div className="relative">
								<input
									type="checkbox"
									checked={form.is_active}
									onChange={(e) => setForm({ ...form, is_active: e.target.checked })}
									className="sr-only"
								/>
								<div
									className={`h-5 w-9 rounded-full transition-colors ${form.is_active ? "bg-[#3D7A8A] dark:bg-[#5BA3B5]" : "bg-[#E2E5E8] dark:bg-[#2D3D4F]"}`}
								>
									<div
										className={`absolute top-0.5 h-4 w-4 rounded-full bg-white shadow transition-transform ${form.is_active ? "translate-x-4" : "translate-x-0.5"}`}
									/>
								</div>
							</div>
							<span className="text-sm text-[#1C2B3A] dark:text-[#D1DCE5]">
								Опублікувати одразу
							</span>
						</label>

						{/* Notify Telegram subscribers toggle */}
						<label className="flex cursor-pointer items-center gap-3">
							<div className="relative">
								<input
									type="checkbox"
									checked={form.notify_subscribers}
									onChange={(e) => setForm({ ...form, notify_subscribers: e.target.checked })}
									className="sr-only"
								/>
								<div
									className={`h-5 w-9 rounded-full transition-colors ${form.notify_subscribers ? "bg-[#1E2761] dark:bg-[#CADCFC]" : "bg-[#E2E5E8] dark:bg-[#2D3D4F]"}`}
								>
									<div
										className={`absolute top-0.5 h-4 w-4 rounded-full bg-white shadow transition-transform ${form.notify_subscribers ? "translate-x-4" : "translate-x-0.5"}`}
									/>
								</div>
							</div>
							<span className="text-sm text-[#1C2B3A] dark:text-[#D1DCE5]">
								Сповістити підписників у Telegram
							</span>
						</label>

						<div className="flex items-center gap-2 pt-2">
							<Button
								onClick={handleSubmit}
								className="gap-2 rounded-xl bg-[#3D7A8A] text-white hover:bg-[#2E6070] dark:bg-[#5BA3B5] dark:hover:bg-[#4A8FA0]"
							>
								<Check className="h-4 w-4" />
								{editingId ? "Зберегти зміни" : "Створити"}
							</Button>
							<Button
								variant="outline"
								onClick={() => setShowForm(false)}
								className="rounded-xl border-[#E2E5E8] text-[#6B7F8C] hover:bg-[#F7F6F2] dark:border-[#2D3D4F] dark:hover:bg-[#1E2D3D]"
							>
								Скасувати
							</Button>
						</div>
					</div>
				</div>
			)}

			{/* Main card */}
			<div className="rounded-2xl border border-[#E2E5E8] bg-white p-6 dark:border-[#2D3D4F] dark:bg-[#162032]">
				<div className="mb-6 flex items-center justify-between">
					<h2 className="text-lg font-semibold text-[#1C2B3A] dark:text-white">
						Новини та оголошення
						<span className="ml-2 rounded-full bg-[#EBF3F5] px-2.5 py-0.5 text-xs font-medium text-[#3D7A8A] dark:bg-[#1A2E3A] dark:text-[#5BA3B5]">
							{announcements.length}
						</span>
					</h2>
					<Button
						onClick={handleOpenCreate}
						className="gap-2 rounded-xl bg-[#3D7A8A] text-white hover:bg-[#2E6070] dark:bg-[#5BA3B5] dark:hover:bg-[#4A8FA0]"
						size="sm"
					>
						<Plus className="h-4 w-4" />
						Нова новина
					</Button>
				</div>

				{isLoading ? (
					<div className="space-y-3">
						{Array.from({ length: 4 }).map((_, i) => (
							<div
								key={i}
								className="h-20 animate-pulse rounded-xl bg-[#F7F6F2] dark:bg-[#1E2D3D]"
							/>
						))}
					</div>
				) : announcements.length === 0 ? (
					<div className="flex flex-col items-center justify-center py-16 text-[#6B7F8C]">
						<p className="text-sm">Новини відсутні</p>
					</div>
				) : (
					<div className="space-y-3">
						{announcements.map((a) => (
							<div
								key={a.id}
								className={`flex items-start gap-4 rounded-xl border p-4 transition-colors ${
									a.is_active
										? "border-[#E2E5E8] bg-[#FAFAFA] dark:border-[#2D3D4F] dark:bg-[#1A2835]"
										: "border-[#E2E5E8] bg-[#F7F6F2] opacity-60 dark:border-[#2D3D4F] dark:bg-[#162032]"
								}`}
							>
								<div className="flex-1 min-w-0">
									<div className="flex flex-wrap items-center gap-2 mb-1">
										<span className="text-xs font-medium text-[#3D7A8A] dark:text-[#5BA3B5]">
											{a.building_name}
										</span>
										<span className="text-xs text-[#6B7F8C]">
											{new Date(a.created_at).toLocaleDateString("uk-UA")}
										</span>
										{!a.is_active && (
											<span className="rounded-full bg-[#E2E5E8] px-2 py-0.5 text-xs text-[#6B7F8C] dark:bg-[#2D3D4F]">
												Приховано
											</span>
										)}
									</div>
									<p className="font-semibold text-[#1C2B3A] dark:text-white">
										{a.title}
									</p>
									<p className="mt-1 text-sm text-[#6B7F8C] line-clamp-2">
										{a.body}
									</p>
								</div>
								<div className="flex shrink-0 items-center gap-1">
									<button
										onClick={() => handleToggleActive(a)}
										title={a.is_active ? "Приховати" : "Опублікувати"}
										className="rounded-lg p-2 text-[#6B7F8C] hover:bg-[#EBF3F5] hover:text-[#3D7A8A] dark:hover:bg-[#1A2E3A] dark:hover:text-[#5BA3B5]"
									>
										{a.is_active ? (
											<EyeOff className="h-4 w-4" />
										) : (
											<Eye className="h-4 w-4" />
										)}
									</button>
									<button
										onClick={() => handleOpenEdit(a)}
										className="rounded-lg p-2 text-[#6B7F8C] hover:bg-[#EBF3F5] hover:text-[#3D7A8A] dark:hover:bg-[#1A2E3A] dark:hover:text-[#5BA3B5]"
									>
										<Pencil className="h-4 w-4" />
									</button>
									<button
										onClick={() => handleDelete(a.id)}
										className="rounded-lg p-2 text-[#6B7F8C] hover:bg-red-50 hover:text-red-500 dark:hover:bg-red-900/20"
									>
										<Trash2 className="h-4 w-4" />
									</button>
								</div>
							</div>
						))}
					</div>
				)}
			</div>
		</div>
	);
}
