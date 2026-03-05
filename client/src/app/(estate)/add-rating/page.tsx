import CreateRatingForm from "@/components/forms/add-rating/CreateRatingForm";
import { AuthFormHeader } from "@/components/forms/auth";
import type { Metadata } from "next";

export const metadata: Metadata = {
	title: "Alpha Apartments | Залишити оцінку",
	description:
		"Мешканці можуть оцінювати технічний персонал",
};

export default function AddRatingPage() {
	return (
		<div>
			<AuthFormHeader
				title="Оцінити технічного спеціаліста"
				staticText="Розкажіть нам, що ви думаєте про надані послуги"
				linkText="До списку спеціалістів"
				linkHref="/technicians"
			/>
			<div className="mt-7 sm:mx-auto sm:w-full sm:max-w-[480px]">
				<div className="bg-lightGrey dark:bg-deepBlueGrey rounded-xl px-6 py-12 shadow sm:rounded-lg sm:px-12 md:rounded-3xl">
					<CreateRatingForm />
				</div>
			</div>
		</div>
	);
}
