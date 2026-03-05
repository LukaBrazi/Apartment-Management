import { AuthFormHeader } from "@/components/forms/auth";
import CreateReportForm from "@/components/forms/report-tenant/CreateReportForm";
import type { Metadata } from "next";

export const metadata: Metadata = {
	title: "Alpha Apartments | Скарга на мешканця",
	description:
		"Мешканці можуть поскаржитися на інших мешканців у разі неналежної поведінки",
};

export default function ReportTenantPage() {
	return (
		<div>
			<AuthFormHeader
				title="Поскаржитися на мешканця"
				staticText="Всі скарги залишаються анонімними. Ми вживемо відповідних заходів, не розкриваючи особу скаржника."
				linkText="До профілю"
				linkHref="/profile"
			/>
			<div className="mt-7 sm:mx-auto sm:w-full sm:max-w-[480px]">
				<div className="bg-lightGrey dark:bg-deepBlueGrey rounded-xl px-6 py-12 shadow sm:rounded-lg sm:px-12 md:rounded-3xl">
					<CreateReportForm />
				</div>
			</div>
		</div>
	);
}
