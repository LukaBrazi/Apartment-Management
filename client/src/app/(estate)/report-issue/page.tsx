import { AuthFormHeader } from "@/components/forms/auth";
import CreateIssueForm from "@/components/forms/report-issue/CreateIssueForm";
import type { Metadata } from "next";

export const metadata: Metadata = {
	title: "ApartmentOS | Подати заявку",
	description:
		"Мешканці можуть повідомляти керівництво про проблеми зі своїми квартирами",
};

export default function ReportIssuePage() {
	return (
		<div className="mx-auto max-w-lg">
			<AuthFormHeader title="Подати заявку щодо квартири" />
			{/* Mobile: tight padding (p-5) so the form body gets more
			    screen real estate; Desktop (sm+): generous card. */}
			<div className="mt-6 sm:mx-auto sm:mt-8 sm:w-full sm:max-w-[480px]">
				<div className="rounded-2xl border border-[#E5E7EB] bg-white p-5 shadow-sm sm:px-8 sm:py-10 dark:border-[#2D3D4F] dark:bg-[#162032]">
					<CreateIssueForm />
				</div>
			</div>
		</div>
	);
}
