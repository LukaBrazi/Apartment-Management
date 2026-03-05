"use client";
import {
	useGetUserProfileQuery,
	useUpdateUserProfileMutation,
} from "@/lib/redux/features/users/usersApiSlice";
import { profileSchema, TProfileSchema } from "@/lib/validationSchemas";
import { useRouter } from "next/navigation";
import React, { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import axios from "axios";
import * as z from "zod";
import { extractErrorMessage } from "@/utils";
import { toast } from "react-toastify";
import { FormFieldComponent } from "../FormFieldComponent";
import { Contact2Icon, Map, MapPinnedIcon, UserCheck2 } from "lucide-react";
import GenderSelectField from "./GenderSelectField";
import OccupationSelectField from "./OccupationSelectField";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import Spinner from "@/components/shared/Spinner";
import { Button } from "@/components/ui/button";

export default function EditProfileForm() {
	const { data } = useGetUserProfileQuery();

	const profile = data?.profile;
	const [avatar, setAvatar] = useState("");
	const [uploading, setUploading] = useState(false);

	const [updateUserProfile, { isLoading }] = useUpdateUserProfileMutation();

	const router = useRouter();

	const {
		register,
		handleSubmit,
		reset,
		setValue,
		control,
		formState: { errors },
	} = useForm<TProfileSchema>();

	useEffect(() => {
		if (profile) {
			reset({ ...profile });
		}
	}, [profile, reset]);

	const uploadFileHandler = async (e: React.ChangeEvent<HTMLInputElement>) => {
		if (!e.target.files) return;

		const file = e.target.files[0];
		const formData = new FormData();
		formData.append("avatar", file);
		setUploading(true);

		try {
			const config = {
				headers: {
					"Content-Type": "multipart/form-data",
				},
			};
			const { data } = await axios.patch(
				"/api/v1/profiles/user/avatar/",
				formData,
				config,
			);
			setAvatar(data);
			setUploading(false);
		} catch (error) {
			console.error("Error uploading file:", error);
		} finally {
			setUploading(false);
		}
	};

	const onSubmit = async (values: z.infer<typeof profileSchema>) => {
		try {
			await updateUserProfile(values).unwrap();
			toast.success("Профіль оновлено");
			router.push("/profile");
		} catch (error) {
			const errorMessage = extractErrorMessage(error);
			toast.error(errorMessage || "An error occurred");
		}
	};

	return (
		<main>
			<form
				noValidate
				onSubmit={handleSubmit(onSubmit)}
				className="flex w-full max-w-md flex-col gap-4"
			>
				<FormFieldComponent
					label="Ім'я користувача"
					name="username"
					register={register}
					errors={errors}
					placeholder="Ім'я користувача"
					startIcon={<UserCheck2 className="dark:text-babyPowder size-8" />}
				/>

				<FormFieldComponent
					label="Ім'я"
					name="first_name"
					register={register}
					errors={errors}
					placeholder="Ім'я"
					startIcon={<Contact2Icon className="dark:text-babyPowder size-8" />}
				/>
				<FormFieldComponent
					label="Прізвище"
					name="last_name"
					register={register}
					errors={errors}
					placeholder="Прізвище"
					startIcon={<Contact2Icon className="dark:text-babyPowder size-8" />}
				/>
				<GenderSelectField setValue={setValue} control={control} />
				<OccupationSelectField setValue={setValue} control={control} />
				<FormFieldComponent
					label="Країна"
					name="country_of_origin"
					register={register}
					errors={errors}
					placeholder="Ваша країна"
					startIcon={<Map className="dark:text-babyPowder size-8" />}
				/>

				<FormFieldComponent
					label="Місто"
					name="city_of_origin"
					register={register}
					errors={errors}
					placeholder="Місто"
					startIcon={<MapPinnedIcon className="dark:text-babyPowder size-8" />}
				/>

				<FormFieldComponent
					label="Про себе"
					name="bio"
					register={register}
					errors={errors}
					placeholder="Розкажіть про себе"
					isTextArea
				/>
				<Label className="h4-semibold dark:text-babyPowder" htmlFor="avatar">
					Аватар
				</Label>
				<div className="flex w-full cursor-pointer items-center">
					<div className="grow" style={{ maxWidth: "90%" }}>
						<Input
							accept="image/*"
							className="file:bg-eerieBlack dark:border-platinum dark:text-platinum cursor-pointer file:mr-3 file:rounded-md file:text-lime-500"
							id="avatar"
							name="avatar"
							type="file"
							onChange={uploadFileHandler}
						/>
					</div>
					{uploading && (
						<div className="shrink-0" style={{ width: "10%" }}>
							<Spinner size="sm" />
						</div>
					)}
				</div>
				<Button
					type="submit"
					className="h4-semibold bg-eerieBlack dark:bg-pumpkin mt-2 w-full text-white"
					disabled={isLoading}
				>
					{isLoading ? <Spinner size="sm" /> : `Оновити профіль`}
				</Button>
			</form>
		</main>
	);
}
