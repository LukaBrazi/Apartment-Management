import { NewsItemResponse, NewsResponse, NewsCreateData } from "@/types";
import { baseApiSlice } from "../api/baseApiSlice";

export const newsApiSlice = baseApiSlice.injectEndpoints({
  endpoints: (builder) => ({
    getNews: builder.query<NewsResponse, void>({
      query: () => "/news/",
      providesTags: ["News"],
    }),

    getNewsItem: builder.query<NewsItemResponse, string>({
      query: (slug) => `/news/${slug}/`,
      providesTags: ["News"],
    }),

    adminGetAllNews: builder.query<NewsResponse, void>({
      query: () => "/news/admin/",
      providesTags: ["News"],
    }),

    adminCreateNews: builder.mutation<NewsItemResponse, NewsCreateData>({
      query: (data) => ({ url: "/news/admin/", method: "POST", body: data }),
      invalidatesTags: ["News"],
    }),

    adminUpdateNews: builder.mutation<NewsItemResponse, { slug: string } & Partial<NewsCreateData>>({
      query: ({ slug, ...data }) => ({ url: `/news/admin/${slug}/`, method: "PATCH", body: data }),
      invalidatesTags: ["News"],
    }),

    adminDeleteNews: builder.mutation<void, string>({
      query: (slug) => ({ url: `/news/admin/${slug}/`, method: "DELETE" }),
      invalidatesTags: ["News"],
    }),
  }),
});

export const {
  useGetNewsQuery,
  useGetNewsItemQuery,
  useAdminGetAllNewsQuery,
  useAdminCreateNewsMutation,
  useAdminUpdateNewsMutation,
  useAdminDeleteNewsMutation,
} = newsApiSlice;
