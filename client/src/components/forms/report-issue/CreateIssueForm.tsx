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
import { Controller, useForm } from "react-hook-form";
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
	// PR-4: the reporter's Unit is read from their Profile.  Backend
	// derives the target Unit from ``profile.unit`` when no id is sent.
	const { data: profileData } = useGetUserProfileQuery();
	const profile = profileData?.profile;
	const hasUnit = Boolean(profile?.unit_id);

	const [selectedBuildingId, setSelectedBuildingId] = useState<string | null>(null);
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
		control,
		reset,
		setValue,
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

	const onSubmit = async (formValues: TIssueCreateSchema) => {
		if (!hasUnit) {
			toast.error(
				"До вашого профілю не прив'язано квартиру. Зверніться до адміністратора.",
			);
			return;
		}

		try {
			// Backend resolves the Unit from request.user.profile.unit.
			await reportIssue(formValues).unwrap();
			toast.success("Заявку подано. Підтвердження надіслано на вашу пошту.");
			reset();
			setSelectedBuildingId(null);
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
								setValue("location_note", "");
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
									const bid = val?.value ?? null;
									setSelectedBuildingId(bid);
									const selected = buildingsData?.buildings?.find((b) => b.id === bid);
									setValue(
										"location_note",
										selected
											? (selected.address ? `${selected.name} (${selected.address})` : selected.name)
											: "",
									);
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
								<Controller
									name="location_note"
									control={control}
									render={({ field: { onChange, onBlur, value } }) => (
										<Select
											options={entranceOptions}
											value={entranceOptions.find((o) => {
												const building = buildingsData?.buildings?.find(
													(b) => b.id === selectedBuildingId,
												);
												return value === `${building?.name} / Під'їзд ${o.label.replace("Під'їзд ", "")}`;
											}) ?? null}
											onChange={(val) => {
												const building = buildingsData?.buildings?.find(
													(b) => b.id === selectedBuildingId,
												);
												const bLabel = building
													? (building.address ? `${building.name} (${building.address})` : building.name)
													: "";
												if (val && building) {
													onChange(`${bLabel} / Під'їзд ${val.label.replace("Під'їзд ", "")}`);
												} else {
													onChange(bLabel);
												}
											}}
											onBlur={onBlur}
											placeholder={entrancesLoading ? "Завантаження..." : "Оберіть під'їзд (необов'язково)"}
											isLoading={entrancesLoading}
											instanceId="entrance-select"
											styles={customStyles}
											isClearable
										/>
									)}
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
