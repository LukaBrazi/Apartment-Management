import MyPassesView from "@/components/passes/MyPassesView";
import type { Metadata } from "next";

export const metadata: Metadata = {
	title: "ApartmentOS | Мої перепустки",
	description: "Список ваших заявок на в'їзд авто",
};

export default function MyPassesPage() {
	return <MyPassesView />;
}
