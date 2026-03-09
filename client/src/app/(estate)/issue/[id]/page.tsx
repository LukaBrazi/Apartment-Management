import IssueDetails from "@/components/issue/IssueDetails";
import type { Metadata } from "next";

export const metadata: Metadata = {
	title: "Skandi Apartments | Деталі заявки",
	description:
		"Авторизовані користувачі можуть переглядати деталі своїх заявок та видаляти їх",
};

interface ParamsProps {
	params: {
		id: string;
	};
}

export default function IssueDetailPage({ params }: ParamsProps) {
	return (
		<div>
			<IssueDetails params={params} />
		</div>
	);
}
