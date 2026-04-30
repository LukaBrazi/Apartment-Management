import AssignedIssues from "@/components/profile/AssignedIssues";
import type { Metadata } from "next";

export const metadata: Metadata = {
	title: "ApartmentOS | Призначені заявки",
	description: "Заявки призначені вам як виконавцю.",
};

export default function AssignedIssuesPage() {
	return (
		<div className="space-y-6">
			<h1 className="text-2xl font-bold text-[#0F172A] dark:text-white">
				Призначені заявки
			</h1>
			<AssignedIssues />
		</div>
	);
}
