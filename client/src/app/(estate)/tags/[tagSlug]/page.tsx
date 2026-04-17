import PostTagCard from "@/components/cards/PostTagCard";
import type { Metadata } from "next";

export const metadata: Metadata = {
	title: " ApartmentOS | Теги",
	description: "Авторизовані користувачі можуть переглядати публікації за тегом",
};

interface SlugParamsProps {
	params: {
		tagSlug: string;
	};
}

export default function TagPostsPage({ params }: SlugParamsProps) {
	return (
		<>
			<PostTagCard params={params} />
		</>
	);
}
