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

  if (isLoading) return <div className="text-sm text-[#6B7280]">Завантаження...</div>;
  if (isError || !item) {
    return (
      <div className="rounded-2xl border border-red-100 bg-red-50 p-6 text-sm text-red-600">
        Новину не знайдено.
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6 max-w-3xl mx-auto">
      <Link href="/news" className="text-sm text-[#2F6FED] hover:underline">
        ← Всі новини
      </Link>

      {item.cover_image && (
        <img
          src={item.cover_image}
          alt={item.title}
          className="w-full rounded-2xl h-64 object-cover"
        />
      )}

      <div className="flex items-center gap-3 flex-wrap">
        {item.pinned && <Pin className="h-4 w-4 text-[#2F6FED]" />}
        {item.category && (
          <span
            className="text-xs font-medium px-2.5 py-1 rounded-full"
            style={{ background: `${item.category.color}20`, color: item.category.color }}
          >
            {item.category.name}
          </span>
        )}
        {item.tags.map((tag) => (
          <span key={tag} className="text-xs bg-[#F3F4F6] text-[#6B7280] px-2 py-0.5 rounded-full">
            #{tag}
          </span>
        ))}
      </div>

      <h1 className="text-3xl font-bold text-[#111827]">{item.title}</h1>

      <div className="flex items-center gap-4 text-xs text-[#9CA3AF]">
        <span>{item.author_name}</span>
        <span>
          {item.published_at
            ? format(new Date(item.published_at), "d MMMM yyyy", { locale: uk })
            : format(new Date(item.created_at), "d MMMM yyyy", { locale: uk })}
        </span>
        <span className="flex items-center gap-1">
          <Eye className="h-3.5 w-3.5" /> {item.views_count}
        </span>
      </div>

      <p className="text-[#374151] italic border-l-4 border-[#2F6FED] pl-4">{item.excerpt}</p>

      <div className="prose prose-sm max-w-none text-[#374151] whitespace-pre-wrap">
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
