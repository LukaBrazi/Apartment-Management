"use client";

import { useState } from "react";
import { ColumnDef } from "@tanstack/react-table";
import { toast } from "react-toastify";
import { Building2, Pencil, Plus, Trash2, X, Check } from "lucide-react";
import { format } from "date-fns";

import { DataTable } from "@/components/admin/DataTable";
import ManageEntrancesModal from "@/components/admin/ManageEntrancesModal";
import {
	useAdminGetBuildingsQuery,
	useAdminCreateBuildingMutation,
	useAdminUpdateBuildingMutation,
	useAdminDeleteBuildingMutation,
} from "@/lib/redux/features/admin/adminApiSlice";
import { Building, BuildingCreateData, EntranceCreatePayload } from "@/types";
import { extractErrorMessage } from "@/utils";

const inputCls =
	"rounded-xl border border-[#E2E5E8] bg-[#F7F6F2] px-3 py-2 text-sm dark:border-[#2D3D4F] dark:bg-[#1C2B3A] dark:text-white focus:outline-none focus:border-[#3D7A8A] focus:ring-1 focus:ring-[#3D7A8A] w-full";
const labelCls = "text-xs font-medium text-[#6B7F8C]";

const MAX_ENTRANCES = 20;
const MAX_APARTMENTS_PER_ENTRANCE = 500;
const MAX_NAME_LENGTH = 20;

const emptyCreate: BuildingCreateData = {
	name: "",
	address: "",
	city: "",
	is_active: true,
	entrances: [{ name: "1", apartments_count: 1 }],
};

interface EditState {
	name: string;
	address: string;
	city: string;
	is_active: boolean;
}

interface EntranceErrors {
	name?: string;
	apartments_count?: string;
}

interface CreateErrors {
	name?: string;
	address?: string;
	entrances?: EntranceErrors[];
}

export default function AdminBuildingsPage() {
	const { data, isLoading } = useAdminGetBuildingsQuery();
	const [createBuilding, { isLoading: isCreating }] = useAdminCreateBuildingMutation();
	const [updateBuilding, { isLoading: isUpdating }] = useAdminUpdateBuildingMutation();
	const [deleteBuilding, { isLoading: isDeleting }] = useAdminDeleteBuildingMutation();

	const [showCreateForm, setShowCreateForm] = useState(false);
	const [createForm, setCreateForm] = useState<BuildingCreateData>(emptyCreate);
	const [createErrors, setCreateErrors] = useState<CreateErrors>({});

	const [editingPkid, setEditingPkid] = useState<number | null>(null);
	const [editForm, setEditForm] = useState<EditState>({
		name: "",
		address: "",
		city: "",
		is_active: true,
	});

	const [deletingPkid, setDeletingPkid] = useState<number | null>(null);

	// Entrances modal state
	const [entrancesBuilding, setEntrancesBuilding] = useState<Building | null>(null);
	const [entrancesModalOpen, setEntrancesModalOpen] = useState(false);

	const buildings = data?.buildings ?? [];

	// ── Helpers for entrances repeater ──────────────────────────────────

	const addEntrance = () => {
		setCreateForm((f) => {
			const list = f.entrances ?? [];
			if (list.length >= MAX_ENTRANCES) return f;
			const nextDefaultName = String(list.length + 1);
			return {
				...f,
				entrances: [...list, { name: nextDefaultName, apartments_count: 1 }],
			};
		});
	};

	const removeEntrance = (idx: number) => {
		setCreateForm((f) => {
			const list = f.entrances ?? [];
			if (list.length <= 1) return f; // keep min 1
			return { ...f, entrances: list.filter((_, i) => i !== idx) };
		});
	};

	const updateEntrance = (idx: number, patch: Partial<EntranceCreatePayload>) => {
		setCreateForm((f) => {
			const list = f.entrances ?? [];
			return {
				...f,
				entrances: list.map((e, i) => (i === idx ? { ...e, ...patch } : e)),
			};
		});
	};

	// ── Validation ──────────────────────────────────────────────────────

	const validateCreate = (): boolean => {
		const errs: CreateErrors = {};
		if (!createForm.name.trim()) errs.name = "Обовʼязкове поле";
		if (!createForm.address.trim()) errs.address = "Обовʼязкове поле";

		const entrances = createForm.entrances ?? [];
		const entranceErrors: EntranceErrors[] = entrances.map((e) => {
			const eErr: EntranceErrors = {};
			if (!e.name.trim()) eErr.name = "Обовʼязкове поле";
			else if (e.name.length > MAX_NAME_LENGTH)
				eErr.name = `Максимум ${MAX_NAME_LENGTH} символів`;
			if (!Number.isFinite(e.apartments_count) || e.apartments_count < 1)
				eErr.apartments_count = "Має бути ≥ 1";
			else if (e.apartments_count > MAX_APARTMENTS_PER_ENTRANCE)
				eErr.apartments_count = `Максимум ${MAX_APARTMENTS_PER_ENTRANCE}`;
			return eErr;
		});
		if (entranceErrors.some((eErr) => Object.keys(eErr).length > 0)) {
			errs.entrances = entranceErrors;
		}

		// Duplicate names check
		const names = entrances.map((e) => e.name.trim()).filter(Boolean);
		const dupSet = new Set<string>();
		const seen = new Set<string>();
		names.forEach((n) => {
			if (seen.has(n)) dupSet.add(n);
			seen.add(n);
		});
		if (dupSet.size > 0) {
			const dupErrs: EntranceErrors[] = entrances.map((e) =>
				dupSet.has(e.name.trim()) ? { name: "Дублікат назви" } : {},
			);
			errs.entrances = (errs.entrances ?? []).map((eErr, i) => ({
				...eErr,
				...dupErrs[i],
			}));
		}

		setCreateErrors(errs);
		// Form is valid only if no top-level errors AND no per-entrance errors.
		const hasEntranceErrors =
			errs.entrances?.some((eErr) => Object.keys(eErr).length > 0) ?? false;
		return !errs.name && !errs.address && !hasEntranceErrors;
	};

	// ── Submit handlers ─────────────────────────────────────────────────

	const handleCreate = async (e: React.FormEvent) => {
		e.preventDefault();
		if (!validateCreate()) return;
		try {
			await createBuilding(createForm).unwrap();
			const entrances = createForm.entrances ?? [];
			const totalUnits = entrances.reduce((s, en) => s + (en.apartments_count || 0), 0);
			toast.success(
				`Будинок створено: ${entrances.length} підʼїздів, ${totalUnits} квартир`,
			);
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

	const openEntrancesModal = (building: Building) => {
		setEntrancesBuilding(building);
		setEntrancesModalOpen(true);
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
							onClick={() => openEntrancesModal(building)}
							className="inline-flex items-center gap-1 rounded-lg border border-[#E2E5E8] dark:border-[#2D3D4F] px-3 py-1.5 text-xs font-medium text-[#3D7A8A] hover:bg-[#EBF3F5] dark:hover:bg-[#1A2E3A] transition-colors"
						>
							<Building2 className="h-3.5 w-3.5" />
							Підʼїзди
						</button>
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

	const entrancesList = createForm.entrances ?? [];
	const totalEntrancesPlanned = entrancesList.length;
	const totalUnitsPlanned = entrancesList.reduce(
		(s, e) => s + (Number(e.apartments_count) || 0),
		0,
	);

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

						{/* ── Entrances repeater ────────────────────────────── */}
						<div className="rounded-xl border border-[#E2E5E8] dark:border-[#2D3D4F] p-4 space-y-3">
							<div className="flex items-center justify-between">
								<div>
									<h4 className="text-sm font-semibold text-[#1C2B3A] dark:text-white">
										Підʼїзди ({totalEntrancesPlanned}/{MAX_ENTRANCES})
									</h4>
									<p className="text-xs text-[#6B7F8C] mt-0.5">
										Заплановано квартир: <strong>{totalUnitsPlanned}</strong>
									</p>
								</div>
								<button
									type="button"
									onClick={addEntrance}
									disabled={totalEntrancesPlanned >= MAX_ENTRANCES}
									className="inline-flex items-center gap-1 rounded-lg border border-[#E2E5E8] dark:border-[#2D3D4F] px-3 py-1.5 text-xs font-medium text-[#3D7A8A] hover:bg-[#EBF3F5] dark:hover:bg-[#1A2E3A] disabled:opacity-50 transition-colors"
								>
									<Plus className="h-3.5 w-3.5" />
									Додати підʼїзд
								</button>
							</div>

							<div className="space-y-2">
								{entrancesList.map((entrance, idx) => {
									const eErrs = createErrors.entrances?.[idx] ?? {};
									return (
										<div
											key={idx}
											className="grid grid-cols-12 gap-2 items-start"
										>
											<div className="col-span-5 space-y-1">
												<label className={labelCls}>
													Назва підʼїзду
												</label>
												<input
													value={entrance.name}
													maxLength={MAX_NAME_LENGTH}
													onChange={(e) =>
														updateEntrance(idx, { name: e.target.value })
													}
													placeholder='напр. "1" або "А"'
													className={inputCls}
												/>
												{eErrs.name && (
													<p className="text-xs text-red-500">
														{eErrs.name}
													</p>
												)}
											</div>
											<div className="col-span-5 space-y-1">
												<label className={labelCls}>Кількість квартир</label>
												<input
													type="number"
													min={1}
													max={MAX_APARTMENTS_PER_ENTRANCE}
													value={entrance.apartments_count}
													onChange={(e) =>
														updateEntrance(idx, {
															apartments_count: Number(e.target.value) || 0,
														})
													}
													className={inputCls}
												/>
												{eErrs.apartments_count && (
													<p className="text-xs text-red-500">
														{eErrs.apartments_count}
													</p>
												)}
											</div>
											<div className="col-span-2 flex items-end h-full">
												<button
													type="button"
													onClick={() => removeEntrance(idx)}
													disabled={entrancesList.length <= 1}
													title="Видалити підʼїзд"
													className="inline-flex items-center gap-1 rounded-lg border border-red-200 dark:border-red-900 px-2 py-2 text-xs font-medium text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 disabled:opacity-30 disabled:hover:bg-transparent transition-colors w-full justify-center"
												>
													<X className="h-3.5 w-3.5" />
												</button>
											</div>
										</div>
									);
								})}
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

			<ManageEntrancesModal
				building={entrancesBuilding}
				open={entrancesModalOpen}
				onOpenChange={(v) => {
					setEntrancesModalOpen(v);
					if (!v) setEntrancesBuilding(null);
				}}
			/>
		</div>
	);
}
