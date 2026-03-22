import { ApartmentData, ApartmentResponse, BuildingsResponse, EntrancesResponse } from "@/types";
import { baseApiSlice } from "../api/baseApiSlice";

export const apartmentApiSlice = baseApiSlice.injectEndpoints({
	endpoints: (builder) => ({
		createApartment: builder.mutation<ApartmentResponse, ApartmentData>({
			query: (formData) => ({
				url: "/apartments/add/",
				method: "POST",
				body: formData,
			}),
			invalidatesTags: ["Apartment"],
		}),

		getMyApartment: builder.query<ApartmentResponse, void>({
			query: () => "/apartments/my-apartments/",
			providesTags: ["Apartment"],
		}),

		getBuildings: builder.query<BuildingsResponse, void>({
			query: () => "/apartments/buildings/",
			providesTags: ["Apartment"],
		}),

		getEntrances: builder.query<EntrancesResponse, string>({
			query: (buildingId) => `/apartments/buildings/${buildingId}/entrances/`,
			providesTags: ["Apartment"],
		}),
	}),
});

export const {
	useCreateApartmentMutation,
	useGetMyApartmentQuery,
	useGetBuildingsQuery,
	useGetEntrancesQuery,
} = apartmentApiSlice;
