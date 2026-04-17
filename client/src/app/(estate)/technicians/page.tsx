import RoleGuard from "@/components/shared/RoleGuard";
import TechnicianCard from "@/components/cards/TechnicianCard";
import type { Metadata } from "next";

export const metadata: Metadata = {
	title: "ApartmentOS | Спеціалісти",
	description:
		"Мешканці можуть переглядати список технічних спеціалістів та їх рейтинг",
};

export default function TechniciansPage() {
	return (
		<RoleGuard role="staff">
			<TechnicianCard />
		</RoleGuard>
	);
}
