import { occupationOptions, residentOccupationOptions } from "@/constants";
import { useGetUserProfileQuery } from "@/lib/redux/features/users/usersApiSlice";
import { TProfileSchema } from "@/lib/validationSchemas";
import { Occupation } from "@/types";
import { Briefcase } from "lucide-react";
import dynamic from "next/dynamic";
import React, { useEffect } from "react";
import { Control, Controller, UseFormSetValue } from "react-hook-form";
import Select from "react-select";
import customStyles from "../selectStyles";

const ClientOnly = dynamic<{ children: React.ReactNode }>(
	() => Promise.resolve(({ children }) => <>{children}</>),
	{ ssr: false },
);

// Values that belong to residents — they can switch between these two.
const RESIDENT_OCCUPATIONS: Occupation[] = ["tenant", "owner"];

// Values assigned by admin — read-only in the UI.
const WORKER_OCCUPATIONS: Occupation[] = [
	"mason",
	"carpenter",
	"plumber",
	"roofer",
	"painter",
	"electrician",
	"hvac",
	"guard",
];

function isOccupation(value: any): value is Occupation {
	return [...RESIDENT_OCCUPATIONS, ...WORKER_OCCUPATIONS].includes(value);
}

function getOccupationLabel(value: Occupation): string {
	return occupationOptions.find((o) => o.value === value)?.label ?? value;
}

interface OccupationSelectFieldProps {
	setValue: UseFormSetValue<TProfileSchema>;
	control: Control<TProfileSchema>;
}

export default function OccupationSelectField({
	setValue,
	control,
}: OccupationSelectFieldProps) {
	const { data: profileData } = useGetUserProfileQuery();
	const profile = profileData?.profile;

	const currentOccupation = profile?.occupation as Occupation | undefined;
	const isResident =
		!currentOccupation || RESIDENT_OCCUPATIONS.includes(currentOccupation);

	useEffect(() => {
		if (profile?.occupation) {
			const occupation = profile.occupation as Occupation;
			if (isOccupation(occupation)) {
				setValue("occupation", occupation);
			}
		}
	}, [profile, setValue]);

	return (
		<div>
			<label htmlFor="occupation" className="h4-semibold dark:text-babyPowder">
				Рід занять
			</label>
			<div className="mt-1 flex items-center space-x-3">
				<Briefcase className="dark:text-babyPowder size-8" />
				{isResident ? (
					// Residents can switch between "Мешканець" and "Власник" only.
					<ClientOnly>
						<Controller
							control={control}
							name="occupation"
							render={({ field }) => (
								<Select
									className="mt-1 w-full"
									{...field}
									options={residentOccupationOptions}
									value={residentOccupationOptions.find(
										(option) => option.value === field.value,
									)}
									onChange={(option) => field.onChange(option?.value)}
									instanceId="occupation-select"
									styles={customStyles}
								/>
							)}
						/>
					</ClientOnly>
				) : (
					// Workers / guards have their occupation assigned by admin — read-only.
					<div className="mt-1 flex h-10 w-full items-center rounded-md border border-gray-200 bg-gray-50 px-3 text-sm text-gray-600 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-300">
						{currentOccupation ? getOccupationLabel(currentOccupation) : "—"}
					</div>
				)}
			</div>
			{!isResident && (
				<p className="mt-1 text-xs text-gray-400">
					Рід занять встановлюється адміністратором
				</p>
			)}
		</div>
	);
}
