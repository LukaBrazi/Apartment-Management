"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { ColumnDef } from "@tanstack/react-table";
import { toast } from "react-toastify";
import { Pencil } from "lucide-react";

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
} from "@/lib/redux/features/admin/adminApiSlice";
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
		"guard",
	]),
	bio: z.string().optional(),
});

type EditFormValues = z.infer<typeof editSchema>;

const occupationLabels: Record<Occupation, string> = {
	mason: "Муляр",
	carpenter: "Тесляр",
	plumber: "Сантехнік",
	roofer: "Покрівельник",
	painter: "Маляр",
	electrician: "Електрик",
	hvac: "Вентиляція/Кліматизація",
	tenant: "Мешканець",
	guard: "Охоронець",
};

export default function AdminResidentsPage() {
	const { data, isLoading } = useGetAdminAllProfilesQuery();
	const [updateProfile, { isLoading: isUpdating }] =
		useAdminUpdateProfileMutation();

	const [selectedProfile, setSelectedProfile] = useState<Profile | null>(null);
	const [dialogOpen, setDialogOpen] = useState(false);

	const {
		register,
		handleSubmit,
		setValue,
		reset,
		formState: { errors },
	} = useForm<EditFormValues>({
		resolver: zodResolver(editSchema),
	});

	const openEdit = (profile: Profile) => {
		setSelectedProfile(profile);
		reset({
			first_name: profile.first_name,
			last_name: profile.last_name,
			username: profile.username,
			gender: profile.gender,
			occupation: profile.occupation,
			bio: profile.bio ?? "",
		});
		setDialogOpen(true);
	};

	const onSubmit = async (values: EditFormValues) => {
		if (!selectedProfile) return;
		try {
			await updateProfile({ slug: selectedProfile.slug, ...values }).unwrap();
			toast.success("Профіль оновлено");
			setDialogOpen(false);
		} catch (e) {
			toast.error(extractErrorMessage(e) || "Помилка оновлення");
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
			accessorKey: "apartment",
			header: "Квартира",
			cell: ({ row }) => {
				const apt = row.original.apartment;
				return apt ? (
					<span>
						{apt.unit_number}, {apt.building}
					</span>
				) : (
					<span className="text-[#6B7F8C]">—</span>
				);
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
			<div>
				<h2 className="text-2xl font-bold text-[#1C2B3A] dark:text-white">
					Мешканці
				</h2>
				<p className="text-[#6B7F8C] text-sm mt-1">
					Усі профілі в системі
				</p>
			</div>

			<div className="bg-white dark:bg-[#162032] rounded-xl border border-[#E2E5E8] dark:border-[#2D3D4F] p-6 shadow-sm">
				<DataTable
					columns={columns}
					data={profiles}
					isLoading={isLoading}
					searchPlaceholder="Пошук мешканців..."
				/>
			</div>

			{/* Edit Dialog */}
			<Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
				<DialogContent className="bg-white dark:bg-[#162032] border-[#E2E5E8] dark:border-[#2D3D4F] max-w-md">
					<DialogHeader>
						<DialogTitle className="text-[#1C2B3A] dark:text-white">
							Редагувати профіль
						</DialogTitle>
					</DialogHeader>

					<form onSubmit={handleSubmit(onSubmit)} className="space-y-4 mt-2">
						<div className="grid grid-cols-2 gap-3">
							<div className="space-y-1">
								<label className="text-xs font-medium text-[#6B7F8C]">
									Ім&apos;я
								</label>
								<Input
									{...register("first_name")}
									className="border-[#E2E5E8] dark:border-[#2D3D4F] bg-[#F7F6F2] dark:bg-[#1C2B3A]"
								/>
								{errors.first_name && (
									<p className="text-xs text-red-500">
										{errors.first_name.message}
									</p>
								)}
							</div>
							<div className="space-y-1">
								<label className="text-xs font-medium text-[#6B7F8C]">
									Прізвище
								</label>
								<Input
									{...register("last_name")}
									className="border-[#E2E5E8] dark:border-[#2D3D4F] bg-[#F7F6F2] dark:bg-[#1C2B3A]"
								/>
								{errors.last_name && (
									<p className="text-xs text-red-500">
										{errors.last_name.message}
									</p>
								)}
							</div>
						</div>

						<div className="space-y-1">
							<label className="text-xs font-medium text-[#6B7F8C]">
								Нікнейм
							</label>
							<Input
								{...register("username")}
								className="border-[#E2E5E8] dark:border-[#2D3D4F] bg-[#F7F6F2] dark:bg-[#1C2B3A]"
							/>
							{errors.username && (
								<p className="text-xs text-red-500">{errors.username.message}</p>
							)}
						</div>

						<div className="space-y-1">
							<label className="text-xs font-medium text-[#6B7F8C]">
								Стать
							</label>
							<Select
								defaultValue={selectedProfile?.gender}
								onValueChange={(val) =>
									setValue("gender", val as "male" | "female" | "other")
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
								onValueChange={(val) => setValue("occupation", val as Occupation)}
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

						<div className="space-y-1">
							<label className="text-xs font-medium text-[#6B7F8C]">
								Про себе
							</label>
							<Textarea
								{...register("bio")}
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
