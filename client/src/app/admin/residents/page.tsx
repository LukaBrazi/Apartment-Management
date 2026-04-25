"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { ColumnDef } from "@tanstack/react-table";
import { toast } from "react-toastify";
import { Pencil, Plus, X } from "lucide-react";

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
	useGetAdminAllProfilesQuery,
	useAdminUpdateProfileMutation,
	useAdminCreateUserMutation,
	useAdminGetBuildingsQuery,
} from "@/lib/redux/features/admin/adminApiSlice";
import { useGetUnitsByBuildingQuery } from "@/lib/redux/features/apartment/apartmentApiSlice";
import { Profile, Occupation } from "@/types";
import { extractErrorMessage } from "@/utils";

const editSchema = z.object({
	first_name: z.string().min(1, "Обов'язкове поле"),
	last_name: z.string().min(1, "Обов'язкове поле"),
	username: z.string().min(3, "Мінімум 3 символи"),
	gender: z.enum(["male", "female", "other"]),
	occupation: z.enum([
		"mason",
		"carpenter",
		"plumber",
		"roofer",
		"painter",
		"electrician",
		"hvac",
		"tenant",
		"owner",
		"guard",
	]),
	bio: z.string().optional(),
	unit_id: z.string().optional().nullable(),
});

const createSchema = z.object({
	email: z.string().email("Некоректний email"),
	username: z.string().min(3, "Мінімум 3 символи"),
	first_name: z.string().min(1, "Обов'язкове поле"),
	last_name: z.string().min(1, "Обов'язкове поле"),
	password: z.string().min(6, "Мінімум 6 символів"),
	unit_id: z.string().optional().nullable(),
});

type EditFormValues = z.infer<typeof editSchema>;
type CreateFormValues = z.infer<typeof createSchema>;

const occupationLabels: Record<Occupation, string> = {
	mason: "Муляр",
	carpenter: "Тесляр",
	plumber: "Сантехнік",
	roofer: "Покрівельник",
	painter: "Маляр",
	electrician: "Електрик",
	hvac: "Вентиляція/Кліматизація",
	tenant: "Орендар",
	owner: "Власник",
	guard: "Охоронець",
};

const inputCls =
	"rounded-xl border border-[#E2E5E8] bg-[#F7F6F2] px-3 py-2 text-sm dark:border-[#2D3D4F] dark:bg-[#1C2B3A] dark:text-white focus:outline-none focus:border-[#3D7A8A] focus:ring-1 focus:ring-[#3D7A8A] w-full";
const labelCls = "text-xs font-medium text-[#6B7F8C]";

export default function AdminResidentsPage() {
	const { data, isLoading } = useGetAdminAllProfilesQuery();
	const [updateProfile, { isLoading: isUpdating }] = useAdminUpdateProfileMutation();
	const [adminCreateUser, { isLoading: isCreating }] = useAdminCreateUserMutation();
	const { data: buildingsData } = useAdminGetBuildingsQuery();

	const [selectedProfile, setSelectedProfile] = useState<Profile | null>(null);
	const [dialogOpen, setDialogOpen] = useState(false);
	const [showCreateForm, setShowCreateForm] = useState(false);

	// Building & unit selection state for create and edit forms
	const [createBuildingId, setCreateBuildingId] = useState<string>("");
	const [editBuildingId, setEditBuildingId] = useState<string>("");
	const [editUnitId, setEditUnitId] = useState<string>("");

	const { data: createUnitsData } = useGetUnitsByBuildingQuery(createBuildingId, {
		skip: !createBuildingId,
	});
	const { data: editUnitsData } = useGetUnitsByBuildingQuery(editBuildingId, {
		skip: !editBuildingId,
	});

	const buildings = buildingsData?.buildings ?? [];
	const createUnits = createUnitsData?.units ?? [];
	const editUnits = editUnitsData?.units ?? [];

	const {
		register: registerEdit,
		handleSubmit: handleSubmitEdit,
		setValue: setValueEdit,
		reset: resetEdit,
		formState: { errors: errorsEdit },
	} = useForm<EditFormValues>({
		resolver: zodResolver(editSchema),
	});

	const {
		register: registerCreate,
		handleSubmit: handleSubmitCreate,
		reset: resetCreate,
		setValue: setValueCreate,
		formState: { errors: errorsCreate },
	} = useForm<CreateFormValues>({
		resolver: zodResolver(createSchema),
	});

	const openEdit = (profile: Profile) => {
		setSelectedProfile(profile);
		setEditBuildingId(profile.building_id ?? "");
		setEditUnitId(profile.unit_id ?? "");
		resetEdit({
			first_name: profile.first_name,
			last_name: profile.last_name,
			username: profile.username,
			gender: profile.gender,
			occupation: profile.occupation,
			bio: profile.bio ?? "",
			unit_id: profile.unit_id ?? null,
		});
		setDialogOpen(true);
	};

	const onSubmitEdit = async (values: EditFormValues) => {
		if (!selectedProfile) return;
		try {
			await updateProfile({
				slug: selectedProfile.slug,
				...values,
				unit_id: values.unit_id || null,
			}).unwrap();
			toast.success("Профіль оновлено");
			setDialogOpen(false);
		} catch (e) {
			toast.error(extractErrorMessage(e) || "Помилка оновлення");
		}
	};

	const onSubmitCreate = async (values: CreateFormValues) => {
		try {
			await adminCreateUser({
				...values,
				occupation: "tenant",
				unit_id: values.unit_id || null,
			}).unwrap();
			toast.success("Мешканця створено");
			resetCreate();
			setCreateBuildingId("");
			setShowCreateForm(false);
		} catch (e) {
			toast.error(extractErrorMessage(e) || "Помилка створення");
		}
	};

	const profiles = data?.profiles?.results ?? [];

	const columns: ColumnDef<Profile, unknown>[] = [
		{
			accessorKey: "full_name",
			header: "Ім'я",
			cell: ({ row }) => (
				<span className="font-medium text-[#1C2B3A] dark:text-white">
					{row.original.full_name || `${row.original.first_name} ${row.original.last_name}`}
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
			header: "Роль",
			cell: ({ row }) => (
				<span>{occupationLabels[row.original.occupation] ?? row.original.occupation}</span>
			),
		},
		{
			accessorKey: "unit_number",
			header: "Квартира",
			cell: ({ row }) => {
				const p = row.original;
				if (p.unit_number && p.building_name) {
					return (
						<span>
							Кв. {p.unit_number}, {p.building_name}
						</span>
					);
				}
				return <span className="text-[#6B7F8C]">—</span>;
			},
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
			<div className="flex items-center justify-between">
				<div>
					<h2 className="text-2xl font-bold text-[#1C2B3A] dark:text-white">
						Мешканці
					</h2>
					<p className="text-[#6B7F8C] text-sm mt-1">
						Усі профілі в системі
					</p>
				</div>
				<button
					onClick={() => {
						resetCreate();
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
							Додати мешканця
						</>
					)}
				</button>
			</div>

			{showCreateForm && (
				<div className="rounded-2xl border border-[#3D7A8A] bg-white p-6 dark:border-[#5BA3B5] dark:bg-[#162032]">
					<h3 className="text-base font-semibold text-[#1C2B3A] dark:text-white mb-4">
						Новий мешканець
					</h3>
					<form onSubmit={handleSubmitCreate(onSubmitCreate)} className="space-y-4">
						<div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
							<div className="space-y-1">
								<label className={labelCls}>Email</label>
								<input
									{...registerCreate("email")}
									type="email"
									placeholder="email@example.com"
									className={inputCls}
								/>
								{errorsCreate.email && (
									<p className="text-xs text-red-500">{errorsCreate.email.message}</p>
								)}
							</div>
							<div className="space-y-1">
								<label className={labelCls}>Нікнейм</label>
								<input
									{...registerCreate("username")}
									placeholder="username"
									className={inputCls}
								/>
								{errorsCreate.username && (
									<p className="text-xs text-red-500">{errorsCreate.username.message}</p>
								)}
							</div>
							<div className="space-y-1">
								<label className={labelCls}>Ім&apos;я</label>
								<input
									{...registerCreate("first_name")}
									placeholder="Іван"
									className={inputCls}
								/>
								{errorsCreate.first_name && (
									<p className="text-xs text-red-500">{errorsCreate.first_name.message}</p>
								)}
							</div>
							<div className="space-y-1">
								<label className={labelCls}>Прізвище</label>
								<input
									{...registerCreate("last_name")}
									placeholder="Петренко"
									className={inputCls}
								/>
								{errorsCreate.last_name && (
									<p className="text-xs text-red-500">{errorsCreate.last_name.message}</p>
								)}
							</div>
							<div className="space-y-1">
								<label className={labelCls}>Пароль</label>
								<input
									{...registerCreate("password")}
									type="password"
									placeholder="Мінімум 6 символів"
									className={inputCls}
								/>
								{errorsCreate.password && (
									<p className="text-xs text-red-500">{errorsCreate.password.message}</p>
								)}
							</div>
							<div className="space-y-1">
								<label className={labelCls}>Роль</label>
								<input
									value="Мешканець"
									disabled
									className={`${inputCls} opacity-60 cursor-not-allowed`}
								/>
							</div>
							<div className="space-y-1">
								<label className={labelCls}>Будинок</label>
								<Select
									value={createBuildingId}
									onValueChange={(val) => {
										setCreateBuildingId(val);
										setValueCreate("unit_id", null);
									}}
								>
									<SelectTrigger className={inputCls}>
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
							</div>
							<div className="space-y-1">
								<label className={labelCls}>Квартира</label>
								<Select
									onValueChange={(val) => setValueCreate("unit_id", val)}
									disabled={!createBuildingId || createUnits.length === 0}
								>
									<SelectTrigger className={inputCls}>
										<SelectValue placeholder={!createBuildingId ? "Спершу оберіть будинок" : createUnits.length === 0 ? "Немає квартир" : "Оберіть квартиру"} />
									</SelectTrigger>
									<SelectContent>
										{createUnits.map((u) => (
											<SelectItem key={u.id} value={u.id}>
												Кв. {u.number} (під&apos;їзд {u.entrance_name}{u.floor ? `, пов. ${u.floor}` : ""})
											</SelectItem>
										))}
									</SelectContent>
								</Select>
							</div>
						</div>
						<div className="flex justify-end">
							<button
								type="submit"
								disabled={isCreating}
								className="inline-flex items-center gap-2 rounded-xl bg-[#3D7A8A] px-5 py-2 text-sm font-medium text-white hover:bg-[#2E6070] dark:bg-[#5BA3B5] dark:hover:bg-[#4A8FA0] disabled:opacity-60 transition-colors"
							>
								{isCreating ? "Створення..." : "Створити мешканця"}
							</button>
						</div>
					</form>
				</div>
			)}

			<div className="bg-white dark:bg-[#162032] rounded-xl border border-[#E2E5E8] dark:border-[#2D3D4F] p-6 shadow-sm">
				<DataTable
					columns={columns}
					data={profiles}
					isLoading={isLoading}
					searchPlaceholder="Пошук мешканців..."
				/>
			</div>

			<Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
				<DialogContent className="bg-white dark:bg-[#162032] border-[#E2E5E8] dark:border-[#2D3D4F] max-w-md">
					<DialogHeader>
						<DialogTitle className="text-[#1C2B3A] dark:text-white">
							Редагувати профіль
						</DialogTitle>
					</DialogHeader>

					<form onSubmit={handleSubmitEdit(onSubmitEdit)} className="space-y-4 mt-2">
						<div className="grid grid-cols-2 gap-3">
							<div className="space-y-1">
								<label className="text-xs font-medium text-[#6B7F8C]">
									Ім&apos;я
								</label>
								<Input
									{...registerEdit("first_name")}
									className="border-[#E2E5E8] dark:border-[#2D3D4F] bg-[#F7F6F2] dark:bg-[#1C2B3A]"
								/>
								{errorsEdit.first_name && (
									<p className="text-xs text-red-500">
										{errorsEdit.first_name.message}
									</p>
								)}
							</div>
							<div className="space-y-1">
								<label className="text-xs font-medium text-[#6B7F8C]">
									Прізвище
								</label>
								<Input
									{...registerEdit("last_name")}
									className="border-[#E2E5E8] dark:border-[#2D3D4F] bg-[#F7F6F2] dark:bg-[#1C2B3A]"
								/>
								{errorsEdit.last_name && (
									<p className="text-xs text-red-500">
										{errorsEdit.last_name.message}
									</p>
								)}
							</div>
						</div>

						<div className="space-y-1">
							<label className="text-xs font-medium text-[#6B7F8C]">
								Нікнейм
							</label>
							<Input
								{...registerEdit("username")}
								className="border-[#E2E5E8] dark:border-[#2D3D4F] bg-[#F7F6F2] dark:bg-[#1C2B3A]"
							/>
							{errorsEdit.username && (
								<p className="text-xs text-red-500">{errorsEdit.username.message}</p>
							)}
						</div>

						<div className="space-y-1">
							<label className="text-xs font-medium text-[#6B7F8C]">
								Стать
							</label>
							<Select
								defaultValue={selectedProfile?.gender}
								onValueChange={(val) =>
									setValueEdit("gender", val as "male" | "female" | "other")
								}
							>
								<SelectTrigger className="border-[#E2E5E8] dark:border-[#2D3D4F] bg-[#F7F6F2] dark:bg-[#1C2B3A]">
									<SelectValue placeholder="Оберіть стать" />
								</SelectTrigger>
								<SelectContent>
									<SelectItem value="male">Чоловік</SelectItem>
									<SelectItem value="female">Жінка</SelectItem>
									<SelectItem value="other">Інше</SelectItem>
								</SelectContent>
							</Select>
						</div>

						<div className="space-y-1">
							<label className="text-xs font-medium text-[#6B7F8C]">
								Роль
							</label>
							<Select
								defaultValue={selectedProfile?.occupation}
								onValueChange={(val) => setValueEdit("occupation", val as Occupation)}
							>
								<SelectTrigger className="border-[#E2E5E8] dark:border-[#2D3D4F] bg-[#F7F6F2] dark:bg-[#1C2B3A]">
									<SelectValue placeholder="Оберіть роль" />
								</SelectTrigger>
								<SelectContent>
									{Object.entries(occupationLabels).map(([val, label]) => (
										<SelectItem key={val} value={val}>
											{label}
										</SelectItem>
									))}
								</SelectContent>
							</Select>
						</div>

						<div className="grid grid-cols-2 gap-3">
							<div className="space-y-1">
								<label className="text-xs font-medium text-[#6B7F8C]">
									Будинок
								</label>
								<Select
									value={editBuildingId || undefined}
									onValueChange={(val) => {
										setEditBuildingId(val);
										setEditUnitId("");
										setValueEdit("unit_id", null);
									}}
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
							</div>
							<div className="space-y-1">
								<label className="text-xs font-medium text-[#6B7F8C]">
									Квартира
								</label>
								<Select
									value={editUnitId || undefined}
									onValueChange={(val) => {
										setEditUnitId(val);
										setValueEdit("unit_id", val);
									}}
									disabled={!editBuildingId || editUnits.length === 0}
								>
									<SelectTrigger className="border-[#E2E5E8] dark:border-[#2D3D4F] bg-[#F7F6F2] dark:bg-[#1C2B3A]">
										<SelectValue placeholder={!editBuildingId ? "Спершу оберіть будинок" : editUnits.length === 0 ? "Немає квартир" : "Оберіть квартиру"} />
									</SelectTrigger>
									<SelectContent>
										{editUnits.map((u) => (
											<SelectItem key={u.id} value={u.id}>
												Кв. {u.number} (під&apos;їзд {u.entrance_name}{u.floor ? `, пов. ${u.floor}` : ""})
											</SelectItem>
										))}
									</SelectContent>
								</Select>
							</div>
						</div>

						<div className="space-y-1">
							<label className="text-xs font-medium text-[#6B7F8C]">
								Про себе
							</label>
							<Textarea
								{...registerEdit("bio")}
								rows={3}
								className="border-[#E2E5E8] dark:border-[#2D3D4F] bg-[#F7F6F2] dark:bg-[#1C2B3A] resize-none"
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
