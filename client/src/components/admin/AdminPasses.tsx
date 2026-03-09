"use client";

import { ColumnDef } from "@tanstack/react-table";
import { DataTable } from "./DataTable";
import StatusBadge from "./StatusBadge";
import { VehiclePass } from "@/types";
import {
	useGetAdminPassesQuery,
	useClosePassMutation,
} from "@/lib/redux/features/admin/adminApiSlice";
import { toast } from "react-toastify";
import { Button } from "@/components/ui/button";
import { Lock } from "lucide-react";

export default function AdminPasses() {
	const { data, isLoading } = useGetAdminPassesQuery();
	const [closePass] = useClosePassMutation();

	const passes = data?.results ?? [];

	const handleClose = async (passId: string) => {
		try {
			await closePass(passId).unwrap();
			toast.success("Пропуск закрито");
		} catch {
			toast.error("Помилка закриття пропуску");
		}
	};

	const columns: ColumnDef<VehiclePass>[] = [
		{
			accessorKey: "tenant_name",
			header: "Мешканець",
			cell: ({ row }) => (
				<div>
					<p className="font-medium text-[#1C2B3A] dark:text-white">
						{row.original.tenant_name}
					</p>
					<p className="text-xs text-[#6B7F8C]">
						{row.original.building_name} / {row.original.unit_label ?? "—"}
					</p>
				</div>
			),
		},
		{
			accessorKey: "car_number",
			header: "Авто",
			cell: ({ getValue }) => {
				const val = getValue<string>();
				return val ? (
					<span className="font-mono text-sm font-medium tracking-wider uppercase text-[#1C2B3A] dark:text-white">
						{val}
					</span>
				) : (
					<span className="text-xs text-[#6B7F8C]">—</span>
				);
			},
		},
		{
			accessorKey: "comment",
			header: "Коментар",
			cell: ({ getValue }) => (
				<span className="max-w-[180px] truncate text-sm text-[#6B7F8C]">
					{getValue<string>() || "—"}
				</span>
			),
		},
		{
			accessorKey: "visit_date",
			header: "Дата візиту",
			cell: ({ getValue }) =>
				new Date(getValue<string>()).toLocaleDateString("uk-UA"),
		},
		{
			accessorKey: "status",
			header: "Статус",
			cell: ({ getValue }) => (
				<StatusBadge value={getValue<string>()} type="status" />
			),
		},
		{
			accessorKey: "closed_by_username",
			header: "Закрив",
			cell: ({ row }) => {
				if (row.original.status === "closed" && row.original.closed_by_username) {
					return (
						<div>
							<p className="text-sm text-[#6B7F8C]">
								@{row.original.closed_by_username}
							</p>
							{row.original.closed_at && (
								<p className="text-xs text-[#6B7F8C]">
									{new Date(row.original.closed_at).toLocaleDateString("uk-UA")}
								</p>
							)}
						</div>
					);
				}
				return <span className="text-xs text-[#6B7F8C]">—</span>;
			},
		},
		{
			id: "actions",
			header: "",
			enableSorting: false,
			cell: ({ row }) => {
				if (row.original.status === "pending") {
					return (
						<Button
							size="sm"
							variant="outline"
							onClick={() => handleClose(row.original.id)}
							className="h-7 gap-1 border-[#E2E5E8] px-2 text-xs text-[#1C2B3A] hover:border-[#3D7A8A] hover:text-[#3D7A8A] dark:border-[#2D3D4F] dark:text-[#D1DCE5] dark:hover:border-[#5BA3B5] dark:hover:text-[#5BA3B5]"
						>
							<Lock className="h-3 w-3" />
							Закрити
						</Button>
					);
				}
				return null;
			},
		},
	];

	return (
		<div className="rounded-2xl border border-[#E2E5E8] bg-white p-6 dark:border-[#2D3D4F] dark:bg-[#162032]">
			<div className="mb-6">
				<h2 className="text-lg font-semibold text-[#1C2B3A] dark:text-white">
					Пропуски для авто
					<span className="ml-2 rounded-full bg-[#EBF3F5] px-2.5 py-0.5 text-xs font-medium text-[#3D7A8A] dark:bg-[#1A2E3A] dark:text-[#5BA3B5]">
						{passes.length}
					</span>
				</h2>
			</div>
			<DataTable
				columns={columns}
				data={passes}
				isLoading={isLoading}
				searchPlaceholder="Пошук пропусків..."
			/>
		</div>
	);
}
