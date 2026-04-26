/**
 * RTK Query slice for the super_admin OrganizationBot API (PR-14).
 *
 * All endpoints here hit ``/api/v1/notifications/telegram-bots/...`` and
 * are gated on the server by ``IsSuperAdmin`` — calling them as a
 * non-superuser returns 403.  The frontend additionally hides the
 * menu entry and the whole ``/admin/telegram-bot`` page behind
 * ``profile.is_superuser`` so directors never see the links.
 *
 * The raw ``bot_token`` is write-only: it's only ever sent TO the API,
 * never received FROM it.  Responses carry ``bot_token_masked`` (for
 * display) and ``is_configured`` (green / red status chip).
 */
import {
	OrganizationBot,
	OrganizationBotCreateData,
	OrganizationBotListResponse,
	OrganizationBotTestResult,
	OrganizationBotUpdateData,
	OrganizationSummary,
} from "@/types";
import { baseApiSlice } from "../api/baseApiSlice";

export const telegramBotsApiSlice = baseApiSlice.injectEndpoints({
	endpoints: (builder) => ({
		listTelegramBots: builder.query<OrganizationBotListResponse, void>({
			query: () => "/notifications/telegram-bots/",
			providesTags: ["TelegramBot"],
		}),

		// Flat list of orgs used by the "organization" dropdown when creating
		// a new bot.  Kept on this slice so the whole feature is gated by a
		// single ``TelegramBot`` cache tag + a single super_admin permission.
		listBotOrganizations: builder.query<OrganizationSummary[], void>({
			query: () => "/notifications/telegram-bots/organizations/",
			providesTags: ["TelegramBot"],
		}),

		createTelegramBot: builder.mutation<
			OrganizationBot,
			OrganizationBotCreateData
		>({
			query: (data) => ({
				url: "/notifications/telegram-bots/",
				method: "POST",
				body: data,
			}),
			invalidatesTags: ["TelegramBot"],
		}),

		updateTelegramBot: builder.mutation<
			OrganizationBot,
			{ id: string } & OrganizationBotUpdateData
		>({
			query: ({ id, ...data }) => ({
				url: `/notifications/telegram-bots/${id}/`,
				method: "PATCH",
				body: data,
			}),
			invalidatesTags: ["TelegramBot"],
		}),

		deleteTelegramBot: builder.mutation<void, string>({
			query: (id) => ({
				url: `/notifications/telegram-bots/${id}/`,
				method: "DELETE",
			}),
			invalidatesTags: ["TelegramBot"],
		}),

		// Health / webhook actions — these mutate ``last_test_*`` on the
		// row on success, so we invalidate the cache tag to refresh the UI.
		testTelegramBot: builder.mutation<OrganizationBotTestResult, string>({
			query: (id) => ({
				url: `/notifications/telegram-bots/${id}/test/`,
				method: "POST",
			}),
			invalidatesTags: ["TelegramBot"],
		}),

		setTelegramBotWebhook: builder.mutation<
			{ ok: boolean; webhook_url: string },
			string
		>({
			query: (id) => ({
				url: `/notifications/telegram-bots/${id}/set_webhook/`,
				method: "POST",
			}),
			invalidatesTags: ["TelegramBot"],
		}),

		deleteTelegramBotWebhook: builder.mutation<{ ok: boolean }, string>({
			query: (id) => ({
				url: `/notifications/telegram-bots/${id}/delete_webhook/`,
				method: "POST",
			}),
			invalidatesTags: ["TelegramBot"],
		}),
	}),
});

export const {
	useListTelegramBotsQuery,
	useListBotOrganizationsQuery,
	useCreateTelegramBotMutation,
	useUpdateTelegramBotMutation,
	useDeleteTelegramBotMutation,
	useTestTelegramBotMutation,
	useSetTelegramBotWebhookMutation,
	useDeleteTelegramBotWebhookMutation,
} = telegramBotsApiSlice;
