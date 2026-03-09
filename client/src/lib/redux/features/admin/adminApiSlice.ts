import { baseApiSlice } from "../api/baseApiSlice";
import {
	AdminCreateUserData,
	AdminIssueUpdateData,
	AdminIssuesResponse,
	AdminProfilesResponse,
	AdminProfileUpdateData,
	Announcement,
	AnnouncementCreateData,
	AnnouncementsResponse,
	Building,
	BuildingCreateData,
	BuildingUpdateData,
	BuildingsResponse,
	NonTenantResponse,
	Profile,
	ProfileResponse,
	VehiclePass,
	VehiclePassesResponse,
} from "@/types";

export const adminApiSlice = baseApiSlice.injectEndpoints({
	endpoints: (builder) => ({
		// Issues
		getAdminIssues: builder.query<AdminIssuesResponse, void>({
			query: () => "/issues/",
			providesTags: ["Issue"],
		}),
		adminUpdateIssue: builder.mutation<
			{ issue: unknown },
			AdminIssueUpdateData
		>({
			query: ({ issueId, ...body }) => ({
				url: `/issues/admin/update/${issueId}/`,
				method: "PATCH",
				body,
			}),
			invalidatesTags: ["Issue"],
		}),

		// Profiles (admin)
		getAdminAllProfiles: builder.query<AdminProfilesResponse, void>({
			query: () => "/profiles/admin/all/",
			providesTags: ["User"],
		}),
		adminUpdateProfile: builder.mutation<
			ProfileResponse,
			AdminProfileUpdateData
		>({
			query: ({ slug, ...body }) => ({
				url: `/profiles/admin/${slug}/update/`,
				method: "PATCH",
				body,
			}),
			invalidatesTags: ["User"],
		}),

		// Announcements (admin)
		getAdminAnnouncements: builder.query<AnnouncementsResponse, void>({
			query: () => "/posts/announcements/admin/",
			providesTags: ["Announcement"],
		}),
		createAnnouncement: builder.mutation<
			{ announcement: Announcement },
			AnnouncementCreateData
		>({
			query: (body) => ({
				url: "/posts/announcements/admin/",
				method: "POST",
				body,
			}),
			invalidatesTags: ["Announcement"],
		}),
		updateAnnouncement: builder.mutation<
			{ announcement: Announcement },
			{ id: string } & Partial<AnnouncementCreateData>
		>({
			query: ({ id, ...body }) => ({
				url: `/posts/announcements/admin/${id}/`,
				method: "PATCH",
				body,
			}),
			invalidatesTags: ["Announcement"],
		}),
		deleteAnnouncement: builder.mutation<void, string>({
			query: (id) => ({
				url: `/posts/announcements/admin/${id}/`,
				method: "DELETE",
			}),
			invalidatesTags: ["Announcement"],
		}),

		// Passes
		getAdminPasses: builder.query<VehiclePassesResponse, void>({
			query: () => "/passes/",
			providesTags: ["VehiclePass"],
		}),
		closePass: builder.mutation<VehiclePass, string>({
			query: (passId) => ({
				url: `/passes/${passId}/close/`,
				method: "POST",
			}),
			invalidatesTags: ["VehiclePass"],
		}),

		// Workers/technicians
		getAdminWorkers: builder.query<NonTenantResponse, void>({
			query: () => "/profiles/non-tenant-profiles/",
			providesTags: ["User"],
		}),

		// Admin user creation
		adminCreateUser: builder.mutation<{ profile: Profile }, AdminCreateUserData>({
			query: (data) => ({ url: "/profiles/admin/create-user/", method: "POST", body: data }),
			invalidatesTags: ["AdminProfiles", "AdminWorkers"],
		}),

		// Buildings
		adminGetBuildings: builder.query<BuildingsResponse, void>({
			query: () => "/apartments/buildings/admin/",
			providesTags: ["AdminBuildings"],
		}),
		adminCreateBuilding: builder.mutation<{ building: Building }, BuildingCreateData>({
			query: (data) => ({ url: "/apartments/buildings/create/", method: "POST", body: data }),
			invalidatesTags: ["AdminBuildings"],
		}),
		adminUpdateBuilding: builder.mutation<{ building: Building }, BuildingUpdateData>({
			query: ({ pkid, ...data }) => ({ url: `/apartments/buildings/${pkid}/`, method: "PATCH", body: data }),
			invalidatesTags: ["AdminBuildings"],
		}),
		adminDeleteBuilding: builder.mutation<void, number>({
			query: (pkid) => ({ url: `/apartments/buildings/${pkid}/`, method: "DELETE" }),
			invalidatesTags: ["AdminBuildings"],
		}),
	}),
});

export const {
	useGetAdminIssuesQuery,
	useAdminUpdateIssueMutation,
	useGetAdminAllProfilesQuery,
	useAdminUpdateProfileMutation,
	useGetAdminAnnouncementsQuery,
	useCreateAnnouncementMutation,
	useUpdateAnnouncementMutation,
	useDeleteAnnouncementMutation,
	useGetAdminPassesQuery,
	useClosePassMutation,
	useGetAdminWorkersQuery,
	useAdminCreateUserMutation,
	useAdminGetBuildingsQuery,
	useAdminCreateBuildingMutation,
	useAdminUpdateBuildingMutation,
	useAdminDeleteBuildingMutation,
} = adminApiSlice;
