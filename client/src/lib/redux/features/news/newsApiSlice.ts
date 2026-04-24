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
      // Server marks the item as read on this GET request.
      // Invalidate the list so the sidebar unread_count refreshes.
      async onQueryStarted(_slug, { dispatch, queryFulfilled }) {
        try {
          await queryFulfilled;
          dispatch(newsApiSlice.util.invalidateTags(["News"]));
        } catch {
          // Ignore errors — the list stays stale, badge may be off by 1 until next fetch.
        }
      },
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
