import PostCard from "@/components/cards/PostCard";
import type { Metadata } from "next";

export const metadata: Metadata = {
	title: "Alpha Apartments | Ласкаво просимо",
	description:
		"Ласкаво просимо до Alpha Apartments. Платформа для мешканців: подавайте заявки, залишайте оголошення та спілкуйтесь.",
};

export default function WelcomePage() {
	return (
		<>
			<PostCard />
		</>
	);
}
