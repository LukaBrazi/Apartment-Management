"use client";

import { ColumnDef } from "@tanstack/react-table";
import { DataTable } from "@/components/admin/DataTable";
import { useGetAdminWorkersQuery } from "@/lib/redux/features/admin/adminApiSlice";
import { Profile, Occupation } from "@/types";

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
		cell: ({ row }) => (
			<span>
				{occupationLabels[row.original.occupation] ?? row.original.occupation}
			</span>
		),
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
];

export default function AdminWorkersPage() {
	const { data, isLoading } = useGetAdminWorkersQuery();

	const workers = data?.non_tenant_profiles?.results ?? [];

	return (
		<div className="space-y-6">
			<div>
				<h2 className="text-2xl font-bold text-[#1C2B3A] dark:text-white">
					Працівники
				</h2>
				<p className="text-[#6B7F8C] text-sm mt-1">
					Персонал та технічні фахівці
				</p>
			</div>

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
