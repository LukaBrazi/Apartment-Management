import React from "react";
import type { Metadata } from "next";
import { AuthFormHeader } from "@/components/forms/auth";
import UpdateIssueForm from "@/components/forms/update-issue/UpdateIssueForm";

export const metadata: Metadata = {
	title: "Alpha Apartments | Оновити заявку",
	description:
		"Призначені спеціалісти можуть оновлювати статус заявки",
};

interface UpdateParamsProps {
	params: {
		id: string;
	};
}

export default function UpdateIssuePage({ params }: UpdateParamsProps) {
	return (
		<div>
			<AuthFormHeader
				title="Оновити заявку"
				staticText="Хочете повернутись?"
				linkText="До профілю"
				linkHref="/profile"
			/>
			<div className="mt-7 sm:mx-auto sm:w-full sm:max-w-[480px]">
				<div className="bg-lightGrey dark:bg-deepBlueGrey rounded-xl px-6 py-12 shadow sm:rounded-lg sm:px-12 md:rounded-3xl">
					<UpdateIssueForm params={params} />
				</div>
			</div>
		</div>
	);
}
