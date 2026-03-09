import PostCard from "@/components/cards/PostCard";
import type { Metadata } from "next";

export const metadata: Metadata = {
	title: "Skandi Apartments | Ласкаво просимо",
	description:
		"Ласкаво просимо до Skandi Apartments. Платформа для мешканців: подавайте заявки, залишайте оголошення та спілкуйтесь.",
};

export default function WelcomePage() {
	return (
		<>
			<PostCard />
		</>
	);
}
