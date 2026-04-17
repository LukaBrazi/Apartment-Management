import {
	IssueResponse,
	MyAssignedIssuesResponse,
	MyIssuesResponse,
	ReportIssueData,
	UpdateIssueData,
	UpdateIssueResponse,
} from "@/types";
import { baseApiSlice } from "../api/baseApiSlice";

export const issueApiSlice = baseApiSlice.injectEndpoints({
	endpoints: (builder) => ({
		reportIssue: builder.mutation<IssueResponse, ReportIssueData>({
			query: ({ apartmentId, ...issueData }) => ({
				url: `/issues/create/${apartmentId}/`,
				method: "POST",
				body: issueData,
			}),
			invalidatesTags: ["Issue"],
		}),
		getAllIssues: builder.query<MyIssuesResponse, void>({
			query: () => "/issues/",
			providesTags: ["Issue"],
		}),
		getMyIssues: builder.query<MyIssuesResponse, void>({
			query: () => "/issues/my-issues/",
			providesTags: ["Issue"],
		}),
		getMyAssignedIssues: builder.query<MyAssignedIssuesResponse, string>({
			query: () => "/issues/assigned/",
			providesTags: ["Issue"],
		}),
		getSingleIssue: builder.query<IssueResponse, string>({
			query: (issueId) => `/issues/${issueId}/`,
			providesTags: ["Issue"],
		}),

		updateIssue: builder.mutation<UpdateIssueResponse, UpdateIssueData>({
			query: ({ issueId, ...statusData }) => ({
				url: `/issues/update/${issueId}/`,
				method: "PATCH",
				body: statusData,
			}),
			invalidatesTags: ["Issue"],
		}),
		deleteIssue: builder.mutation<void, string>({
			query: (issueId) => ({
				url: `/issues/delete/${issueId}/`,
				method: "DELETE",
			}),
			invalidatesTags: ["Issue"],
		}),
	}),
});

export const {
	useReportIssueMutation,
	useDeleteIssueMutation,
	useGetAllIssuesQuery,
	useGetMyIssuesQuery,
	useGetSingleIssueQuery,
	useGetMyAssignedIssuesQuery,
	useUpdateIssueMutation,
} = issueApiSlice;
