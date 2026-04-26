import { baseApiSlice } from "../api/baseApiSlice";

interface SubmitFeedbackRequest {
	message: string;
}

interface SubmitFeedbackResponse {
	id: string;
	message: string;
	created_at: string;
}

export const feedbackApiSlice = baseApiSlice.injectEndpoints({
	endpoints: (builder) => ({
		submitFeedback: builder.mutation<SubmitFeedbackResponse, SubmitFeedbackRequest>({
			query: (data) => ({
				url: "/feedback/create/",
				method: "POST",
				body: data,
			}),
		}),
	}),
});

export const { useSubmitFeedbackMutation } = feedbackApiSlice;
