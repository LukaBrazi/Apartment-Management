import {
	VehiclePass,
	VehiclePassCreateData,
	VehiclePassCreateResponse,
	VehiclePassesResponse,
} from "@/types";
import { baseApiSlice } from "../api/baseApiSlice";

interface PassListParams {
	visit_date?: string;
	building?: number;
	tenant?: string;
	status?: string;
}

export const passApiSlice = baseApiSlice.injectEndpoints({
	endpoints: (builder) => ({
		createPass: builder.mutation<VehiclePassCreateResponse, VehiclePassCreateData>({
			query: (data) => ({
				url: "/passes/",
				method: "POST",
				body: data,
			}),
			invalidatesTags: ["VehiclePass"],
		}),
		getMyPasses: builder.query<VehiclePassesResponse, void>({
			query: () => "/passes/my/",
			providesTags: ["VehiclePass"],
		}),
		getAllPasses: builder.query<VehiclePassesResponse, PassListParams>({
			query: (params) => ({
				url: "/passes/",
				params,
			}),
			providesTags: ["VehiclePass"],
		}),
		closePass: builder.mutation<VehiclePass, string>({
			query: (passId) => ({
				url: `/passes/${passId}/close/`,
				method: "POST",
			}),
			invalidatesTags: ["VehiclePass"],
		}),
		deletePass: builder.mutation<void, string>({
			query: (passId) => ({
				url: `/passes/${passId}/`,
				method: "DELETE",
			}),
			invalidatesTags: ["VehiclePass"],
		}),
	}),
});

export const {
	useCreatePassMutation,
	useGetMyPassesQuery,
	useGetAllPassesQuery,
	useClosePassMutation,
	useDeletePassMutation,
} = passApiSlice;
