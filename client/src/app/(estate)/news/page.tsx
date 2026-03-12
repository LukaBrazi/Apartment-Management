"use client";

import { useGetNewsQuery } from "@/lib/redux/features/news/newsApiSlice";
import Link from "next/link";
import { format } from "date-fns";
import { uk } from "date-fns/locale";
import { Pin, ExternalLink } from "lucide-react";

export default function NewsPage() {
  const { data, isLoading, isError } = useGetNewsQuery();
  const newsList = data?.news ?? [];

  if (isLoading) {
    return (
      <div className="flex flex-col gap-6">
        <h1 className="text-2xl font-bold text-[#111827]">Новини</h1>
        <div className="text-sm text-[#6B7280]">Завантаження...</div>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="flex flex-col gap-6">
        <h1 className="text-2xl font-bold text-[#111827]">Новини</h1>
        <div className="rounded-2xl border border-red-100 bg-red-50 p-6 text-sm text-red-600">
          Не вдалося завантажити новини.
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold text-[#111827]">Новини</h1>
        <p className="text-sm text-[#6B7280] mt-1">Актуальні новини та оновлення порталу</p>
      </div>

      {newsList.length === 0 ? (
        <div className="rounded-2xl border border-[#E5E7EB] bg-white p-8 text-center shadow-sm">
          <p className="text-sm text-[#6B7280]">Новин ще немає.</p>
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {newsList.map((item) => (
            <Link
              key={item.id}
              href={`/news/${item.slug}`}
              className="group rounded-2xl border border-[#E5E7EB] bg-white shadow-sm overflow-hidden hover:shadow-md transition-shadow"
            >
              {item.cover_image && (
                <img
                  src={item.cover_image}
                  alt={item.title}
                  className="w-full h-44 object-cover"
                />
              )}
              <div className="p-4 flex flex-col gap-2">
                <div className="flex items-center gap-2">
                  {item.pinned && (
                    <Pin className="h-3.5 w-3.5 text-[#2F6FED]" />
                  )}
                  {item.category && (
                    <span
                      className="text-xs font-medium px-2 py-0.5 rounded-full"
                      style={{ background: `${item.category.color}20`, color: item.category.color }}
                    >
                      {item.category.name}
                    </span>
                  )}
                </div>
                <h2 className="font-semibold text-[#111827] group-hover:text-[#2F6FED] transition-colors line-clamp-2">
                  {item.title}
                </h2>
                <p className="text-sm text-[#6B7280] line-clamp-3">{item.excerpt}</p>
                <div className="flex items-center justify-between mt-auto pt-2 border-t border-[#F3F4F6]">
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
          ))}
        </div>
      )}
    </div>
  );
}
