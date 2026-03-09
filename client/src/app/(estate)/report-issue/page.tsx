import { AuthFormHeader } from "@/components/forms/auth";
import CreateIssueForm from "@/components/forms/report-issue/CreateIssueForm";
import type { Metadata } from "next";

export const metadata: Metadata = {
	title: "Skandi Apartments | Подати заявку",
	description:
		"Мешканці можуть повідомляти керівництво про проблеми зі своїми квартирами",
};

export default function ReportIssuePage() {
	return (
		<div className="mx-auto max-w-lg">
			<AuthFormHeader title="Подати заявку щодо квартири" />
			<div className="mt-8 sm:mx-auto sm:w-full sm:max-w-[480px]">
				<div className="rounded-2xl border border-[#E2E5E8] bg-white px-8 py-10 shadow-sm dark:border-[#2D3D4F] dark:bg-[#162032]">
					<CreateIssueForm />
				</div>
			</div>
		</div>
	);
}
