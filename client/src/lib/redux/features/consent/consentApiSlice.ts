/**
 * RTK Query slice for the GDPR consent endpoints (PR-5).
 *
 *   GET  /api/v1/consent/me/  → useGetMyConsentQuery()
 *   POST /api/v1/consent/     → useAcceptConsentMutation()
 *
 * The "Consent" tag is invalidated on every successful POST so the
 * ConsentGate immediately re-fetches and can dismiss the modal.
 */
import { baseApiSlice } from "@/lib/redux/features/api/baseApiSlice";
import type { ConsentMeResponse, ConsentType } from "@/types";

export const consentApiSlice = baseApiSlice.injectEndpoints({
	endpoints: (builder) => ({
		getMyConsent: builder.query<ConsentMeResponse, void>({
			query: () => ({ url: "/consent/me/", method: "GET" }),
			providesTags: ["Consent"],
		}),
		acceptConsent: builder.mutation<
			void,
			{ consent_type: ConsentType; version: string }
		>({
			query: (body) => ({
				url: "/consent/",
				method: "POST",
				body,
			}),
			invalidatesTags: ["Consent"],
		}),
	}),
});

export const { useGetMyConsentQuery, useAcceptConsentMutation } =
	consentApiSlice;
