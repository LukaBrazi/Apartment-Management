"use client";

import {
	useGetPopularTagsQuery,
	useGetTopPostsQuery,
} from "@/lib/redux/features/posts/postApiSlice";
import { ChevronRight } from "lucide-react";
import Link from "next/link";

export default function RightNavbar() {
	const { data } = useGetTopPostsQuery();
	const topPosts = data?.top_posts.results;
	const { data: tagData } = useGetPopularTagsQuery();

	return (
		<section className="custom-scrollbar sticky right-0 top-0 flex h-screen w-[260px] flex-col gap-8 overflow-y-auto border-l border-[#E2E5E8] bg-white p-6 pt-36 max-xl:hidden dark:border-[#2D3D4F] dark:bg-[#162032]">
			<div>
				<h3 className="text-sm font-semibold uppercase tracking-wider text-[#6B7F8C] dark:text-[#8FA8B8]">
					Популярні публікації
				</h3>
				<div className="mt-4 flex flex-col gap-3">
					{topPosts && topPosts.length > 0 ? (
						topPosts.map((post) => (
							<Link
								key={post.id}
								href={`/post/${post.slug}`}
								className="group flex cursor-pointer items-center justify-between gap-3 rounded-lg p-2 transition-colors hover:bg-[#EBF3F5] dark:hover:bg-[#1A2E3A]"
							>
								<p className="text-sm text-[#1C2B3A] line-clamp-2 group-hover:text-[#3D7A8A] dark:text-[#F0EDE6] dark:group-hover:text-[#5BA3B5]">
									{post.title.length > 35 ? `${post.title.substring(0, 35)}…` : post.title}
								</p>
								<ChevronRight className="size-4 shrink-0 text-[#3D7A8A] dark:text-[#5BA3B5]" />
							</Link>
						))
					) : (
						<p className="text-sm text-[#6B7F8C] dark:text-[#8FA8B8]">
							Публікацій поки немає
						</p>
					)}
				</div>
			</div>

			<div>
				<h3 className="text-sm font-semibold uppercase tracking-wider text-[#6B7F8C] dark:text-[#8FA8B8]">
					Популярні теги
				</h3>
				<div className="mt-4 flex flex-col gap-2">
					{tagData && tagData.popular_tags.results.length > 0 ? (
						tagData.popular_tags.results.slice(0, 5).map((tag) => (
							<Link
								key={tag.slug}
								href={`/tags/${tag.slug}`}
								className="group flex cursor-pointer items-center justify-between gap-3 rounded-lg p-2 transition-colors hover:bg-[#EBF3F5] dark:hover:bg-[#1A2E3A]"
							>
								<div className="flex items-center gap-2">
									<span className="text-sm text-[#1C2B3A] group-hover:text-[#3D7A8A] dark:text-[#F0EDE6] dark:group-hover:text-[#5BA3B5]">
										{tag.name}
									</span>
									<span className="text-xs text-[#6B7F8C] dark:text-[#8FA8B8]">
										({tag.post_count})
									</span>
								</div>
								<ChevronRight className="size-4 shrink-0 text-[#3D7A8A] dark:text-[#5BA3B5]" />
							</Link>
						))
					) : (
						<p className="text-sm text-[#6B7F8C] dark:text-[#8FA8B8]">
							Тегів поки немає
						</p>
					)}
				</div>
			</div>
		</section>
	);
}
