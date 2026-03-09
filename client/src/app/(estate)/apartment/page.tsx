import ApartmentCreateForm from "@/components/forms/apartment/ApartmentCreateForm";
import { AuthFormHeader } from "@/components/forms/auth";
import type { Metadata } from "next";

export const metadata: Metadata = {
	title: "Skandi Apartments | Додати квартиру",
	description: "Авторизовані користувачі можуть додати дані своєї квартири",
};

export default function AddApartmentPage() {
	return (
		<div>
			<AuthFormHeader
				title="Додати квартиру"
				staticText="Хочете повернутись?"
				linkText="До профілю"
				linkHref="/profile"
			/>
			<div className="mt-7 sm:mx-auto sm:w-full sm:max-w-[480px]">
				<div className="bg-lightGrey dark:bg-deepBlueGrey rounded-xl px-6 py-12 shadow sm:rounded-lg sm:px-12 md:rounded-3xl">
					<ApartmentCreateForm />
				</div>
			</div>
		</div>
	);
}
