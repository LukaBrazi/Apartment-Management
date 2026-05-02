"use client";

import {
	useGetBuildingsQuery,
	useGetEntrancesQuery,
} from "@/lib/redux/features/apartment/apartmentApiSlice";
import { useGetUserProfileQuery } from "@/lib/redux/features/users/usersApiSlice";
import { useReportIssueMutation } from "@/lib/redux/features/issues/issueApiSlice";
import { issueCreateSchema, TIssueCreateSchema } from "@/lib/validationSchemas";
import { extractErrorMessage } from "@/utils";
import { zodResolver } from "@hookform/resolvers/zod";
import dynamic from "next/dynamic";
import { useRouter } from "next/navigation";
import React, { useState } from "react";
import { useForm } from "react-hook-form";
import { toast } from "react-toastify";
import { FormFieldComponent } from "../FormFieldComponent";
import Select from "react-select";
import customStyles from "../selectStyles";
import { Button } from "@/components/ui/button";
import Spinner from "@/components/shared/Spinner";
import { MapPinIcon } from "lucide-react";

const ClientOnly = dynamic<{ children: React.ReactNode }>(
	() => Promise.resolve(({ children }) => <>{children}</>),
	{ ssr: false },
);

export default function CreateIssueForm() {
	// Backend resolves Unit from primary Residency (see PR-11) when no id is sent.
	const { data: profileData } = useGetUserProfileQuery();
	const profile = profileData?.profile;
	const hasUnit = Boolean(profile?.unit_id);

	// Local-only selection state — composed into `location_note` on
	// submit.  Keeping these out of react-hook-form avoids the race
	// between the building's `setValue` and the entrance Controller
	// that previously dropped the entrance suffix on submit.
	const [selectedBuildingId, setSelectedBuildingId] = useState<string | null>(null);
	const [selectedEntranceId, setSelectedEntranceId] = useState<string | null>(null);
	const [notBuildingRelated, setNotBuildingRelated] = useState(false);

	const { data: buildingsData, isLoading: buildingsLoading } = useGetBuildingsQuery();
	const { data: entrancesData, isLoading: entrancesLoading } = useGetEntrancesQuery(
		selectedBuildingId ?? "",
		{ skip: !selectedBuildingId },
	);

	const [reportIssue, { isLoading }] = useReportIssueMutation();
	const router = useRouter();

	const {
		register,
		handleSubmit,
		reset,
		formState: { errors },
	} = useForm<TIssueCreateSchema>({
		resolver: zodResolver(issueCreateSchema),
		mode: "all",
	});

	const buildingOptions =
		buildingsData?.buildings?.map((b) => ({
			value: b.id,
			label: b.address ? `${b.name} — ${b.address}` : b.name,
		})) ?? [];

	const entranceOptions =
		entrancesData?.entrances?.map((e) => ({
			value: e.id,
			label: `Під'їзд ${e.name}`,
		})) ?? [];

	// Compose location_note from current selection (building + optional
	// entrance).  Building label uses "(address)" suffix only when the
	// building has one, so the format is consistent with what the
	// backend prepends to description: "📍 Місце: …".
	const composeLocationNote = (): string => {
		if (notBuildingRelated) return "";
		const building = buildingsData?.buildings?.find((b) => b.id === selectedBuildingId);
		if (!building) return "";
		const buildingLabel = building.address
			? `${building.name} (${building.address})`
			: building.name;
		const entrance = entrancesData?.entrances?.find((e) => e.id === selectedEntranceId);
		if (entrance) {
			return `${buildingLabel} / Підʼїзд ${entrance.name}`;
		}
		return buildingLabel;
	};

	const onSubmit = async (formValues: TIssueCreateSchema) => {
		if (!hasUnit) {
			toast.error(
				"До вашого профілю не прив'язано квартиру. Зверніться до адміністратора.",
			);
			return;
		}

		try {
			// Backend resolves Unit from primary Residency (see PR-11).
			// We send `location_note` composed locally here — NOT from
			// react-hook-form state — to avoid the race that previously
			// dropped the entrance suffix between Controller / setValue.
			await reportIssue({
				...formValues,
				location_note: composeLocationNote(),
			}).unwrap();
			toast.success("Заявку подано. Підтвердження надіслано на вашу пошту.");
			reset();
			setSelectedBuildingId(null);
			setSelectedEntranceId(null);
			setNotBuildingRelated(false);
			router.push("/welcome");
		} catch (error) {
			const errorMessage = extractErrorMessage(error);
			toast.error(errorMessage || "Сталася помилка. Спробуйте ще раз.");
		}
	};

	return (
		<form
			noValidate
			onSubmit={handleSubmit(onSubmit)}
			className="flex w-full max-w-md flex-col gap-5"
		>
			<FormFieldComponent
				label="Назва заявки"
				name="title"
				register={register}
				errors={errors}
				placeholder="Коротко опишіть проблему"
			/>

			{/* Location section */}
			<div className="flex flex-col gap-3 rounded-xl border border-[#E2E5E8] bg-[#F7F6F2] p-4 dark:border-[#2D3D4F] dark:bg-[#1E2D3D]">
				<div className="flex items-center gap-2">
					<MapPinIcon className="size-5 text-[#3D7A8A] dark:text-[#5BA3B5]" />
					<span className="text-sm font-semibold text-[#1C2B3A] dark:text-[#F0EDE6]">
						Місце проблеми
					</span>
				</div>

				<label className="flex cursor-pointer items-center gap-3">
					<input
						type="checkbox"
						checked={notBuildingRelated}
						onChange={(e) => {
							setNotBuildingRelated(e.target.checked);
							if (e.target.checked) {
								setSelectedBuildingId(null);
								setSelectedEntranceId(null);
							}
						}}
						className="size-4 rounded border-[#E2E5E8] accent-[#3D7A8A]"
					/>
					<span className="text-sm text-[#6B7F8C] dark:text-[#8FA8B8]">
						Не стосується будинку
					</span>
				</label>

				{!notBuildingRelated && (
					<div className="flex flex-col gap-3">
						<ClientOnly>
							<Select
								options={buildingOptions}
								value={buildingOptions.find((o) => o.value === selectedBuildingId) ?? null}
								onChange={(val) => {
									setSelectedBuildingId(val?.value ?? null);
									// Reset entrance whenever the building changes, otherwise
									// stale entranceId can compose into a different building's
									// label on submit.
									setSelectedEntranceId(null);
								}}
								placeholder={buildingsLoading ? "Завантаження..." : "Оберіть будинок"}
								isLoading={buildingsLoading}
								instanceId="building-select"
								styles={customStyles}
								isClearable
							/>
						</ClientOnly>

						{selectedBuildingId && (
							<ClientOnly>
								<Select
									options={entranceOptions}
									value={
										entranceOptions.find((o) => o.value === selectedEntranceId) ?? null
									}
									onChange={(val) => {
										setSelectedEntranceId(val?.value ?? null);
									}}
									placeholder={
										entrancesLoading
											? "Завантаження..."
											: entranceOptions.length === 0
												? "У будинку немає підʼїздів"
												: "Оберіть підʼїзд (необовʼязково)"
									}
									isLoading={entrancesLoading}
									isDisabled={!entrancesLoading && entranceOptions.length === 0}
									instanceId="entrance-select"
									styles={customStyles}
									isClearable
								/>
							</ClientOnly>
						)}
					</div>
				)}
			</div>

			<FormFieldComponent
				label="Детальний опис"
				name="description"
				register={register}
				errors={errors}
				placeholder="Опишіть проблему докладніше — що сталося, де, коли"
				isTextArea
			/>

			<Button
				type="submit"
				disabled={isLoading}
				className="h-11 w-full rounded-xl bg-[#3D7A8A] text-sm font-semibold text-white shadow-none transition-colors hover:bg-[#2E6070] disabled:opacity-60 dark:bg-[#5BA3B5] dark:hover:bg-[#4A8FA0]"
			>
				{isLoading ? <Spinner size="sm" /> : "Подати заявку"}
			</Button>
		</form>
	);
}
