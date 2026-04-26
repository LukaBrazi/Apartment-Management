import {
	IssueResponse,
	IssueReviewData,
	IssueReview,
	IssueReviewsResponse,
	MyAssignedIssuesResponse,
	MyIssuesResponse,
	ReportIssueData,
	ReviewableIssue,
	UpdateIssueData,
	UpdateIssueResponse,
} from "@/types";
import { baseApiSlice } from "../api/baseApiSlice";

export const issueApiSlice = baseApiSlice.injectEndpoints({
	endpoints: (builder) => ({
		reportIssue: builder.mutation<IssueResponse, ReportIssueData>({
			// PR-4: default to the Unit on the reporter's profile; when a
			// dispatcher passes ``unitId`` we target that Unit explicitly.
			query: ({ unitId, ...issueData }) => ({
				url: unitId ? `/issues/create/unit/${unitId}/` : "/issues/create/",
				method: "POST",
				body: issueData,
			}),
			invalidatesTags: ["Issue"],
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
		reviewIssue: builder.mutation<IssueReview, IssueReviewData>({
			query: ({ issueId, ...reviewData }) => ({
				url: `/issues/${issueId}/review/`,
				method: "POST",
				body: reviewData,
			}),
			invalidatesTags: ["Issue"],
		}),
		getIssueReviews: builder.query<IssueReviewsResponse, string>({
			query: (issueId) => `/issues/${issueId}/reviews/`,
			providesTags: ["Issue"],
		}),
		getMyReviewableIssues: builder.query<ReviewableIssue[], void>({
			query: () => "/issues/my/reviewable/",
			providesTags: ["Issue"],
		}),
	}),
});

export const {
	useReportIssueMutation,
	useDeleteIssueMutation,
	useGetMyIssuesQuery,
	useGetSingleIssueQuery,
	useGetMyAssignedIssuesQuery,
	useUpdateIssueMutation,
	useReviewIssueMutation,
	useGetIssueReviewsQuery,
	useGetMyReviewableIssuesQuery,
} = issueApiSlice;
