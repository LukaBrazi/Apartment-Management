import { ApartmentData, ApartmentResponse, BuildingsResponse, EntrancesResponse, UnitsResponse } from "@/types";
import { baseApiSlice } from "../api/baseApiSlice";

export const apartmentApiSlice = baseApiSlice.injectEndpoints({
	endpoints: (builder) => ({
		createApartment: builder.mutation<ApartmentResponse, ApartmentData>({
			query: (formData) => ({
				url: "/apartments/add/",
				method: "POST",
				body: formData,
			}),
			invalidatesTags: ["Apartment", "User"],
		}),

		getMyApartment: builder.query<ApartmentResponse, void>({
			query: () => "/apartments/my-apartment/",
			// Backend returns { apartment: {...} } (singular object).
			transformResponse: (response: any): ApartmentResponse => {
				return { apartment: response?.apartment ?? null };
			},
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

		getUnitsByBuilding: builder.query<UnitsResponse, string>({
			query: (buildingId) => `/apartments/buildings/${buildingId}/units/`,
			providesTags: ["Apartment"],
		}),
	}),
});

export const {
	useCreateApartmentMutation,
	useGetMyApartmentQuery,
	useGetBuildingsQuery,
	useGetEntrancesQuery,
	useGetUnitsByBuildingQuery,
} = apartmentApiSlice;
