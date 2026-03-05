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
		<div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-lightGrey dark:bg-deepBlueGrey p-4 flex flex-col gap-3 shadow-sm">
			<div className="flex items-center justify-between">
				<div className="flex items-center gap-2">
					<UserIcon className="size-4 text-gray-500 dark:text-gray-400" />
					<span className="font-semibold dark:text-babyPowder">
						{pass.tenant_name}
					</span>
					<span className="text-sm text-gray-500 dark:text-gray-400">
						@{pass.tenant_username}
					</span>
				</div>
				<Badge
					className={
						isClosed
							? "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200"
							: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200"
					}
				>
					{isClosed ? "Закрита" : "Очікує"}
				</Badge>
			</div>

			<div className="grid grid-cols-2 gap-2 text-sm">
				{pass.building_name && (
					<div>
						<span className="text-gray-500 dark:text-gray-400">Будинок: </span>
						<span className="dark:text-babyPowder">{pass.building_name}</span>
					</div>
				)}
				{pass.unit_label && (
					<div>
						<span className="text-gray-500 dark:text-gray-400">Квартира: </span>
						<span className="dark:text-babyPowder">{pass.unit_label}</span>
					</div>
				)}
				<div className="flex items-center gap-1">
					<CarIcon className="size-4 text-gray-500 dark:text-gray-400" />
					<span className="dark:text-babyPowder">
						{pass.car_number || <em className="text-gray-400">Без номера</em>}
					</span>
				</div>
				<div className="flex items-center gap-1">
					<ClockIcon className="size-4 text-gray-500 dark:text-gray-400" />
					<span className="text-gray-500 dark:text-gray-400">
						Подано: {new Date(pass.created_at).toLocaleTimeString()}
					</span>
				</div>
			</div>

			{pass.comment && (
				<p className="text-sm italic text-gray-600 dark:text-gray-300 border-l-2 border-pumpkin pl-2">
					{pass.comment}
				</p>
			)}

			{isClosed && pass.closed_by_username && (
				<p className="text-xs text-gray-500 dark:text-gray-400 flex items-center gap-1">
					<CheckCircleIcon className="size-3 text-green-500" />
					Закрито @{pass.closed_by_username}
				</p>
			)}

			{!isClosed && (
				<Button
					onClick={handleClose}
					disabled={isLoading}
					className="bg-pumpkin hover:bg-pumpkin/90 text-white w-full mt-1"
				>
					{isLoading ? <Spinner size="sm" /> : "Позначити як проїхав"}
				</Button>
			)}
		</div>
	);
}
