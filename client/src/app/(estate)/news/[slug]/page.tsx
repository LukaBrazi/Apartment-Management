"use client";

import { useGetNewsItemQuery } from "@/lib/redux/features/news/newsApiSlice";
import { useParams } from "next/navigation";
import { format } from "date-fns";
import { uk } from "date-fns/locale";
import { ExternalLink, Eye, Pin } from "lucide-react";
import Link from "next/link";

export default function NewsDetailPage() {
	const { slug } = useParams<{ slug: string }>();
	const { data, isLoading, isError } = useGetNewsItemQuery(slug);
	const item = data?.news_item;

	if (isLoading)
		return <div className="text-sm text-[#6B7280]">Завантаження...</div>;
	if (isError || !item) {
		return (
			<div className="rounded-2xl border border-red-100 bg-red-50 p-5 text-sm text-red-600 md:p-6">
				Новину не знайдено.
			</div>
		);
	}

	// Mobile-first article layout: compact hero (192px) on phones, upgrades
	// to 256px at md+. Title drops from text-3xl → text-xl on mobile so the
	// H1 doesn't push content below the fold on 375px viewports.
	return (
		<div className="mx-auto flex max-w-3xl flex-col gap-4 md:gap-6">
			<Link
				href="/news"
				className="text-sm text-[#2F6FED] hover:underline"
			>
				← Всі новини
			</Link>

			{item.cover_image && (
				<img
					src={item.cover_image}
					alt={item.title}
					className="h-48 w-full rounded-2xl object-cover md:h-64"
				/>
			)}

			<div className="flex flex-wrap items-center gap-2 md:gap-3">
				{item.pinned && <Pin className="h-4 w-4 text-[#2F6FED]" />}
				{item.category && (
					<span
						className="rounded-full px-2.5 py-1 text-xs font-medium"
						style={{
							background: `${item.category.color}20`,
							color: item.category.color,
						}}
					>
						{item.category.name}
					</span>
				)}
				{item.tags.map((tag) => (
					<span
						key={tag}
						className="rounded-full bg-[#F3F4F6] px-2 py-0.5 text-xs text-[#6B7280] dark:bg-[#1E2D3D] dark:text-[#A0B3C1]"
					>
						#{tag}
					</span>
				))}
			</div>

			<h1 className="text-xl font-bold text-[#111827] md:text-3xl dark:text-[#F0EDE6]">
				{item.title}
			</h1>

			<div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-[#9CA3AF]">
				<span>{item.author_name}</span>
				<span>
					{item.published_at
						? format(new Date(item.published_at), "d MMMM yyyy", {
								locale: uk,
							})
						: format(new Date(item.created_at), "d MMMM yyyy", {
								locale: uk,
							})}
				</span>
				<span className="flex items-center gap-1">
					<Eye className="h-3.5 w-3.5" /> {item.views_count}
				</span>
			</div>

			<p className="border-l-4 border-[#2F6FED] pl-4 text-sm italic text-[#374151] md:text-base dark:text-[#A0B3C1]">
				{item.excerpt}
			</p>

			<div className="prose prose-sm max-w-none whitespace-pre-wrap text-sm text-[#374151] md:text-base dark:text-[#A0B3C1]">
				{item.body}
			</div>

			{item.external_url && (
				<a
					href={item.external_url}
					target="_blank"
					rel="noopener noreferrer"
					className="flex items-center gap-2 text-sm text-[#2F6FED] hover:underline"
				>
					<ExternalLink className="h-4 w-4" /> Джерело
				</a>
			)}
		</div>
	);
}
