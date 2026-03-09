"use client";

import {
	ColumnDef,
	flexRender,
	getCoreRowModel,
	getFilteredRowModel,
	getPaginationRowModel,
	getSortedRowModel,
	SortingState,
	useReactTable,
} from "@tanstack/react-table";
import { ChevronUp, ChevronDown, ChevronsUpDown, Search } from "lucide-react";
import { useState } from "react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

interface DataTableProps<TData> {
	columns: ColumnDef<TData, unknown>[];
	data: TData[];
	isLoading?: boolean;
	searchPlaceholder?: string;
}

export function DataTable<TData>({
	columns,
	data,
	isLoading,
	searchPlaceholder = "Пошук...",
}: DataTableProps<TData>) {
	const [sorting, setSorting] = useState<SortingState>([]);
	const [globalFilter, setGlobalFilter] = useState("");

	const table = useReactTable({
		data,
		columns,
		state: { sorting, globalFilter },
		onSortingChange: setSorting,
		onGlobalFilterChange: setGlobalFilter,
		getCoreRowModel: getCoreRowModel(),
		getSortedRowModel: getSortedRowModel(),
		getFilteredRowModel: getFilteredRowModel(),
		getPaginationRowModel: getPaginationRowModel(),
		initialState: { pagination: { pageSize: 10 } },
	});

	return (
		<div className="space-y-4">
			{/* Search */}
			<div className="relative">
				<Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-[#6B7F8C]" />
				<Input
					placeholder={searchPlaceholder}
					value={globalFilter}
					onChange={(e) => setGlobalFilter(e.target.value)}
					className="pl-9 bg-white dark:bg-[#162032] border-[#E2E5E8] dark:border-[#2D3D4F] text-[#1C2B3A] dark:text-white placeholder:text-[#6B7F8C] focus-visible:ring-[#3D7A8A]"
				/>
			</div>

			{/* Table */}
			<div className="overflow-x-auto rounded-lg border border-[#E2E5E8] dark:border-[#2D3D4F]">
				<table className="w-full text-sm">
					<thead>
						{table.getHeaderGroups().map((headerGroup) => (
							<tr key={headerGroup.id}>
								{headerGroup.headers.map((header) => (
									<th
										key={header.id}
										className="px-4 py-3 text-left font-semibold text-xs uppercase tracking-wider text-[#6B7F8C] bg-[#F7F6F2] dark:bg-[#1E2D3D] border-b border-[#E2E5E8] dark:border-[#2D3D4F] whitespace-nowrap"
									>
										{header.isPlaceholder ? null : (
											<div
												className={
													header.column.getCanSort()
														? "flex items-center gap-1 cursor-pointer select-none hover:text-[#3D7A8A] transition-colors"
														: "flex items-center gap-1"
												}
												onClick={header.column.getToggleSortingHandler()}
											>
												{flexRender(
													header.column.columnDef.header,
													header.getContext(),
												)}
												{header.column.getCanSort() && (
													<span className="ml-1">
														{header.column.getIsSorted() === "asc" ? (
															<ChevronUp className="h-3 w-3 text-[#3D7A8A]" />
														) : header.column.getIsSorted() === "desc" ? (
															<ChevronDown className="h-3 w-3 text-[#3D7A8A]" />
														) : (
															<ChevronsUpDown className="h-3 w-3 opacity-40" />
														)}
													</span>
												)}
											</div>
										)}
									</th>
								))}
							</tr>
						))}
					</thead>
					<tbody>
						{isLoading ? (
							Array.from({ length: 10 }).map((_, i) => (
								<tr key={i}>
									{columns.map((_, j) => (
										<td key={j} className="px-4 py-3">
											<div className="h-4 rounded bg-[#E2E5E8] dark:bg-[#2D3D4F] animate-pulse" />
										</td>
									))}
								</tr>
							))
						) : table.getRowModel().rows.length === 0 ? (
							<tr>
								<td
									colSpan={columns.length}
									className="px-4 py-12 text-center text-[#6B7F8C]"
								>
									Дані відсутні
								</td>
							</tr>
						) : (
							table.getRowModel().rows.map((row) => (
								<tr
									key={row.id}
									className="border-b border-[#E2E5E8] dark:border-[#2D3D4F] hover:bg-[#EBF3F5] dark:hover:bg-[#1A2E3A] transition-colors"
								>
									{row.getVisibleCells().map((cell) => (
										<td
											key={cell.id}
											className="px-4 py-3 text-[#1C2B3A] dark:text-[#D1DCE5]"
										>
											{flexRender(
												cell.column.columnDef.cell,
												cell.getContext(),
											)}
										</td>
									))}
								</tr>
							))
						)}
					</tbody>
				</table>
			</div>

			{/* Pagination */}
			<div className="flex items-center justify-between px-1">
				<p className="text-sm text-[#6B7F8C]">
					Сторінка {table.getState().pagination.pageIndex + 1} з{" "}
					{table.getPageCount() || 1}
				</p>
				<div className="flex items-center gap-2">
					<Button
						variant="outline"
						size="sm"
						onClick={() => table.previousPage()}
						disabled={!table.getCanPreviousPage()}
						className="border-[#E2E5E8] dark:border-[#2D3D4F] text-[#1C2B3A] dark:text-[#D1DCE5] hover:bg-[#EBF3F5] dark:hover:bg-[#1A2E3A] disabled:opacity-40"
					>
						Назад
					</Button>
					<Button
						variant="outline"
						size="sm"
						onClick={() => table.nextPage()}
						disabled={!table.getCanNextPage()}
						className="border-[#E2E5E8] dark:border-[#2D3D4F] text-[#1C2B3A] dark:text-[#D1DCE5] hover:bg-[#EBF3F5] dark:hover:bg-[#1A2E3A] disabled:opacity-40"
					>
						Вперед
					</Button>
				</div>
			</div>
		</div>
	);
}
