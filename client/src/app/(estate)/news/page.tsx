"use client";

import { useGetNewsQuery } from "@/lib/redux/features/news/newsApiSlice";
import { NewsItem } from "@/types";
import Image from "next/image";
import Link from "next/link";
import { format } from "date-fns";
import { uk } from "date-fns/locale";
import { Pin, ExternalLink } from "lucide-react";

function NewsCard({ item, pinned = false }: { item: NewsItem; pinned?: boolean }) {
	return (
		<Link
			href={`/news/${item.slug}`}
			className="group relative flex flex-col overflow-hidden rounded-2xl border border-[#F1F5F9] bg-white shadow-[0_1px_2px_rgba(0,0,0,0.05)] transition-shadow hover:shadow-md dark:border-[#2D3D4F] dark:bg-[#162032]"
		>
			{item.cover_image && (
				<img
					src={item.cover_image}
					alt={item.title}
					className="h-40 w-full object-cover sm:h-44"
				/>
			)}
			{pinned && (
				<span className="absolute top-3 right-3 rounded-full bg-[#1E2761] px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-[#CADCFC]">
					Закріплено
				</span>
			)}
			<div className="flex flex-1 flex-col gap-2 p-4">
				<div className="flex flex-wrap items-center gap-2">
					{item.pinned && !item.cover_image && (
						<Pin className="h-3.5 w-3.5 flex-shrink-0 text-[#1E2761]" />
					)}
					{item.category && (
						<span
							className="rounded-full px-2 py-0.5 text-xs font-medium"
							style={{
								background: `${item.category.color}20`,
								color: item.category.color,
							}}
						>
							{item.category.name}
						</span>
					)}
				</div>
				<h2 className="line-clamp-2 text-base font-semibold text-[#111827] transition-colors group-hover:text-[#4A90D9] dark:text-[#F0EDE6]">
					{item.title}
				</h2>
				<p className="line-clamp-3 text-sm text-[#6B7280] dark:text-[#A0B3C1]">
					{item.excerpt}
				</p>
				<div className="mt-auto flex items-center justify-between border-t border-[#F3F4F6] pt-2 dark:border-[#2D3D4F]">
					<span className="text-xs text-[#9CA3AF]">
						{item.published_at
							? format(new Date(item.published_at), "d MMM yyyy", { locale: uk })
							: format(new Date(item.created_at), "d MMM yyyy", { locale: uk })}
					</span>
					{item.external_url && (
						<ExternalLink className="h-3.5 w-3.5 text-[#9CA3AF]" />
					)}
				</div>
			</div>
		</Link>
	);
}

export default function NewsPage() {
	const { data, isLoading, isError } = useGetNewsQuery();
	const newsList = data?.news ?? [];

	if (isLoading) {
		return (
			<div className="flex flex-col gap-4 md:gap-6">
				<h1 className="text-xl font-bold text-[#111827] md:text-2xl dark:text-[#F0EDE6]">
					Новини
				</h1>
				<div className="text-sm text-[#6B7280]">Завантаження...</div>
			</div>
		);
	}

	if (isError) {
		return (
			<div className="flex flex-col gap-4 md:gap-6">
				<h1 className="text-xl font-bold text-[#111827] md:text-2xl dark:text-[#F0EDE6]">
					Новини
				</h1>
				<div className="rounded-2xl border border-red-100 bg-red-50 p-5 text-sm text-red-600 md:p-6">
					Не вдалося завантажити новини.
				</div>
			</div>
		);
	}

	const pinned = newsList.filter((item) => item.pinned);
	const regular = newsList.filter((item) => !item.pinned);

	return (
		<div className="flex flex-col gap-4 md:gap-6">
			<div>
				<h1 className="text-xl font-bold text-[#111827] md:text-2xl dark:text-[#F0EDE6]">
					Новини
				</h1>
				<p className="mt-1 text-xs text-[#6B7280] md:text-sm dark:text-[#8FA8B8]">
					Актуальні новини та оновлення порталу
				</p>
			</div>

			{newsList.length === 0 ? (
				<div className="flex flex-col items-center gap-4 rounded-2xl border border-[#F1F5F9] bg-white p-6 text-center shadow-[0_1px_2px_rgba(0,0,0,0.05)] md:p-10 dark:border-[#2D3D4F] dark:bg-[#162032]">
					<Image
						src="/assets/images/empty-states/empty-announcements.svg"
						alt=""
						width={180}
						height={180}
						className="h-32 w-32 opacity-70 md:h-[180px] md:w-[180px]"
					/>
					<p className="text-sm text-[#6B7280]">Новин ще немає</p>
					<p className="text-xs text-[#9CA3AF]">
						Слідкуйте за оновленнями порталу
					</p>
				</div>
			) : (
				<>
					{pinned.length > 0 && (
						<div className="mb-2">
							<div className="mb-3 flex items-center gap-2">
								<Pin className="h-4 w-4 text-[#1E2761]" />
								<h2 className="text-sm font-semibold uppercase tracking-wider text-[#1E2761]">
									Закріплено
								</h2>
							</div>
							<div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
								{pinned.map((item) => (
									<NewsCard key={item.id} item={item} pinned />
								))}
							</div>
						</div>
					)}
					{regular.length > 0 && (
						<div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
							{regular.map((item) => (
								<NewsCard key={item.id} item={item} />
							))}
						</div>
					)}
				</>
			)}
		</div>
	);
}
