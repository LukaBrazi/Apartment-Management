import { TelegramGenerateTokenResponse, TelegramSettingsData, TelegramStatus } from "@/types";
import { baseApiSlice } from "../api/baseApiSlice";

export const telegramProfileApiSlice = baseApiSlice.injectEndpoints({
  endpoints: (builder) => ({
    getTelegramStatus: builder.query<TelegramStatus, void>({
      query: () => "/notifications/telegram/status/",
      providesTags: ["TelegramProfile"],
    }),
    generateTelegramToken: builder.mutation<TelegramGenerateTokenResponse, void>({
      query: () => ({
        url: "/notifications/telegram/generate-token/",
        method: "POST",
      }),
      // Don't invalidate status here — we poll separately
    }),
    disconnectTelegram: builder.mutation<{ detail: string }, void>({
      query: () => ({
        url: "/notifications/telegram/disconnect/",
        method: "DELETE",
      }),
      invalidatesTags: ["TelegramProfile"],
    }),
    updateTelegramSettings: builder.mutation<TelegramStatus, TelegramSettingsData>({
      query: (data) => ({
        url: "/notifications/telegram/settings/",
        method: "PATCH",
        body: data,
      }),
      invalidatesTags: ["TelegramProfile"],
    }),
  }),
});

export const {
  useGetTelegramStatusQuery,
  useGenerateTelegramTokenMutation,
  useDisconnectTelegramMutation,
  useUpdateTelegramSettingsMutation,
} = telegramProfileApiSlice;
