import BookmarkedPostCard from "@/components/cards/BookmarkedPostCard";
import type { Metadata } from "next";

export const metadata: Metadata = {
	title: "Alpha Apartments | Закладки",
	description: "Авторизовані користувачі можуть переглядати збережені публікації",
};

export default function BookmarkedPostsPage() {
	return (
		<>
			<BookmarkedPostCard />
		</>
	);
}
