import { BuildingsResponse, EntrancesResponse, UnitsResponse } from "@/types";
import { baseApiSlice } from "../api/baseApiSlice";

/**
 * Building/Entrance/Unit lookups for location pickers.
 *
 * PR-4: the tenant-facing "create apartment" mutation and the
 * "get-my-apartment" reader were removed — Unit membership is
 * admin-managed and canonical Unit data flows via the Profile
 * endpoint.  The remaining queries survive PR-6 because they're
 * used by staff-side forms (location picker, Units-by-Building
 * admin table).
 */
export const apartmentApiSlice = baseApiSlice.injectEndpoints({
	endpoints: (builder) => ({
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
	useGetBuildingsQuery,
	useGetEntrancesQuery,
	useGetUnitsByBuildingQuery,
} = apartmentApiSlice;
