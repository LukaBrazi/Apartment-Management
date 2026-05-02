import {
	MyReportsResponse,
	ReportTenantData,
	ReportTenantResponse,
} from "@/types";
import { baseApiSlice } from "../api/baseApiSlice";

export const reportApiSlice = baseApiSlice.injectEndpoints({
	endpoints: (builder) => ({
		reportTenant: builder.mutation<ReportTenantResponse, ReportTenantData>({
			query: (reportData) => ({
				url: "/reports/create/",
				method: "POST",
				body: reportData,
			}),
			invalidatesTags: ["Report"],
		}),

		getMyReports: builder.query<MyReportsResponse, void>({
			// Backend route is `/reports/my-reports/` (apps/reports/urls.py).
			// Earlier `/reports/me/` returned 404 → empty list after a
			// successful create — exactly the reported "скарга створена,
			// але у списку нема" symptom.
			query: () => "/reports/my-reports/",
			providesTags: ["Report"],
		}),
	}),
});

export const { useReportTenantMutation, useGetMyReportsQuery } = reportApiSlice;
