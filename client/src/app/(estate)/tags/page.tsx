"use client";

import { useGetPopularTagsQuery } from "@/lib/redux/features/posts/postApiSlice";
import Spinner from "@/components/shared/Spinner";
import Link from "next/link";
import { Hash, ChevronRight } from "lucide-react";

export default function TagsPage() {
	const { data, isLoading } = useGetPopularTagsQuery();
	const tags = data?.popular_tags?.results ?? [];

	if (isLoading) {
		return (
			<div className="flex flex-col gap-6">
				<div>
					<h1 className="text-2xl font-bold text-[#111827] dark:text-[#F0EDE6]">Теги</h1>
					<p className="text-sm text-[#6B7280] mt-1 dark:text-[#8FA8B8]">Перегляд публікацій за тегами</p>
				</div>
				<div className="flex-center pt-16">
					<Spinner size="xl" />
				</div>
			</div>
		);
	}

	return (
		<div className="flex flex-col gap-6">
			<div>
				<h1 className="text-2xl font-bold text-[#111827] dark:text-[#F0EDE6]">Теги</h1>
				<p className="text-sm text-[#6B7280] mt-1 dark:text-[#8FA8B8]">
					Перегляд публікацій за тегами
					{tags.length > 0 && (
						<span className="ml-2 inline-flex items-center rounded-full bg-[#EEF3FD] px-2 py-0.5 text-xs font-medium text-[#2F6FED] dark:bg-[#1A2E3A] dark:text-[#5BA3B5]">
							{tags.length}
						</span>
					)}
				</p>
			</div>

			{tags.length === 0 ? (
				<div className="rounded-2xl border border-[#E5E7EB] bg-white p-8 text-center shadow-sm dark:border-[#2D3D4F] dark:bg-[#162032]">
					<div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-[#EEF3FD] dark:bg-[#1A2E3A]">
						<Hash className="h-8 w-8 text-[#2F6FED] dark:text-[#5BA3B5]" />
					</div>
					<h2 className="text-lg font-semibold text-[#111827] dark:text-[#F0EDE6]">Тегів поки немає</h2>
					<p className="mt-2 text-sm text-[#6B7280] dark:text-[#8FA8B8]">Публікацій з тегами ще не створено.</p>
				</div>
			) : (
				<div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
					{tags.map((tag) => (
						<Link
							key={tag.slug}
							href={`/tags/${tag.slug}`}
							className="group flex items-center justify-between rounded-2xl border border-[#E5E7EB] bg-white p-4 shadow-sm transition-all hover:border-[#2F6FED] hover:shadow-md dark:border-[#2D3D4F] dark:bg-[#162032] dark:hover:border-[#5BA3B5]"
						>
							<div className="flex items-center gap-3">
								<div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[#EEF3FD] group-hover:bg-[#2F6FED] dark:bg-[#1A2E3A] dark:group-hover:bg-[#5BA3B5] transition-colors">
									<Hash className="h-5 w-5 text-[#2F6FED] group-hover:text-white dark:text-[#5BA3B5] dark:group-hover:text-white transition-colors" />
								</div>
								<div>
									<p className="text-sm font-semibold text-[#111827] dark:text-[#F0EDE6]">{tag.name}</p>
									<p className="text-xs text-[#6B7280] dark:text-[#8FA8B8]">
										{tag.post_count} {tag.post_count === 1 ? "публікація" : "публікацій"}
									</p>
								</div>
							</div>
							<ChevronRight className="h-5 w-5 text-[#6B7280] group-hover:text-[#2F6FED] dark:text-[#8FA8B8] dark:group-hover:text-[#5BA3B5] transition-colors" />
						</Link>
					))}
				</div>
			)}
		</div>
	);
}
