"use client";

import { ColumnDef } from "@tanstack/react-table";
import { toast } from "react-toastify";
import { format } from "date-fns";
import { XCircle } from "lucide-react";

import { DataTable } from "@/components/admin/DataTable";
import StatusBadge from "@/components/admin/StatusBadge";
import { Button } from "@/components/ui/button";
import {
	useGetAdminPassesQuery,
	useClosePassMutation,
} from "@/lib/redux/features/admin/adminApiSlice";
import { VehiclePass } from "@/types";
import { extractErrorMessage } from "@/utils";

export default function AdminPassesPage() {
	const { data, isLoading } = useGetAdminPassesQuery();
	const [closePass, { isLoading: isClosing }] = useClosePassMutation();

	const handleClose = async (passId: string) => {
		try {
			await closePass(passId).unwrap();
			toast.success("Перепустку закрито");
		} catch (e) {
			toast.error(extractErrorMessage(e) || "Помилка закриття");
		}
	};

	const passes = data?.results ?? [];

	const columns: ColumnDef<VehiclePass, unknown>[] = [
		{
			accessorKey: "tenant_name",
			header: "Мешканець",
			cell: ({ row }) => (
				<div>
					<p className="font-medium text-[#1C2B3A] dark:text-white">
						{row.original.tenant_name}
					</p>
					<p className="text-xs text-[#6B7F8C]">
						@{row.original.tenant_username}
					</p>
				</div>
			),
		},
		{
			accessorKey: "unit_label",
			header: "Квартира",
			cell: ({ row }) => (
				<div>
					<p>{row.original.unit_label ?? "—"}</p>
					{row.original.building_name && (
						<p className="text-xs text-[#6B7F8C]">{row.original.building_name}</p>
					)}
				</div>
			),
		},
		{
			accessorKey: "car_number",
			header: "Номер авто",
			cell: ({ row }) =>
				row.original.car_number ? (
					<span className="font-mono text-sm bg-[#F7F6F2] dark:bg-[#1E2D3D] px-2 py-0.5 rounded border border-[#E2E5E8] dark:border-[#2D3D4F]">
						{row.original.car_number}
					</span>
				) : (
					<span className="text-[#6B7F8C]">—</span>
				),
		},
		{
			accessorKey: "visit_date",
			header: "Дата відвідування",
			cell: ({ row }) => {
				try {
					return format(new Date(row.original.visit_date), "dd.MM.yyyy");
				} catch {
					return row.original.visit_date;
				}
			},
		},
		{
			accessorKey: "status",
			header: "Статус",
			cell: ({ row }) => <StatusBadge value={row.original.status} />,
		},
		{
			id: "actions",
			header: "Дії",
			cell: ({ row }) => {
				if (row.original.status !== "pending") return null;
				return (
					<Button
						variant="outline"
						size="sm"
						onClick={() => handleClose(row.original.id)}
						disabled={isClosing}
						className="border-red-200 dark:border-red-900 text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20"
					>
						<XCircle className="h-3.5 w-3.5 mr-1" />
						Закрити
					</Button>
				);
			},
		},
	];

	return (
		<div className="space-y-6">
			<div>
				<h2 className="text-2xl font-bold text-[#1C2B3A] dark:text-white">
					Перепустки
				</h2>
				<p className="text-[#6B7F8C] text-sm mt-1">
					Усі запити на перепустки транспортних засобів
				</p>
			</div>

			<div className="bg-white dark:bg-[#162032] rounded-xl border border-[#E2E5E8] dark:border-[#2D3D4F] p-6 shadow-sm">
				<DataTable
					columns={columns}
					data={passes}
					isLoading={isLoading}
					searchPlaceholder="Пошук перепусток..."
				/>
			</div>
		</div>
	);
}
