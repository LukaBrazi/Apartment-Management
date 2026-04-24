"use client";

import { Button } from "@/components/ui/button";
import Spinner from "@/components/shared/Spinner";
import { useCreatePassMutation } from "@/lib/redux/features/passes/passApiSlice";
import { passCreateSchema, TPassCreateSchema } from "@/lib/validationSchemas";
import { extractErrorMessage } from "@/utils";
import { zodResolver } from "@hookform/resolvers/zod";
import { CarIcon } from "lucide-react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { toast } from "react-toastify";
import { FormFieldComponent } from "../FormFieldComponent";

export default function CreatePassForm() {
	const [createPass, { isLoading }] = useCreatePassMutation();
	const router = useRouter();

	const {
		register,
		handleSubmit,
		reset,
		formState: { errors },
	} = useForm<TPassCreateSchema>({
		resolver: zodResolver(passCreateSchema),
		mode: "all",
	});

	const onSubmit = async (values: TPassCreateSchema) => {
		try {
			await createPass(values).unwrap();
			toast.success("Перепустку успішно замовлено.");
			reset();
			router.push("/welcome");
		} catch (error) {
			const msg = extractErrorMessage(error);
			toast.error(msg || "An error occurred");
		}
	};

	return (
		<form
			noValidate
			onSubmit={handleSubmit(onSubmit)}
			className="flex w-full max-w-md flex-col gap-4 dark:text-black"
		>
			<div>
				<label className="h4-semibold dark:text-babyPowder block mb-1">
					Дата відвідування <span className="text-red-500">*</span>
				</label>
				<input
					type="date"
					{...register("visit_date")}
					min={new Date().toISOString().split("T")[0]}
					className="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm dark:bg-deepBlueGrey dark:text-babyPowder dark:border-gray-600 focus:outline-none focus:ring-2 focus:ring-pumpkin"
				/>
				{errors.visit_date && (
					<p className="mt-1 text-sm text-red-500">{errors.visit_date.message}</p>
				)}
			</div>

			<FormFieldComponent
				label="Номер авто (необов'язково)"
				name="car_number"
				register={register}
				errors={errors}
				placeholder="напр. AA1234BB"
				startIcon={<CarIcon className="dark:text-babyPowder size-8" />}
			/>

			<FormFieldComponent
				label="Коментар (необов'язково)"
				name="comment"
				register={register}
				errors={errors}
				placeholder="Будь-яка примітка для охорони"
				isTextArea
				startIcon={<CarIcon className="dark:text-babyPowder size-8" />}
			/>

			<Button
				type="submit"
				className="h4-semibold bg-eerieBlack dark:bg-pumpkin mt-2 w-full text-white"
				disabled={isLoading}
			>
				{isLoading ? <Spinner size="sm" /> : "Надіслати заявку"}
			</Button>
		</form>
	);
}
