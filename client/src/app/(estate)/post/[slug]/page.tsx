import PostDetails from "@/components/post/PostDetails";
import type { Metadata } from "next";

export const metadata: Metadata = {
	title: "Alpha Apartments | Деталі публікації",
	description: "Авторизовані користувачі можуть переглядати деталі публікацій",
};

interface ParamsProps {
	params: {
		slug: string;
	};
}

export default function PostDetailPage({ params }: ParamsProps) {
	return (
		<>
			<PostDetails params={params} />
		</>
	);
}
