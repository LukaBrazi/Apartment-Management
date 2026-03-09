"use client";

import { useState } from "react";
import { ColumnDef } from "@tanstack/react-table";
import { toast } from "react-toastify";
import { Pencil, Plus, Trash2, X, Check } from "lucide-react";
import { format } from "date-fns";

import { DataTable } from "@/components/admin/DataTable";
import {
	useAdminGetBuildingsQuery,
	useAdminCreateBuildingMutation,
	useAdminUpdateBuildingMutation,
	useAdminDeleteBuildingMutation,
} from "@/lib/redux/features/admin/adminApiSlice";
import { Building, BuildingCreateData } from "@/types";
import { extractErrorMessage } from "@/utils";

const inputCls =
	"rounded-xl border border-[#E2E5E8] bg-[#F7F6F2] px-3 py-2 text-sm dark:border-[#2D3D4F] dark:bg-[#1C2B3A] dark:text-white focus:outline-none focus:border-[#3D7A8A] focus:ring-1 focus:ring-[#3D7A8A] w-full";
const labelCls = "text-xs font-medium text-[#6B7F8C]";

const emptyCreate: BuildingCreateData = {
	name: "",
	address: "",
	city: "",
	is_active: true,
};

interface EditState {
	name: string;
	address: string;
	city: string;
	is_active: boolean;
}

export default function AdminBuildingsPage() {
	const { data, isLoading } = useAdminGetBuildingsQuery();
	const [createBuilding, { isLoading: isCreating }] = useAdminCreateBuildingMutation();
	const [updateBuilding, { isLoading: isUpdating }] = useAdminUpdateBuildingMutation();
	const [deleteBuilding, { isLoading: isDeleting }] = useAdminDeleteBuildingMutation();

	const [showCreateForm, setShowCreateForm] = useState(false);
	const [createForm, setCreateForm] = useState<BuildingCreateData>(emptyCreate);
	const [createErrors, setCreateErrors] = useState<Partial<Record<keyof BuildingCreateData, string>>>({});

	const [editingPkid, setEditingPkid] = useState<number | null>(null);
	const [editForm, setEditForm] = useState<EditState>({
		name: "",
		address: "",
		city: "",
		is_active: true,
	});

	const [deletingPkid, setDeletingPkid] = useState<number | null>(null);

	const buildings = data?.buildings ?? [];

	const validateCreate = (): boolean => {
		const errs: Partial<Record<keyof BuildingCreateData, string>> = {};
		if (!createForm.name.trim()) errs.name = "Обов'язкове поле";
		if (!createForm.address.trim()) errs.address = "Обов'язкове поле";
		setCreateErrors(errs);
		return Object.keys(errs).length === 0;
	};

	const handleCreate = async (e: React.FormEvent) => {
		e.preventDefault();
		if (!validateCreate()) return;
		try {
			await createBuilding(createForm).unwrap();
			toast.success("Будинок створено");
			setCreateForm(emptyCreate);
			setCreateErrors({});
			setShowCreateForm(false);
		} catch (err) {
			toast.error(extractErrorMessage(err) || "Помилка створення");
		}
	};

	const openEdit = (building: Building) => {
		setEditingPkid(building.pkid);
		setEditForm({
			name: building.name,
			address: building.address,
			city: building.city,
			is_active: building.is_active,
		});
	};

	const handleEdit = async (pkid: number) => {
		try {
			await updateBuilding({ pkid, ...editForm }).unwrap();
			toast.success("Будинок оновлено");
			setEditingPkid(null);
		} catch (err) {
			toast.error(extractErrorMessage(err) || "Помилка оновлення");
		}
	};

	const handleDelete = async (pkid: number) => {
		try {
			await deleteBuilding(pkid).unwrap();
			toast.success("Будинок видалено");
			setDeletingPkid(null);
		} catch (err) {
			toast.error(extractErrorMessage(err) || "Помилка видалення");
		}
	};

	const columns: ColumnDef<Building, unknown>[] = [
		{
			accessorKey: "name",
			header: "Назва",
			cell: ({ row }) => {
				const building = row.original;
				if (editingPkid === building.pkid) {
					return (
						<input
							value={editForm.name}
							onChange={(e) => setEditForm((f) => ({ ...f, name: e.target.value }))}
							className="rounded-xl border border-[#E2E5E8] bg-[#F7F6F2] px-2 py-1 text-sm dark:border-[#2D3D4F] dark:bg-[#1C2B3A] dark:text-white focus:outline-none focus:border-[#3D7A8A] w-full max-w-[160px]"
						/>
					);
				}
				return (
					<span className="font-medium text-[#1C2B3A] dark:text-white">
						{building.name}
					</span>
				);
			},
		},
		{
			accessorKey: "address",
			header: "Адреса",
			cell: ({ row }) => {
				const building = row.original;
				if (editingPkid === building.pkid) {
					return (
						<input
							value={editForm.address}
							onChange={(e) =>
								setEditForm((f) => ({ ...f, address: e.target.value }))
							}
							className="rounded-xl border border-[#E2E5E8] bg-[#F7F6F2] px-2 py-1 text-sm dark:border-[#2D3D4F] dark:bg-[#1C2B3A] dark:text-white focus:outline-none focus:border-[#3D7A8A] w-full max-w-[200px]"
						/>
					);
				}
				return <span className="text-sm text-[#6B7F8C]">{building.address}</span>;
			},
		},
		{
			accessorKey: "city",
			header: "Місто",
			cell: ({ row }) => {
				const building = row.original;
				if (editingPkid === building.pkid) {
					return (
						<input
							value={editForm.city}
							onChange={(e) => setEditForm((f) => ({ ...f, city: e.target.value }))}
							className="rounded-xl border border-[#E2E5E8] bg-[#F7F6F2] px-2 py-1 text-sm dark:border-[#2D3D4F] dark:bg-[#1C2B3A] dark:text-white focus:outline-none focus:border-[#3D7A8A] w-full max-w-[120px]"
						/>
					);
				}
				return <span className="text-sm">{building.city || "—"}</span>;
			},
		},
		{
			accessorKey: "is_active",
			header: "Статус",
			cell: ({ row }) => {
				const building = row.original;
				if (editingPkid === building.pkid) {
					return (
						<button
							type="button"
							role="switch"
							aria-checked={editForm.is_active}
							onClick={() =>
								setEditForm((f) => ({ ...f, is_active: !f.is_active }))
							}
							className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors focus-visible:outline-none ${
								editForm.is_active
									? "bg-[#3D7A8A]"
									: "bg-[#E2E5E8] dark:bg-[#2D3D4F]"
							}`}
						>
							<span
								className={`inline-block h-3.5 w-3.5 transform rounded-full bg-white transition-transform ${
									editForm.is_active ? "translate-x-[18px]" : "translate-x-0.5"
								}`}
							/>
						</button>
					);
				}
				return building.is_active ? (
					<span className="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300">
						Активний
					</span>
				) : (
					<span className="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium bg-slate-100 text-slate-600 dark:bg-slate-800/40 dark:text-slate-400">
						Неактивний
					</span>
				);
			},
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
					return <span className="text-sm text-[#6B7F8C]">{row.original.created_at}</span>;
				}
			},
		},
		{
			id: "actions",
			header: "Дії",
			cell: ({ row }) => {
				const building = row.original;

				if (deletingPkid === building.pkid) {
					return (
						<div className="flex items-center gap-2">
							<span className="text-xs text-[#6B7F8C]">Видалити?</span>
							<button
								onClick={() => handleDelete(building.pkid)}
								disabled={isDeleting}
								className="inline-flex items-center gap-1 rounded-lg px-3 py-1.5 text-xs font-medium bg-red-600 text-white hover:bg-red-700 disabled:opacity-60 transition-colors"
							>
								{isDeleting ? "..." : "Так"}
							</button>
							<button
								onClick={() => setDeletingPkid(null)}
								className="inline-flex items-center gap-1 rounded-lg px-2 py-1.5 text-xs font-medium text-[#6B7F8C] hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
							>
								Ні
							</button>
						</div>
					);
				}

				if (editingPkid === building.pkid) {
					return (
						<div className="flex items-center gap-2">
							<button
								onClick={() => handleEdit(building.pkid)}
								disabled={isUpdating}
								className="inline-flex items-center gap-1 rounded-lg px-3 py-1.5 text-xs font-medium bg-[#3D7A8A] text-white hover:bg-[#2E6070] dark:bg-[#5BA3B5] dark:hover:bg-[#4A8FA0] disabled:opacity-60 transition-colors"
							>
								<Check className="h-3.5 w-3.5" />
								Зберегти
							</button>
							<button
								onClick={() => setEditingPkid(null)}
								className="inline-flex items-center gap-1 rounded-lg px-2 py-1.5 text-xs font-medium text-[#6B7F8C] hover:bg-red-50 hover:text-red-500 dark:hover:bg-red-900/20 transition-colors"
							>
								<X className="h-3.5 w-3.5" />
							</button>
						</div>
					);
				}

				return (
					<div className="flex items-center gap-2">
						<button
							onClick={() => openEdit(building)}
							className="inline-flex items-center gap-1 rounded-lg border border-[#E2E5E8] dark:border-[#2D3D4F] px-3 py-1.5 text-xs font-medium text-[#3D7A8A] hover:bg-[#EBF3F5] dark:hover:bg-[#1A2E3A] transition-colors"
						>
							<Pencil className="h-3.5 w-3.5" />
							Редагувати
						</button>
						<button
							onClick={() => setDeletingPkid(building.pkid)}
							className="inline-flex items-center gap-1 rounded-lg border border-red-200 dark:border-red-900 px-2 py-1.5 text-xs font-medium text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors"
						>
							<Trash2 className="h-3.5 w-3.5" />
						</button>
					</div>
				);
			},
		},
	];

	return (
		<div className="space-y-6">
			<div className="flex items-center justify-between">
				<div>
					<h2 className="text-2xl font-bold text-[#1C2B3A] dark:text-white">
						Будинки
					</h2>
					<p className="text-[#6B7F8C] text-sm mt-1">
						Управління будинками
					</p>
				</div>
				<button
					onClick={() => {
						setCreateForm(emptyCreate);
						setCreateErrors({});
						setShowCreateForm((v) => !v);
					}}
					className="inline-flex items-center gap-2 rounded-xl bg-[#3D7A8A] px-4 py-2 text-sm font-medium text-white hover:bg-[#2E6070] dark:bg-[#5BA3B5] dark:hover:bg-[#4A8FA0] transition-colors"
				>
					{showCreateForm ? (
						<>
							<X className="h-4 w-4" />
							Скасувати
						</>
					) : (
						<>
							<Plus className="h-4 w-4" />
							Додати будинок
						</>
					)}
				</button>
			</div>

			{showCreateForm && (
				<div className="rounded-2xl border border-[#3D7A8A] bg-white p-6 dark:border-[#5BA3B5] dark:bg-[#162032]">
					<h3 className="text-base font-semibold text-[#1C2B3A] dark:text-white mb-4">
						Новий будинок
					</h3>
					<form onSubmit={handleCreate} className="space-y-4">
						<div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
							<div className="space-y-1">
								<label className={labelCls}>Назва</label>
								<input
									value={createForm.name}
									onChange={(e) =>
										setCreateForm((f) => ({ ...f, name: e.target.value }))
									}
									placeholder="Будинок №1"
									className={inputCls}
								/>
								{createErrors.name && (
									<p className="text-xs text-red-500">{createErrors.name}</p>
								)}
							</div>
							<div className="space-y-1">
								<label className={labelCls}>Адреса</label>
								<input
									value={createForm.address}
									onChange={(e) =>
										setCreateForm((f) => ({ ...f, address: e.target.value }))
									}
									placeholder="вул. Шевченка, 1"
									className={inputCls}
								/>
								{createErrors.address && (
									<p className="text-xs text-red-500">{createErrors.address}</p>
								)}
							</div>
							<div className="space-y-1">
								<label className={labelCls}>Місто</label>
								<input
									value={createForm.city}
									onChange={(e) =>
										setCreateForm((f) => ({ ...f, city: e.target.value }))
									}
									placeholder="Київ"
									className={inputCls}
								/>
							</div>
							<div className="space-y-1">
								<label className={labelCls}>Статус</label>
								<div className="flex items-center gap-3 pt-2">
									<button
										type="button"
										role="switch"
										aria-checked={createForm.is_active}
										onClick={() =>
											setCreateForm((f) => ({
												...f,
												is_active: !f.is_active,
											}))
										}
										className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors focus-visible:outline-none ${
											createForm.is_active
												? "bg-[#3D7A8A]"
												: "bg-[#E2E5E8] dark:bg-[#2D3D4F]"
										}`}
									>
										<span
											className={`inline-block h-3.5 w-3.5 transform rounded-full bg-white transition-transform ${
												createForm.is_active
													? "translate-x-[18px]"
													: "translate-x-0.5"
											}`}
										/>
									</button>
									<span className="text-sm text-[#1C2B3A] dark:text-[#D1DCE5]">
										Активний
									</span>
								</div>
							</div>
						</div>
						<div className="flex justify-end">
							<button
								type="submit"
								disabled={isCreating}
								className="inline-flex items-center gap-2 rounded-xl bg-[#3D7A8A] px-5 py-2 text-sm font-medium text-white hover:bg-[#2E6070] dark:bg-[#5BA3B5] dark:hover:bg-[#4A8FA0] disabled:opacity-60 transition-colors"
							>
								{isCreating ? "Створення..." : "Створити будинок"}
							</button>
						</div>
					</form>
				</div>
			)}

			<div className="bg-white dark:bg-[#162032] rounded-xl border border-[#E2E5E8] dark:border-[#2D3D4F] p-6 shadow-sm">
				<DataTable
					columns={columns}
					data={buildings}
					isLoading={isLoading}
					searchPlaceholder="Пошук будинків..."
				/>
			</div>
		</div>
	);
}
