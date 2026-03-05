"use client";
import * as z from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { Contact2Icon, MailIcon, UserCheck2 } from "lucide-react";
import { useRegisterUserMutation } from "@/lib/redux/features/auth/authApiSlice";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import {
	registerUserSchema,
	TRregisterUserSchema,
} from "@/lib/validationSchemas";
import { extractErrorMessage } from "@/utils";
import { toast } from "react-toastify";
import { FormFieldComponent } from "@/components/forms/FormFieldComponent";
import { Button } from "@/components/ui/button";
import Spinner from "@/components/shared/Spinner";

export default function RegisterForm() {
	const [registerUser, { isLoading }] = useRegisterUserMutation();
	const router = useRouter();

	const {
		register,
		handleSubmit,
		reset,
		formState: { errors },
	} = useForm<TRregisterUserSchema>({
		resolver: zodResolver(registerUserSchema),
		mode: "all",
		defaultValues: {
			username: "",
			first_name: "",
			last_name: "",
			email: "",
			password: "",
			re_password: "",
		},
	});

	const onSubmit = async (values: z.infer<typeof registerUserSchema>) => {
		try {
			await registerUser(values).unwrap();
			toast.success(
				"На вашу електронну адресу надіслано листа з посиланням для активації. Перевірте пошту та активуйте акаунт.",
			);
			router.push("/login");
			reset();
		} catch (e) {
			const errorMessage = extractErrorMessage(e);
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

				<FormFieldComponent
					label="Електронна адреса"
					name="email"
					register={register}
					errors={errors}
					placeholder="Електронна адреса"
					startIcon={<MailIcon className="dark:text-babyPowder size-8" />}
				/>

				<FormFieldComponent
					label="Пароль"
					name="password"
					register={register}
					errors={errors}
					placeholder="Пароль"
					isPassword={true}
				/>

				<FormFieldComponent
					label="Підтвердіть пароль"
					name="re_password"
					register={register}
					errors={errors}
					placeholder="Підтвердіть пароль"
					isPassword={true}
				/>
				<Button
					type="submit"
					className="h4-semibold bg-eerieBlack dark:bg-pumpkin w-full text-white"
					disabled={isLoading}
				>
					{isLoading ? <Spinner size="sm" /> : `Зареєструватися`}
				</Button>
			</form>
		</main>
	);
}
