"use client";

import { useState } from "react";
import { toast } from "react-toastify";
import { Pencil, Plus, Trash2, X, Check } from "lucide-react";

import {
	Dialog,
	DialogContent,
	DialogHeader,
	DialogTitle,
	DialogDescription,
} from "@/components/ui/dialog";
import {
	useGetBuildingEntrancesQuery,
	useAdminCreateEntranceMutation,
	useAdminUpdateEntranceMutation,
	useAdminDeleteEntranceMutation,
	useAdminGrowEntranceMutation,
} from "@/lib/redux/features/admin/adminApiSlice";
import { Building } from "@/types";
import { extractErrorMessage } from "@/utils";

const inputCls =
	"rounded-xl border border-[#E2E5E8] bg-[#F7F6F2] px-3 py-2 text-sm dark:border-[#2D3D4F] dark:bg-[#1C2B3A] dark:text-white focus:outline-none focus:border-[#3D7A8A] focus:ring-1 focus:ring-[#3D7A8A] w-full";
const labelCls = "text-xs font-medium text-[#6B7F8C]";

interface Props {
	building: Building | null;
	open: boolean;
	onOpenChange: (v: boolean) => void;
}

export default function ManageEntrancesModal({ building, open, onOpenChange }: Props) {
	const buildingPkid = building?.pkid;
	const { data, isLoading } = useGetBuildingEntrancesQuery(buildingPkid as number, {
		skip: !buildingPkid,
	});
	const [createEntrance, { isLoading: isCreating }] = useAdminCreateEntranceMutation();
	const [updateEntrance] = useAdminUpdateEntranceMutation();
	const [deleteEntrance] = useAdminDeleteEntranceMutation();
	const [growEntrance] = useAdminGrowEntranceMutation();

	const entrances = data?.entrances ?? [];

	// New entrance form state
	const [newName, setNewName] = useState("");
	const [newCount, setNewCount] = useState<number>(1);
	const [newErrors, setNewErrors] = useState<{ name?: string; count?: string }>({});

	// Per-row editing state
	const [renameId, setRenameId] = useState<string | null>(null);
	const [renameValue, setRenameValue] = useState("");
	const [growId, setGrowId] = useState<string | null>(null);
	const [growValue, setGrowValue] = useState<number>(1);
	const [deletingId, setDeletingId] = useState<string | null>(null);

	const validateNew = (): boolean => {
		const errs: { name?: string; count?: string } = {};
		if (!newName.trim()) errs.name = "Обовʼязкове поле";
		else if (newName.length > 20) errs.name = "Максимум 20 символів";
		if (!Number.isFinite(newCount) || newCount < 1) errs.count = "Має бути ≥ 1";
		else if (newCount > 500) errs.count = "Максимум 500";
		setNewErrors(errs);
		return Object.keys(errs).length === 0;
	};

	const handleCreate = async () => {
		if (!buildingPkid) return;
		if (!validateNew()) return;
		try {
			await createEntrance({
				buildingPkid,
				name: newName.trim(),
				apartments_count: newCount,
			}).unwrap();
			toast.success(`Підʼїзд "${newName.trim()}" створено (${newCount} кв.)`);
			setNewName("");
			setNewCount(1);
			setNewErrors({});
		} catch (err) {
			toast.error(extractErrorMessage(err) || "Помилка створення підʼїзду");
		}
	};

	const handleRename = async (id: string) => {
		const trimmed = renameValue.trim();
		if (!trimmed) {
			toast.error("Назва підʼїзду не може бути пустою");
			return;
		}
		if (trimmed.length > 20) {
			toast.error("Максимум 20 символів");
			return;
		}
		try {
			await updateEntrance({ id, name: trimmed }).unwrap();
			toast.success("Підʼїзд перейменовано");
			setRenameId(null);
			setRenameValue("");
		} catch (err) {
			toast.error(extractErrorMessage(err) || "Помилка перейменування");
		}
	};

	const handleGrow = async (id: string) => {
		if (!Number.isFinite(growValue) || growValue < 1) {
			toast.error("Число має бути ≥ 1");
			return;
		}
		try {
			await growEntrance({ id, delta: growValue }).unwrap();
			toast.success(`+${growValue} квартир додано`);
			setGrowId(null);
			setGrowValue(1);
		} catch (err) {
			toast.error(extractErrorMessage(err) || "Помилка додавання квартир");
		}
	};

	const handleDelete = async (id: string) => {
		try {
			await deleteEntrance(id).unwrap();
			toast.success("Підʼїзд видалено");
			setDeletingId(null);
		} catch (err) {
			// 409 Conflict → backend returns custom Ukrainian message
			const msg = extractErrorMessage(err);
			toast.error(
				msg ||
					"Не можна видалити підʼїзд з активними мешканцями",
			);
		}
	};

	return (
		<Dialog open={open} onOpenChange={onOpenChange}>
			<DialogContent className="max-w-2xl">
				<DialogHeader>
					<DialogTitle>Підʼїзди — {building?.name}</DialogTitle>
					<DialogDescription>
						Перейменувати, додати квартири, видалити підʼїзди.
					</DialogDescription>
				</DialogHeader>

				<div className="space-y-4 max-h-[60vh] overflow-y-auto">
					{isLoading && (
						<p className="text-sm text-[#6B7F8C]">Завантаження...</p>
					)}
					{!isLoading && entrances.length === 0 && (
						<p className="text-sm text-[#6B7F8C]">
							У будинку поки нема жодного підʼїзду.
						</p>
					)}

					{entrances.map((e) => (
						<div
							key={e.id}
							className="rounded-xl border border-[#E2E5E8] dark:border-[#2D3D4F] p-3 space-y-2"
						>
							<div className="flex items-center justify-between gap-3 flex-wrap">
								<div className="flex items-center gap-2">
									{renameId === e.id ? (
										<>
											<input
												value={renameValue}
												onChange={(ev) => setRenameValue(ev.target.value)}
												className={inputCls + " max-w-[140px]"}
												maxLength={20}
											/>
											<button
												onClick={() => handleRename(e.id)}
												className="inline-flex items-center gap-1 rounded-lg px-2 py-1.5 text-xs font-medium bg-[#3D7A8A] text-white hover:bg-[#2E6070]"
											>
												<Check className="h-3.5 w-3.5" />
											</button>
											<button
												onClick={() => {
													setRenameId(null);
													setRenameValue("");
												}}
												className="inline-flex items-center gap-1 rounded-lg px-2 py-1.5 text-xs text-[#6B7F8C] hover:bg-slate-100 dark:hover:bg-slate-800"
											>
												<X className="h-3.5 w-3.5" />
											</button>
										</>
									) : (
										<>
											<span className="font-medium text-[#1C2B3A] dark:text-white">
												Підʼїзд {e.name}
											</span>
											<span className="text-xs text-[#6B7F8C]">
												{e.units_count} квартир
											</span>
										</>
									)}
								</div>

								<div className="flex items-center gap-2">
									{renameId !== e.id && (
										<button
											onClick={() => {
												setRenameId(e.id);
												setRenameValue(e.name);
											}}
											className="inline-flex items-center gap-1 rounded-lg border border-[#E2E5E8] dark:border-[#2D3D4F] px-2 py-1.5 text-xs text-[#3D7A8A] hover:bg-[#EBF3F5] dark:hover:bg-[#1A2E3A]"
										>
											<Pencil className="h-3.5 w-3.5" />
											Перейменувати
										</button>
									)}

									{deletingId === e.id ? (
										<div className="flex items-center gap-1.5">
											<span className="text-xs text-[#6B7F8C]">Видалити?</span>
											<button
												onClick={() => handleDelete(e.id)}
												className="rounded-lg bg-red-600 px-2 py-1 text-xs text-white hover:bg-red-700"
											>
												Так
											</button>
											<button
												onClick={() => setDeletingId(null)}
												className="rounded-lg px-2 py-1 text-xs text-[#6B7F8C] hover:bg-slate-100 dark:hover:bg-slate-800"
											>
												Ні
											</button>
										</div>
									) : (
										<button
											onClick={() => setDeletingId(e.id)}
											className="inline-flex items-center gap-1 rounded-lg border border-red-200 dark:border-red-900 px-2 py-1.5 text-xs text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20"
										>
											<Trash2 className="h-3.5 w-3.5" />
										</button>
									)}
								</div>
							</div>

							<div className="flex items-center gap-2">
								{growId === e.id ? (
									<>
										<input
											type="number"
											min={1}
											max={500}
											value={growValue}
											onChange={(ev) =>
												setGrowValue(Number(ev.target.value) || 0)
											}
											className={inputCls + " max-w-[100px]"}
										/>
										<button
											onClick={() => handleGrow(e.id)}
											className="inline-flex items-center gap-1 rounded-lg px-3 py-1.5 text-xs bg-[#3D7A8A] text-white hover:bg-[#2E6070]"
										>
											Додати
										</button>
										<button
											onClick={() => {
												setGrowId(null);
												setGrowValue(1);
											}}
											className="rounded-lg px-2 py-1.5 text-xs text-[#6B7F8C] hover:bg-slate-100 dark:hover:bg-slate-800"
										>
											<X className="h-3.5 w-3.5" />
										</button>
									</>
								) : (
									<button
										onClick={() => {
											setGrowId(e.id);
											setGrowValue(1);
										}}
										className="inline-flex items-center gap-1 rounded-lg border border-[#E2E5E8] dark:border-[#2D3D4F] px-2 py-1.5 text-xs text-[#3D7A8A] hover:bg-[#EBF3F5] dark:hover:bg-[#1A2E3A]"
									>
										<Plus className="h-3.5 w-3.5" />
										Додати квартири
									</button>
								)}
							</div>
						</div>
					))}
				</div>

				{/* Add new entrance form */}
				<div className="rounded-xl border border-[#3D7A8A] bg-white dark:bg-[#162032] p-4 space-y-3">
					<h4 className="text-sm font-semibold text-[#1C2B3A] dark:text-white">
						Додати новий підʼїзд
					</h4>
					<div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
						<div className="space-y-1">
							<label className={labelCls}>Назва</label>
							<input
								value={newName}
								onChange={(e) => setNewName(e.target.value)}
								placeholder="2"
								className={inputCls}
								maxLength={20}
							/>
							{newErrors.name && (
								<p className="text-xs text-red-500">{newErrors.name}</p>
							)}
						</div>
						<div className="space-y-1">
							<label className={labelCls}>Кількість квартир</label>
							<input
								type="number"
								min={1}
								max={500}
								value={newCount}
								onChange={(e) => setNewCount(Number(e.target.value) || 0)}
								className={inputCls}
							/>
							{newErrors.count && (
								<p className="text-xs text-red-500">{newErrors.count}</p>
							)}
						</div>
						<div className="flex items-end">
							<button
								onClick={handleCreate}
								disabled={isCreating}
								className="inline-flex items-center gap-2 rounded-xl bg-[#3D7A8A] px-4 py-2 text-sm text-white hover:bg-[#2E6070] dark:bg-[#5BA3B5] dark:hover:bg-[#4A8FA0] disabled:opacity-60"
							>
								<Plus className="h-4 w-4" />
								{isCreating ? "Створення..." : "Створити підʼїзд"}
							</button>
						</div>
					</div>
				</div>
			</DialogContent>
		</Dialog>
	);
}
