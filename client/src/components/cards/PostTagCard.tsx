"use client";

import { useGetPostsByTagQuery } from "@/lib/redux/features/posts/postApiSlice";
import Spinner from "../shared/Spinner";
import {
	Card,
	CardContent,
	CardDescription,
	CardHeader,
	CardTitle,
} from "../ui/card";
import { formatDate, getRepliesText, getViewText } from "@/utils";
import { formatDistanceToNow, parseISO } from "date-fns";
import Link from "next/link";
import { Button } from "../ui/button";
import { EyeIcon, MessageSquareQuoteIcon, Hash } from "lucide-react";

interface SlugParamsProps {
	params: {
		tagSlug: string;
	};
}

export default function PostTagCard({ params }: SlugParamsProps) {
	const { data, isLoading } = useGetPostsByTagQuery(params.tagSlug);
	const decodedTag = decodeURIComponent(params.tagSlug);

	if (isLoading) {
		return (
			<div className="flex-center pt-32">
				<Spinner size="xl" />
			</div>
		);
	}

	const posts = data?.posts_by_tag?.results || [];

	return (
		<div className="flex flex-col gap-6">
			<div className="flex items-center gap-3">
				<div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-[#EEF3FD] dark:bg-[#1A2E3A]">
					<Hash className="h-6 w-6 text-[#2F6FED] dark:text-[#5BA3B5]" />
				</div>
				<div>
					<h1 className="text-2xl font-bold text-[#111827] dark:text-[#F0EDE6]">
						Публікації з тегом &ldquo;{decodedTag}&rdquo;
					</h1>
					<p className="text-sm text-[#6B7280] dark:text-[#8FA8B8]">
						{posts.length > 0
							? `Знайдено ${posts.length} публікацій`
							: "Публікацій не знайдено"}
					</p>
				</div>
			</div>

			{posts.length === 0 ? (
				<div className="rounded-2xl border border-[#E5E7EB] bg-white p-8 text-center shadow-sm dark:border-[#2D3D4F] dark:bg-[#162032]">
					<p className="text-sm text-[#6B7280] dark:text-[#8FA8B8]">
						За тегом &ldquo;{decodedTag}&rdquo; публікацій не знайдено.
					</p>
				</div>
			) : (
				<div className="grid grid-cols-1 gap-4 md:grid-cols-2">
					{posts.map((post) => (
						<Card
							key={post.id}
							className="rounded-2xl border border-[#E5E7EB] bg-white shadow-sm transition-shadow hover:shadow-md dark:border-[#2D3D4F] dark:bg-[#162032]"
						>
							<CardHeader className="pb-3">
								<CardTitle className="text-lg font-semibold text-[#111827] dark:text-[#F0EDE6] line-clamp-2">
									{post.title}
								</CardTitle>
								<CardDescription>
									<div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-[#6B7280] dark:text-[#8FA8B8]">
										<span>
											Опубліковано{" "}
											<span className="font-medium text-[#374151] dark:text-[#C5D0D8]">
												{formatDate(post.created_at).toString()}
											</span>
										</span>
										<span>
											Оновлено{" "}
											<span className="font-medium text-[#374151] dark:text-[#C5D0D8]">
												{formatDistanceToNow(parseISO(post.updated_at), {
													addSuffix: true,
												})}
											</span>
										</span>
									</div>
								</CardDescription>
							</CardHeader>
							<CardContent className="border-t border-[#E5E7EB] py-3 dark:border-[#2D3D4F]">
								<p className="text-sm text-[#374151] dark:text-[#C5D0D8] line-clamp-3">
									{post.body}
								</p>
							</CardContent>

							<div className="flex items-center justify-between border-t border-[#E5E7EB] p-4 dark:border-[#2D3D4F]">
								<Link href={`/post/${post.slug}`}>
									<Button
										size="sm"
										className="rounded-lg bg-[#2F6FED] text-white hover:bg-[#1E5BCC] dark:bg-[#5BA3B5] dark:hover:bg-[#4A8D9E]"
									>
										Переглянути
									</Button>
								</Link>
								<div className="flex items-center gap-4 text-sm text-[#6B7280] dark:text-[#8FA8B8]">
									<div className="flex items-center gap-1">
										<EyeIcon className="h-4 w-4" />
										<span>{getViewText(post.view_count)}</span>
									</div>
									<div className="flex items-center gap-1">
										<MessageSquareQuoteIcon className="h-4 w-4" />
										<span>{getRepliesText(post.replies_count)}</span>
									</div>
								</div>
							</div>
						</Card>
					))}
				</div>
			)}
		</div>
	);
}
