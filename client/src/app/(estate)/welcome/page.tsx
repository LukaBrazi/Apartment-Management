import type { Metadata } from "next";
import ResidentDashboard from "@/components/dashboard/ResidentDashboard";

export const metadata: Metadata = {
	title: "ApartmentOS | Кабінет мешканця",
	description: "Ваш особистий кабінет мешканця — заявки, оголошення та платіжки.",
};

export default function WelcomePage() {
	return <ResidentDashboard />;
}
