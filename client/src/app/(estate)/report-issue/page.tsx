import { AuthFormHeader } from "@/components/forms/auth";
import CreateIssueForm from "@/components/forms/report-issue/CreateIssueForm";
import type { Metadata } from "next";

export const metadata: Metadata = {
	title: "Alpha Apartments | Подати заявку",
	description:
		"Мешканці можуть повідомляти керівництво про проблеми зі своїми квартирами",
};

export default function ReportIssuePage() {
	return (
		<div>
			<AuthFormHeader title="Подати заявку щодо квартири" />
			<div className="mt-7 sm:mx-auto sm:w-full sm:max-w-[480px]">
				<div className="bg-lightGrey dark:bg-deepBlueGrey rounded-xl px-6 py-12 shadow sm:rounded-lg sm:px-12 md:rounded-3xl">
					<p className="dark:text-pumpkin text-2xl">
						<CreateIssueForm />
					</p>
				</div>
			</div>
		</div>
	);
}
