"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { ColumnDef } from "@tanstack/react-table";
import { toast } from "react-toastify";
import { format } from "date-fns";
import { Plus, Pencil, Trash2, Pin } from "lucide-react";
import { DataTable } from "@/components/admin/DataTable";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  useAdminGetAllNewsQuery,
  useAdminCreateNewsMutation,
  useAdminUpdateNewsMutation,
  useAdminDeleteNewsMutation,
} from "@/lib/redux/features/news/newsApiSlice";
import { NewsItem } from "@/types";

const newsSchema = z.object({
  title: z.string().min(1, "Вкажіть заголовок"),
  excerpt: z.string().min(1, "Вкажіть короткий опис"),
  body: z.string().min(1, "Вкажіть текст новини"),
  is_published: z.boolean(),
  pinned: z.boolean(),
  notify_subscribers: z.boolean(),
  external_url: z.string().url("Невалідний URL").or(z.literal("")),
});

type NewsFormData = z.infer<typeof newsSchema>;

const emptyForm: NewsFormData = {
  title: "",
  excerpt: "",
  body: "",
  is_published: false,
  pinned: false,
  notify_subscribers: false,
  external_url: "",
};

export default function AdminNewsPage() {
  const { data, isLoading } = useAdminGetAllNewsQuery();
  const [createNews] = useAdminCreateNewsMutation();
  const [updateNews] = useAdminUpdateNewsMutation();
  const [deleteNews] = useAdminDeleteNewsMutation();

  const [showForm, setShowForm] = useState(false);
  const [editingSlug, setEditingSlug] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<NewsFormData>({
    resolver: zodResolver(newsSchema),
    defaultValues: emptyForm,
  });

  const newsList = data?.news ?? [];

  const onSubmit = async (values: NewsFormData) => {
    try {
      if (editingSlug) {
        await updateNews({ slug: editingSlug, ...values }).unwrap();
        toast.success("Новину оновлено");
      } else {
        await createNews(values).unwrap();
        toast.success("Новину створено");
      }
      reset(emptyForm);
      setShowForm(false);
      setEditingSlug(null);
    } catch {
      toast.error("Помилка збереження");
    }
  };

  const handleEdit = (item: NewsItem) => {
    reset({
      title: item.title,
      excerpt: item.excerpt,
      body: item.body ?? "",
      is_published: item.is_published,
      pinned: item.pinned,
      notify_subscribers: false, // reset on edit — don't re-send notifications
      external_url: item.external_url,
    });
    setEditingSlug(item.slug);
    setShowForm(true);
  };

  const handleDelete = async (slug: string) => {
    if (!confirm("Видалити новину?")) return;
    try {
      await deleteNews(slug).unwrap();
      toast.success("Новину видалено");
    } catch {
      toast.error("Помилка видалення");
    }
  };

  const columns: ColumnDef<NewsItem>[] = [
    {
      accessorKey: "title",
      header: "Заголовок",
      cell: ({ row }) => (
        <div className="flex items-center gap-2">
          {row.original.pinned && (
            <Pin className="h-3.5 w-3.5 text-[#2F6FED]" />
          )}
          <span className="font-medium text-sm">{row.original.title}</span>
        </div>
      ),
    },
    {
      accessorKey: "is_published",
      header: "Статус",
      cell: ({ row }) => (
        <span
          className={`text-xs px-2 py-0.5 rounded-full font-medium ${
            row.original.is_published
              ? "bg-green-100 text-green-700"
              : "bg-yellow-100 text-yellow-700"
          }`}
        >
          {row.original.is_published ? "Опубліковано" : "Чернетка"}
        </span>
      ),
    },
    {
      accessorKey: "views_count",
      header: "Перегляди",
      cell: ({ row }) => (
        <span className="text-sm text-[#6B7280]">
          {row.original.views_count}
        </span>
      ),
    },
    {
      accessorKey: "created_at",
      header: "Дата",
      cell: ({ row }) => (
        <span className="text-sm text-[#6B7280]">
          {format(new Date(row.original.created_at), "dd.MM.yyyy")}
        </span>
      ),
    },
    {
      id: "actions",
      header: "Дії",
      cell: ({ row }) => (
        <div className="flex gap-2">
          <Button
            size="sm"
            variant="outline"
            onClick={() => handleEdit(row.original)}
          >
            <Pencil className="h-3.5 w-3.5" />
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={() => handleDelete(row.original.slug)}
            className="text-red-500 hover:text-red-700"
          >
            <Trash2 className="h-3.5 w-3.5" />
          </Button>
        </div>
      ),
    },
  ];

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-[#111827]">Новини порталу</h1>
        <Button
          onClick={() => {
            setShowForm(!showForm);
            setEditingSlug(null);
            reset(emptyForm);
          }}
        >
          <Plus className="h-4 w-4 mr-2" />
          {showForm ? "Скасувати" : "Нова новина"}
        </Button>
      </div>

      {showForm && (
        <form
          onSubmit={handleSubmit(onSubmit)}
          className="rounded-2xl border border-[#E5E7EB] bg-white p-6 flex flex-col gap-4 shadow-sm"
        >
          <h2 className="font-semibold text-[#111827]">
            {editingSlug ? "Редагувати" : "Нова новина"}
          </h2>
          <div>
            <Input placeholder="Заголовок" {...register("title")} />
            {errors.title && (
              <p className="text-xs text-red-500 mt-1">
                {errors.title.message}
              </p>
            )}
          </div>
          <div>
            <Textarea
              placeholder="Короткий опис (для картки)"
              rows={2}
              {...register("excerpt")}
            />
            {errors.excerpt && (
              <p className="text-xs text-red-500 mt-1">
                {errors.excerpt.message}
              </p>
            )}
          </div>
          <div>
            <Textarea
              placeholder="Повний текст новини"
              rows={6}
              {...register("body")}
            />
            {errors.body && (
              <p className="text-xs text-red-500 mt-1">
                {errors.body.message}
              </p>
            )}
          </div>
          <Input
            placeholder="Посилання на джерело (необов'язково)"
            {...register("external_url")}
          />
          <div className="flex flex-wrap gap-6">
            <label className="flex items-center gap-2 text-sm cursor-pointer">
              <input
                type="checkbox"
                {...register("is_published")}
                className="rounded"
              />
              Опублікувати
            </label>
            <label className="flex items-center gap-2 text-sm cursor-pointer">
              <input
                type="checkbox"
                {...register("pinned")}
                className="rounded"
              />
              Закріпити
            </label>
            <label className="flex items-center gap-2 text-sm cursor-pointer">
              <input
                type="checkbox"
                {...register("notify_subscribers")}
                className="rounded"
              />
              <span className="flex items-center gap-1">
                Сповістити підписників у Telegram
              </span>
            </label>
          </div>
          <Button type="submit" className="self-start">
            {editingSlug ? "Зберегти зміни" : "Створити новину"}
          </Button>
        </form>
      )}

      <DataTable columns={columns} data={newsList} isLoading={isLoading} />
    </div>
  );
}
