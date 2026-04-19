"use client";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import Spinner from "@/components/shared/Spinner";
import { useClosePassMutation } from "@/lib/redux/features/passes/passApiSlice";
import { VehiclePass } from "@/types";
import { CarIcon, CheckCircleIcon, ClockIcon, UserIcon } from "lucide-react";
import { toast } from "react-toastify";

interface Props {
	pass: VehiclePass;
}

export default function VehiclePassCard({ pass }: Props) {
	const [closePass, { isLoading }] = useClosePassMutation();

	const handleClose = async () => {
		try {
			await closePass(pass.id).unwrap();
			toast.success("Перепустку позначено як закриту.");
		} catch {
			toast.error("Не вдалося закрити перепустку.");
		}
	};

	const isClosed = pass.status === "closed";

	return (
		// Mobile-first card: single-column metadata on phones (grid-cols-1),
		// two-column at sm+ (the pre-existing desktop layout). Tokens
		// migrated to the unified SaaS palette (`saas.card` surface,
		// `saas.border`) while keeping the Pumpkin brand color for the
		// primary CTA that guards tap dozens of times per shift.
		<div className="flex flex-col gap-3 rounded-xl border border-[#E5E7EB] bg-white p-4 shadow-sm dark:border-[#2D3D4F] dark:bg-[#162032]">
			<div className="flex flex-wrap items-center justify-between gap-2">
				<div className="flex min-w-0 items-center gap-2">
					<UserIcon className="size-4 flex-shrink-0 text-gray-500 dark:text-gray-400" />
					<span className="truncate font-semibold dark:text-babyPowder">
						{pass.tenant_name}
					</span>
					<span className="hidden truncate text-sm text-gray-500 sm:inline dark:text-gray-400">
						@{pass.tenant_username}
					</span>
				</div>
				<Badge
					className={
						isClosed
							? "flex-shrink-0 bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200"
							: "flex-shrink-0 bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200"
					}
				>
					{isClosed ? "Закрита" : "Очікує"}
				</Badge>
			</div>

			<div className="grid grid-cols-1 gap-2 text-sm sm:grid-cols-2">
				{pass.building_name && (
					<div className="min-w-0 truncate">
						<span className="text-gray-500 dark:text-gray-400">Будинок: </span>
						<span className="dark:text-babyPowder">{pass.building_name}</span>
					</div>
				)}
				{pass.unit_label && (
					<div className="min-w-0 truncate">
						<span className="text-gray-500 dark:text-gray-400">Квартира: </span>
						<span className="dark:text-babyPowder">{pass.unit_label}</span>
					</div>
				)}
				<div className="flex min-w-0 items-center gap-1">
					<CarIcon className="size-4 flex-shrink-0 text-gray-500 dark:text-gray-400" />
					<span className="truncate dark:text-babyPowder">
						{pass.car_number || <em className="text-gray-400">Без номера</em>}
					</span>
				</div>
				<div className="flex min-w-0 items-center gap-1">
					<ClockIcon className="size-4 flex-shrink-0 text-gray-500 dark:text-gray-400" />
					<span className="truncate text-gray-500 dark:text-gray-400">
						Подано: {new Date(pass.created_at).toLocaleTimeString()}
					</span>
				</div>
			</div>

			{pass.comment && (
				<p className="border-l-2 border-pumpkin pl-2 text-sm italic text-gray-600 dark:text-gray-300">
					{pass.comment}
				</p>
			)}

			{isClosed && pass.closed_by_username && (
				<p className="flex items-center gap-1 text-xs text-gray-500 dark:text-gray-400">
					<CheckCircleIcon className="size-3 text-green-500" />
					Закрито @{pass.closed_by_username}
				</p>
			)}

			{!isClosed && (
				// tap ≥ 44px (Button baseline ~40px, add min-h explicit).
				<Button
					onClick={handleClose}
					disabled={isLoading}
					className="tap mt-1 w-full bg-pumpkin text-white hover:bg-pumpkin/90"
				>
					{isLoading ? <Spinner size="sm" /> : "Позначити як проїхав"}
				</Button>
			)}
		</div>
	);
}
