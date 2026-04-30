"use client";

import { useState } from "react";
import { ColumnDef } from "@tanstack/react-table";
import { toast } from "react-toastify";
import { Pencil, Plus, X, Check } from "lucide-react";

import { DataTable } from "@/components/admin/DataTable";
import {
	useGetAdminWorkersQuery,
	useAdminCreateUserMutation,
	useAdminUpdateProfileMutation,
} from "@/lib/redux/features/admin/adminApiSlice";
import { Profile, Occupation } from "@/types";
import { extractErrorMessage } from "@/utils";

const occupationLabels: Record<Occupation, string> = {
	mason: "Муляр",
	carpenter: "Тесляр",
	plumber: "Сантехнік",
	roofer: "Покрівельник",
	painter: "Маляр",
	electrician: "Електрик",
	hvac: "Вентиляція/Кліматизація",
	tenant: "Мешканець",
	owner: "Власник",
	guard: "Охоронець",
};

const workerOccupations: Occupation[] = [
	"mason",
	"carpenter",
	"plumber",
	"roofer",
	"painter",
	"electrician",
	"hvac",
	"guard",
];

const inputCls =
	"rounded-xl border border-[#E2E5E8] bg-[#F7F6F2] px-3 py-2 text-sm dark:border-[#2D3D4F] dark:bg-[#1C2B3A] dark:text-white focus:outline-none focus:border-[#3D7A8A] focus:ring-1 focus:ring-[#3D7A8A] w-full";
const labelCls = "text-xs font-medium text-[#6B7F8C]";

interface CreateForm {
	email: string;
	username: string;
	first_name: string;
	last_name: string;
	password: string;
	occupation: Occupation;
}

interface EditForm {
	occupation: Occupation;
}

const emptyCreate: CreateForm = {
	email: "",
	username: "",
	first_name: "",
	last_name: "",
	password: "",
	occupation: "mason",
};

export default function AdminWorkersPage() {
	const { data, isLoading } = useGetAdminWorkersQuery();
	const [adminCreateUser, { isLoading: isCreating }] = useAdminCreateUserMutation();
	const [updateProfile, { isLoading: isUpdating }] = useAdminUpdateProfileMutation();

	const [showCreateForm, setShowCreateForm] = useState(false);
	const [createForm, setCreateForm] = useState<CreateForm>(emptyCreate);
	const [createErrors, setCreateErrors] = useState<Partial<Record<keyof CreateForm, string>>>({});

	const [editingSlug, setEditingSlug] = useState<string | null>(null);
	const [editForm, setEditForm] = useState<EditForm>({ occupation: "mason" });

	const workers = data?.non_tenant_profiles?.results ?? [];

	const validateCreate = (): boolean => {
		const errs: Partial<Record<keyof CreateForm, string>> = {};
		if (!createForm.email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(createForm.email))
			errs.email = "Некоректний email";
		if (!createForm.username || createForm.username.length < 3)
			errs.username = "Мінімум 3 символи";
		if (!createForm.first_name) errs.first_name = "Обов'язкове поле";
		if (!createForm.last_name) errs.last_name = "Обов'язкове поле";
		if (!createForm.password || createForm.password.length < 6)
			errs.password = "Мінімум 6 символів";
		setCreateErrors(errs);
		return Object.keys(errs).length === 0;
	};

	const handleCreate = async (e: React.FormEvent) => {
		e.preventDefault();
		if (!validateCreate()) return;
		try {
			await adminCreateUser(createForm).unwrap();
			toast.success("Працівника створено");
			setCreateForm(emptyCreate);
			setCreateErrors({});
			setShowCreateForm(false);
		} catch (err) {
			toast.error(extractErrorMessage(err) || "Помилка створення");
		}
	};

	const openEdit = (profile: Profile) => {
		setEditingSlug(profile.slug);
		setEditForm({ occupation: profile.occupation });
	};

	const handleEdit = async (slug: string) => {
		try {
			await updateProfile({ slug, occupation: editForm.occupation }).unwrap();
			toast.success("Профіль оновлено");
			setEditingSlug(null);
		} catch (err) {
			toast.error(extractErrorMessage(err) || "Помилка оновлення");
		}
	};

	const columns: ColumnDef<Profile, unknown>[] = [
		{
			accessorKey: "full_name",
			header: "Ім'я",
			cell: ({ row }) => (
				<span className="font-medium text-[#1C2B3A] dark:text-white">
					{row.original.full_name ||
						`${row.original.first_name} ${row.original.last_name}`}
				</span>
			),
		},
		{
			accessorKey: "username",
			header: "Нікнейм",
			cell: ({ row }) => (
				<span className="text-[#6B7F8C]">@{row.original.username}</span>
			),
		},
		{
			accessorKey: "occupation",
			header: "Спеціалізація",
			cell: ({ row }) => {
				const profile = row.original;
				if (editingSlug === profile.slug) {
					return (
						<select
							value={editForm.occupation}
							onChange={(e) =>
								setEditForm({ occupation: e.target.value as Occupation })
							}
							className="rounded-xl border border-[#E2E5E8] bg-[#F7F6F2] px-2 py-1 text-sm dark:border-[#2D3D4F] dark:bg-[#1C2B3A] dark:text-white focus:outline-none focus:border-[#3D7A8A]"
						>
							{workerOccupations.map((occ) => (
								<option key={occ} value={occ}>
									{occupationLabels[occ]}
								</option>
							))}
						</select>
					);
				}
				return (
					<span>
						{occupationLabels[profile.occupation] ?? profile.occupation}
					</span>
				);
			},
		},
		{
			accessorKey: "average_rating",
			header: "Рейтинг",
			cell: ({ row }) => {
				const rating = row.original.average_rating;
				return (
					<div className="flex items-center gap-1.5">
						<span className="text-amber-500">★</span>
						<span className="font-medium">
							{rating ? rating.toFixed(1) : "—"}
						</span>
					</div>
				);
			},
		},
		{
			id: "actions",
			header: "Дії",
			cell: ({ row }) => {
				const profile = row.original;
				if (editingSlug === profile.slug) {
					return (
						<div className="flex items-center gap-2">
							<button
								onClick={() => handleEdit(profile.slug)}
								disabled={isUpdating}
								className="inline-flex items-center gap-1 rounded-lg px-3 py-1.5 text-xs font-medium bg-[#3D7A8A] text-white hover:bg-[#2E6070] dark:bg-[#5BA3B5] dark:hover:bg-[#4A8FA0] disabled:opacity-60 transition-colors"
							>
								<Check className="h-3.5 w-3.5" />
								Зберегти
							</button>
							<button
								onClick={() => setEditingSlug(null)}
								className="inline-flex items-center gap-1 rounded-lg px-3 py-1.5 text-xs font-medium text-[#6B7F8C] hover:bg-red-50 hover:text-red-500 dark:hover:bg-red-900/20 transition-colors"
							>
								<X className="h-3.5 w-3.5" />
							</button>
						</div>
					);
				}
				return (
					<button
						onClick={() => openEdit(profile)}
						className="inline-flex items-center gap-1 rounded-lg border border-[#E2E5E8] dark:border-[#2D3D4F] px-3 py-1.5 text-xs font-medium text-[#3D7A8A] hover:bg-[#EBF3F5] dark:hover:bg-[#1A2E3A] transition-colors"
					>
						<Pencil className="h-3.5 w-3.5" />
						Редагувати
					</button>
				);
			},
		},
	];

	return (
		<div className="space-y-6">
			<div className="flex items-center justify-between">
				<div>
					<h2 className="text-2xl font-bold text-[#1C2B3A] dark:text-white">
						Працівники
					</h2>
					<p className="text-[#6B7F8C] text-sm mt-1">
						Персонал та технічні фахівці
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
							Додати працівника
						</>
					)}
				</button>
			</div>

			{showCreateForm && (
				<div className="rounded-2xl border border-[#3D7A8A] bg-white p-6 dark:border-[#5BA3B5] dark:bg-[#162032]">
					<h3 className="text-base font-semibold text-[#1C2B3A] dark:text-white mb-4">
						Новий працівник
					</h3>
					<form onSubmit={handleCreate} className="space-y-4">
						<div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
							<div className="space-y-1">
								<label className={labelCls}>Email</label>
								<input
									type="email"
									value={createForm.email}
									onChange={(e) =>
										setCreateForm((f) => ({ ...f, email: e.target.value }))
									}
									placeholder="email@example.com"
									className={inputCls}
								/>
								{createErrors.email && (
									<p className="text-xs text-red-500">{createErrors.email}</p>
								)}
							</div>
							<div className="space-y-1">
								<label className={labelCls}>Нікнейм</label>
								<input
									value={createForm.username}
									onChange={(e) =>
										setCreateForm((f) => ({ ...f, username: e.target.value }))
									}
									placeholder="username"
									className={inputCls}
								/>
								{createErrors.username && (
									<p className="text-xs text-red-500">{createErrors.username}</p>
								)}
							</div>
							<div className="space-y-1">
								<label className={labelCls}>Ім&apos;я</label>
								<input
									value={createForm.first_name}
									onChange={(e) =>
										setCreateForm((f) => ({ ...f, first_name: e.target.value }))
									}
									placeholder="Іван"
									className={inputCls}
								/>
								{createErrors.first_name && (
									<p className="text-xs text-red-500">{createErrors.first_name}</p>
								)}
							</div>
							<div className="space-y-1">
								<label className={labelCls}>Прізвище</label>
								<input
									value={createForm.last_name}
									onChange={(e) =>
										setCreateForm((f) => ({ ...f, last_name: e.target.value }))
									}
									placeholder="Петренко"
									className={inputCls}
								/>
								{createErrors.last_name && (
									<p className="text-xs text-red-500">{createErrors.last_name}</p>
								)}
							</div>
							<div className="space-y-1">
								<label className={labelCls}>Пароль</label>
								<input
									type="password"
									value={createForm.password}
									onChange={(e) =>
										setCreateForm((f) => ({ ...f, password: e.target.value }))
									}
									placeholder="Мінімум 6 символів"
									className={inputCls}
								/>
								{createErrors.password && (
									<p className="text-xs text-red-500">{createErrors.password}</p>
								)}
							</div>
							<div className="space-y-1">
								<label className={labelCls}>Спеціалізація</label>
								<select
									value={createForm.occupation}
									onChange={(e) =>
										setCreateForm((f) => ({
											...f,
											occupation: e.target.value as Occupation,
										}))
									}
									className={inputCls}
								>
									{workerOccupations.map((occ) => (
										<option key={occ} value={occ}>
											{occupationLabels[occ]}
										</option>
									))}
								</select>
							</div>
						</div>
						<div className="flex justify-end">
							<button
								type="submit"
								disabled={isCreating}
								className="inline-flex items-center gap-2 rounded-xl bg-[#3D7A8A] px-5 py-2 text-sm font-medium text-white hover:bg-[#2E6070] dark:bg-[#5BA3B5] dark:hover:bg-[#4A8FA0] disabled:opacity-60 transition-colors"
							>
								{isCreating ? "Створення..." : "Створити працівника"}
							</button>
						</div>
					</form>
				</div>
			)}

			<div className="bg-white dark:bg-[#162032] rounded-xl border border-[#E2E5E8] dark:border-[#2D3D4F] p-6 shadow-sm">
				<DataTable
					columns={columns}
					data={workers}
					isLoading={isLoading}
					searchPlaceholder="Пошук працівників..."
				/>
			</div>
		</div>
	);
}
