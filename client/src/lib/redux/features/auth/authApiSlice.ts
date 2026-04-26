import { baseApiSlice } from "@/lib/redux/features/api/baseApiSlice";
import {
	LoginResponse,
	LoginUserData,
	ResetPasswordConfirmData,
	ResetPasswordData,
} from "@/types";

export const authApiSlice = baseApiSlice.injectEndpoints({
	endpoints: (builder) => ({
		loginUser: builder.mutation<LoginResponse, LoginUserData>({
			query: (credentials) => ({
				url: "/auth/login/",
				method: "POST",
				body: credentials,
			}),
		}),
		resetPasswordRequest: builder.mutation<void, ResetPasswordData>({
			query: (formData) => ({
				url: "/auth/users/reset_password/",
				method: "POST",
				body: formData,
			}),
		}),
		resetPasswordConfirm: builder.mutation<void, ResetPasswordConfirmData>({
			query: (formData) => ({
				url: "/auth/users/reset_password_confirm/",
				method: "POST",
				body: formData,
			}),
		}),
		logoutUser: builder.mutation<void, void>({
			query: () => ({
				url: "/auth/logout/",
				method: "POST",
			}),
		}),
	}),
});

export const {
	useLoginUserMutation,
	useLogoutUserMutation,
	useResetPasswordConfirmMutation,
	useResetPasswordRequestMutation,
} = authApiSlice;
