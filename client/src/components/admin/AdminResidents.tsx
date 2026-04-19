"use client";

import { useState } from "react";
import { ColumnDef } from "@tanstack/react-table";
import { DataTable } from "./DataTable";
import { Profile } from "@/types";
import {
	useGetAdminAllProfilesQuery,
	useAdminUpdateProfileMutation,
} from "@/lib/redux/features/admin/adminApiSlice";
import { occupationOptions } from "@/constants";
import { toast } from "react-toastify";
import { Pencil, X, Check } from "lucide-react";
import { Button } from "@/components/ui/button";
import Image from "next/image";

export default function AdminResidents() {
	const { data, isLoading } = useGetAdminAllProfilesQuery();
	const [updateProfile] = useAdminUpdateProfileMutation();
	const [editingSlug, setEditingSlug] = useState<string | null>(null);
	const [editOccupation, setEditOccupation] = useState("");

	const residents = (data?.profiles?.results ?? []).filter(
		(p) => p.occupation === "tenant",
	);

	const handleSave = async (slug: string) => {
		try {
			await updateProfile({ slug, occupation: editOccupation as Profile["occupation"] }).unwrap();
			toast.success("Профіль оновлено");
			setEditingSlug(null);
		} catch {
			toast.error("Помилка оновлення профілю");
		}
	};

	const columns: ColumnDef<Profile>[] = [
		{
			accessorKey: "avatar",
			header: "",
			enableSorting: false,
			cell: ({ row }) => (
				<div className="flex h-8 w-8 items-center justify-center overflow-hidden rounded-full bg-[#EBF3F5] dark:bg-[#1A2E3A]">
					{row.original.avatar ? (
						<Image
							src={row.original.avatar}
							alt={row.original.full_name}
							width={32}
							height={32}
							className="h-full w-full object-cover"
						/>
					) : (
						<span className="text-xs font-semibold text-[#3D7A8A]">
							{row.original.first_name?.[0]?.toUpperCase() ?? "?"}
						</span>
					)}
				</div>
			),
		},
		{
			accessorKey: "full_name",
			header: "Ім'я",
		},
		{
			accessorKey: "username",
			header: "Логін",
			cell: ({ getValue }) => (
				<span className="font-mono text-xs text-[#6B7F8C]">@{getValue<string>()}</span>
			),
		},
		{
			// PR-4: unit/building come straight off the Profile payload.
			accessorKey: "unit_number",
			header: "Квартира",
			cell: ({ row }) =>
				row.original.unit_number ? (
					<span className="text-sm">
						{row.original.building_name ?? "—"} / кв. {row.original.unit_number}
					</span>
				) : (
					<span className="text-xs text-[#6B7F8C]">—</span>
				),
		},
		{
			accessorKey: "occupation",
			header: "Роль",
			cell: ({ row }) => {
				const isEditing = editingSlug === row.original.slug;
				const label =
					occupationOptions.find((o) => o.value === row.original.occupation)?.label ??
					row.original.occupation;

				if (isEditing) {
					return (
						<div className="flex items-center gap-2">
							<select
								value={editOccupation}
								onChange={(e) => setEditOccupation(e.target.value)}
								className="rounded-lg border border-[#E2E5E8] bg-white px-2 py-1 text-sm text-[#1C2B3A] dark:border-[#2D3D4F] dark:bg-[#162032] dark:text-white"
							>
								{occupationOptions.map((o) => (
									<option key={o.value} value={o.value}>
										{o.label}
									</option>
								))}
							</select>
							<button
								onClick={() => handleSave(row.original.slug)}
								className="rounded p-1 text-green-600 hover:bg-green-50 dark:hover:bg-green-900/20"
							>
								<Check className="h-4 w-4" />
							</button>
							<button
								onClick={() => setEditingSlug(null)}
								className="rounded p-1 text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20"
							>
								<X className="h-4 w-4" />
							</button>
						</div>
					);
				}

				return (
					<div className="flex items-center gap-2">
						<span className="text-sm">{label}</span>
						<button
							onClick={() => {
								setEditingSlug(row.original.slug);
								setEditOccupation(row.original.occupation);
							}}
							className="rounded p-1 text-[#6B7F8C] opacity-0 hover:bg-[#EBF3F5] hover:text-[#3D7A8A] group-hover:opacity-100 dark:hover:bg-[#1A2E3A] dark:hover:text-[#5BA3B5]"
						>
							<Pencil className="h-3 w-3" />
						</button>
					</div>
				);
			},
		},
		{
			accessorKey: "date_joined",
			header: "Дата реєстрації",
			cell: ({ getValue }) =>
				new Date(getValue<string>()).toLocaleDateString("uk-UA"),
		},
	];

	return (
		<div className="rounded-2xl border border-[#E2E5E8] bg-white p-6 dark:border-[#2D3D4F] dark:bg-[#162032]">
			<div className="mb-6 flex items-center justify-between">
				<h2 className="text-lg font-semibold text-[#1C2B3A] dark:text-white">
					Мешканці
					<span className="ml-2 rounded-full bg-[#EBF3F5] px-2.5 py-0.5 text-xs font-medium text-[#3D7A8A] dark:bg-[#1A2E3A] dark:text-[#5BA3B5]">
						{residents.length}
					</span>
				</h2>
			</div>
			<DataTable
				columns={columns}
				data={residents}
				isLoading={isLoading}
				searchPlaceholder="Пошук мешканців..."
			/>
		</div>
	);
}
