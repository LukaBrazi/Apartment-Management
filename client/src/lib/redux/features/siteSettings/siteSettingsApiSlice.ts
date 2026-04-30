import { baseApiSlice } from "../api/baseApiSlice";

/**
 * Contact person data from the API.
 */
export interface ContactPerson {
  id: number;
  name: string;
  role: "manager" | "technician" | "guard" | "accountant" | "emergency" | "other";
  role_display: string;
  position?: string;
  phone?: string;
  email?: string;
  telegram?: string;
  photo_url?: string | null;
  is_emergency: boolean;
  working_hours?: string;
  order: number;
}

/**
 * Site settings data from the API.
 */
export interface SiteSettings {
  hero_title: string;
  hero_subtitle: string;
  hero_image_url: string | null;
  cta_text: string;
  cta_url: string;
  platform_name: string;
  platform_tagline: string;
  logo_url?: string;
  favicon_url?: string;
  primary_color: string;
  secondary_color: string;
  display_complex_name: string;
  display_complex_address: string;
  complex_description?: string;
  support_email?: string;
  support_phone?: string;
  support_hours?: string;
  telegram_url?: string;
  viber_url?: string;
  footer_text?: string;
  terms_url?: string;
  privacy_url?: string;
  meta_title?: string;
  meta_description?: string;
  links: Array<{
    id: number;
    label: string;
    url: string;
    order: number;
    open_in_new_tab: boolean;
  }>;
}

/**
 * Response from /api/v1/site-settings/
 */
export interface SiteSettingsResponse {
  settings: SiteSettings;
  contacts: ContactPerson[];
}

/**
 * Admin-side ContactPerson row.  Mirrors ``AdminContactPersonSerializer``
 * on the backend — note ``organization`` is intentionally absent (pinned
 * server-side, see PR-15).
 */
export interface AdminContactPerson extends ContactPerson {
  is_active: boolean;
}

export interface AdminContactCreateData {
  name: string;
  role: AdminContactPerson["role"];
  position?: string;
  phone?: string;
  email?: string;
  telegram?: string;
  is_emergency?: boolean;
  working_hours?: string;
  order?: number;
  is_active?: boolean;
}

export interface AdminContactUpdateData
  extends Partial<AdminContactCreateData> {
  id: number;
}

/**
 * RTK Query endpoints for site settings and contacts.
 */
export const siteSettingsApiSlice = baseApiSlice.injectEndpoints({
  endpoints: (builder) => ({
    /**
     * Fetch public site settings and active contacts.
     * Available to all users (no authentication required).
     */
    getSiteSettings: builder.query<SiteSettingsResponse, void>({
      query: () => "/site-settings/",
      // Support both GenericJSONRenderer-wrapped ({ site_settings: {...} })
      // and direct API response ({ settings, contacts })
      transformResponse: (raw: any): SiteSettingsResponse =>
        raw.site_settings ?? raw,
      providesTags: ["SiteSettings"],
    }),

    // ── PR-15: admin contact CRUD ─────────────────────────────────────────
    getAdminContacts: builder.query<AdminContactPerson[], void>({
      query: () => "/site-settings/contacts/admin/",
      // GenericJSONRenderer wraps the list under "admin_contacts".  Tolerate
      // both that and a bare array so the slice survives a backend renderer
      // tweak without churn.
      transformResponse: (raw: any): AdminContactPerson[] => {
        if (Array.isArray(raw)) return raw;
        if (raw && Array.isArray(raw.admin_contacts)) return raw.admin_contacts;
        if (raw && raw.admin_contacts && Array.isArray(raw.admin_contacts.results)) {
          return raw.admin_contacts.results;
        }
        return [];
      },
      providesTags: ["AdminContacts"],
    }),
    adminCreateContact: builder.mutation<AdminContactPerson, AdminContactCreateData>({
      query: (body) => ({
        url: "/site-settings/contacts/admin/",
        method: "POST",
        body,
      }),
      invalidatesTags: ["AdminContacts", "SiteSettings"],
    }),
    adminUpdateContact: builder.mutation<AdminContactPerson, AdminContactUpdateData>({
      query: ({ id, ...body }) => ({
        url: `/site-settings/contacts/admin/${id}/`,
        method: "PATCH",
        body,
      }),
      invalidatesTags: ["AdminContacts", "SiteSettings"],
    }),
    adminDeleteContact: builder.mutation<void, number>({
      query: (id) => ({
        url: `/site-settings/contacts/admin/${id}/`,
        method: "DELETE",
      }),
      invalidatesTags: ["AdminContacts", "SiteSettings"],
    }),
  }),
});

export const {
  useGetSiteSettingsQuery,
  useGetAdminContactsQuery,
  useAdminCreateContactMutation,
  useAdminUpdateContactMutation,
  useAdminDeleteContactMutation,
} = siteSettingsApiSlice;
