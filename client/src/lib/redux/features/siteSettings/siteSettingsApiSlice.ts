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
      providesTags: ["SiteSettings"],
    }),
  }),
});

export const { useGetSiteSettingsQuery } = siteSettingsApiSlice;
