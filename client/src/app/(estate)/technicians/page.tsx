import TechnicianCard from "@/components/cards/TechnicianCard";
import type { Metadata } from "next";

export const metadata: Metadata = {
	title: "Alpha Apartments | Спеціалісти",
	description:
		"Мешканці можуть переглядати список технічних спеціалістів та їх рейтинг",
};

export default function TechniciansPage() {
	return (
		<>
			<TechnicianCard />
		</>
	);
}
