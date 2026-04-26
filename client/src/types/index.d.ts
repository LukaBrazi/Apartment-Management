export interface UserState {
	user: {
		searchTerm: string;
		page: number;
	};
}

// ── GDPR consent (PR-5) ──────────────────────────────────────────────────────
export type ConsentType = "tos" | "privacy";

export interface Consent {
	version: string;
	accepted_at: string;
	current: boolean;
}

export interface ConsentMeResponse {
	tos: Consent | null;
	privacy: Consent | null;
	/** Server-side currently configured ToS version. Use this when POSTing /consent/. */
	tos_current_version: string;
	/** Server-side currently configured Privacy version. Use this when POSTing /consent/. */
	privacy_current_version: string;
}

export interface PostState {
	post: {
		page: number;
	};
}

export interface Reply {
	id: string;
	post: number;
	author_username: string;
	avatar: string;
	body: string;
	created_at: string;
	updated_at: string;
}

interface Post {
	id: string;
	title: string;
	slug: string;
	body: string;
	tags: string[];
	author_username: string;
	is_bookmarked: boolean;
	created_at: string;
	updated_at: string;
	view_count: number;
	upvotes: number;
	downvotes: number;
	is_upvoted: boolean;
	replies_count: number;
	avatar: string;
	replies: Reply[];
}

export interface PostsResponse {
	posts: {
		count: number;
		next: null | string;
		previous: null | string;
		results: Post[];
	};
}

export interface MyPostsResponse {
	my_posts: {
		count: number;
		next: null | string;
		previous: null | string;
		results: Post[];
	};
}

export interface PostData {
	title: string;
	tags: string[];
	body: string;
}

export interface BookmarkResponse {
	message: string;
}

export interface UpvoteDownvoteResponse {
	message: string;
}
export interface ReplyData {
	body: string;
}
export interface ReplyPostData extends ReplyData {
	postId: string | undefined;
}
export interface ReplyResponse {
	reply: {
		id: string;
		post: number;
		author_username: string;
		body: string;
		created_at: string;
		updated_at: string;
	};
}
export interface UpdatePostData {
	postSlug: string;
	title: string;
	body: string;
}

export interface PostResponse {
	post: Post;
}

export interface PostsByTagResponse {
	posts_by_tag: {
		count: number;
		next: null | string;
		previous: null | string;
		results: Post[];
	};
}

export interface BookmarkedPostsResponse {
	bookmarked_posts: {
		count: number;
		next: null | string;
		previous: null | string;
		results: Post[];
	};
}
interface TopPost {
	id: string;
	title: string;
	slug: string;
	author_username: string;
	upvotes: number;
	view_count: number;
	replies_count: number;
	avatar: string;
	created_at: string;
}

interface PopularTag {
	name: string;
	slug: string;
	post_count: number;
}

export interface PopularTagResponse {
	popular_tags: {
		count: number;
		next: null | string;
		previous: null | string;
		results: PopularTag[];
	};
}

export interface TopPostsResponse {
	top_posts: {
		count: number;
		next: null | string;
		previous: null | string;
		results: TopPost[];
	};
}
interface Report {
	id: string;
	title: string;
	description: string;
	created_at: string;
}

export interface MyReportsResponse {
	reports: {
		count: number;
		next: null | string;
		previous: null | string;
		results: Report[];
	};
}

export interface ReportTenantData {
	title: string;
	description: string;
	reported_person_name: string;
}

export interface ReportTenantResponse {
	report: Report;
}

export interface Building {
	pkid: number;
	id: string;
	name: string;
	address: string;
	city: string;
	is_active: boolean;
	complex_name?: string;
	created_at: string;
}

export interface BuildingsResponse {
	buildings: Building[];
}

export interface Entrance {
	id: string;
	name: string;
	building: string;
	building_name: string;
}

export interface EntrancesResponse {
	entrances: Entrance[];
}

export interface Unit {
	id: string;
	unit_id: string;
	number: string;
	floor: number | null;
	entrance: string;
	entrance_name: string;
	building_name: string;
}

export interface UnitsResponse {
	units: Unit[];
}

export interface IssueData {
	title: string;
	description: string;
	location_note?: string;
}

/**
 * Issue reporting is Unit-scoped.  The backend resolves the Unit from
 * the user's primary Residency (see PR-11) by default, so no identifier
 * is required in the payload.  ``unitId`` is forwarded only when the
 * reporter is a dispatcher acting on a foreign Unit.
 */
export interface ReportIssueData extends IssueData {
	unitId?: string;
}

export interface Issue {
	id: string;
	unit_number: string | null;
	unit_id: string | null;
	building_name: string | null;
	reported_by: string;
	title: string;
	description: string;
	status: "reported" | "accepted" | "in_progress" | "done" | "rejected";
	priority: "low" | "medium" | "high";
	view_count: number;
	is_overdue: boolean;
	assigned_to?: string;
}

export interface IssueResponse {
	issue: Issue;
}

export interface UpdateIssueResponse {
	issue: {
		title: string;
		description: string;
		unit_number: string | null;
		reported_by: string;
		status: "reported" | "accepted" | "in_progress" | "done" | "rejected";
		resolved_by: string;
		resolved_on: string;
	};
}

export interface IssueStatusData {
	status: string;
}

export interface UpdateIssueData extends IssueStatusData {
	issueId: string;
}
export interface MyIssuesResponse {
	my_issues: {
		count: number;
		next?: string;
		previous?: string;
		results: Issue[];
	};
}

export interface MyAssignedIssuesResponse {
	assigned_issues: {
		count: number;
		next?: string;
		previous?: string;
		results: Issue[];
	};
}

export interface IssueReview {
	id: string;
	issue: string;
	reviewer: number;
	reviewer_name: string;
	reviewee: number;
	reviewee_name: string;
	rating: number;
	comment: string;
	created_at: string;
}

export interface IssueReviewsResponse {
	reviews: IssueReview[];
}

export interface IssueReviewData {
	issueId: string;
	rating: number;
	comment?: string;
}

export interface LeftNavLink {
	path: string;
	label: string;
	imgLocation: string;
}

export interface UserCommonData {
	email: string;
	password: string;
}

export interface User {
	first_name: string;
	last_name: string;
	email: string;
}

export interface UserResponse {
	id: string;
	email: string;
	first_name: string;
	last_name: string;
	username: string;
	slug: string;
	full_name: string;
	gender: string;
	occupation: string;
	phone_number: string;
	country: string;
	city: string;
	reputation: string;
	avatar: string;
	date_joined: string;
}
export interface LoginUserData extends UserCommonData {
	/**
	 * If true, backend extends the refresh cookie lifetime to 14 days
	 * and the session survives browser restarts. Defaults to false
	 * (session cookies, die on browser close).
	 */
	remember_me?: boolean;
}

export interface ResetPasswordConfirmData {
	uid: string;
	token: string;
	new_password: string;
	re_new_password: string;
}
export interface ResetPasswordData {
	email: string;
}

export interface LoginResponse {
	message: string;
}
export interface Profile {
	id: string;
	slug: string;
	first_name: string;
	last_name: string;
	username: string;
	full_name: string;
	gender: "male" | "female" | "other";
	country_of_origin: string;
	city_of_origin: string;
	bio?: string;
	is_staff: boolean;
	// PR-14: gates the super_admin-only ``/admin/telegram-bot`` page.
	// Exposed from ``User.is_superuser``; do not confuse with ``is_staff``
	// which admits directors / admins / staff generally.
	is_superuser: boolean;
	occupation:
		| "mason"
		| "carpenter"
		| "plumber"
		| "roofer"
		| "painter"
		| "electrician"
		| "hvac"
		| "tenant"
		| "owner"
		| "guard";
	reputation: number;
	date_joined: string;
	avatar?: string;
	average_rating: number;
	// Canonical Unit / Building fields — resolved from the user's
	// primary Residency by ``ProfileSerializer``.
	unit_id?: string | null;
	unit_number?: string | null;
	building_name?: string | null;
	building_id?: string | null;
}

export interface ProfilesResponse {
	profiles: {
		count: number;
		next?: string;
		previous?: string;
		results: Profile[];
	};
}
export interface RatingResponse {
	rating: {
		id: string;
		rating: number;
		comment: string;
	};
}
export interface RatingData {
	rated_user_username: string;
	rating: number;
	comment: string;
}
export interface NonTenantResponse {
	non_tenant_profiles: {
		count: number;
		next?: string;
		previous?: string;
		results: Profile[];
	};
}
export interface QueryParams {
	page?: number;
	searchTerm?: string;
}

export interface PostQueryParams {
	page?: number;
}

export interface ProfileResponse {
	profile: Profile;
}

export interface ProfileData {
	first_name: string;
	last_name: string;
	username: string;
	gender: "male" | "female" | "other";
	bio?: string;
	country_of_origin: string;
	city_of_origin: string;
	occupation:
		| "mason"
		| "carpenter"
		| "plumber"
		| "roofer"
		| "painter"
		| "electrician"
		| "hvac"
		| "tenant"
		| "owner"
		| "guard";
	phone_number: string;
}

export type Occupation =
	| "mason"
	| "carpenter"
	| "plumber"
	| "roofer"
	| "painter"
	| "electrician"
	| "hvac"
	| "tenant"
	| "owner"
	| "guard";

export interface ReviewableIssueReview {
	id: string;
	rating: number;
	comment: string;
}

export interface ReviewableIssue {
	id: string;
	title: string;
	assigned_to_name: string;
	assigned_to_username: string;
	resolved_on: string | null;
	created_at: string;
	my_review: ReviewableIssueReview | null;
}

export interface VehiclePass {
	id: string;
	tenant_name: string;
	tenant_username: string;
	unit_label: string | null;
	building_name: string | null;
	car_number: string;
	comment: string;
	visit_date: string;
	status: "pending" | "closed";
	closed_by_username: string | null;
	closed_at: string | null;
	created_at: string;
}

export interface VehiclePassesResponse {
	count: number;
	next: string | null;
	previous: string | null;
	results: VehiclePass[];
}

export interface VehiclePassCreateData {
	car_number?: string;
	comment?: string;
	visit_date: string;
}

export interface VehiclePassCreateResponse {
	id: string;
	car_number: string;
	comment: string;
	visit_date: string;
}

export interface AdminIssueUpdateData {
	issueId: string;
	status?: string;
	priority?: string;
	assigned_to_username?: string | null;
}

export interface Announcement {
	id: string;
	building: string;
	building_name: string;
	title: string;
	body: string;
	is_active: boolean;
	created_at: string;
}

export interface AnnouncementsResponse {
	count: number;
	next: string | null;
	previous: string | null;
	results: Announcement[];
}

export interface AnnouncementCreateData {
	building: string;
	title: string;
	body: string;
	is_active: boolean;
	notify_subscribers?: boolean;
}

export interface AdminIssuesResponse {
	issues: {
		count: number;
		next?: string;
		previous?: string;
		results: Issue[];
	};
}

export interface AdminProfilesResponse {
	profiles: {
		count: number;
		next?: string;
		previous?: string;
		results: Profile[];
	};
}

export interface AdminProfileUpdateData {
	slug: string;
	first_name?: string;
	last_name?: string;
	username?: string;
	gender?: "male" | "female" | "other";
	occupation?: Occupation;
	bio?: string;
	unit_id?: string | null;
}

export interface AdminCreateUserData {
	email: string;
	username: string;
	first_name: string;
	last_name: string;
	password: string;
	occupation: Occupation;
	unit_id?: string | null;
}

export interface BuildingCreateData {
	name: string;
	address: string;
	city: string;
	is_active: boolean;
}

export interface BuildingUpdateData extends Partial<BuildingCreateData> {
	pkid: number;
}

export interface NewsCategory {
	id: string;
	name: string;
	slug: string;
	color: string;
}

export interface NewsItem {
	id: string;
	title: string;
	slug: string;
	excerpt: string;
	body?: string;
	cover_image: string | null;
	category: NewsCategory | null;
	tags: string[];
	author_name: string;
	published_at: string | null;
	is_published: boolean;
	pinned: boolean;
	views_count: number;
	external_url: string;
	created_at: string;
}

export interface NewsResponse {
	status_code: number;
	news: NewsItem[];
	unread_count: number;
}

export interface NewsItemResponse {
	status_code: number;
	news_item: NewsItem;
}

export interface NewsCreateData {
	title: string;
	excerpt: string;
	body: string;
	is_published: boolean;
	pinned: boolean;
	notify_subscribers?: boolean;
	category?: string | null;
	external_url?: string;
	published_at?: string | null;
}

// ── PR-14: multi-tenant Telegram bots (super_admin UI) ───────────────────

export interface OrganizationBot {
	id: string;
	organization: number;
	organization_slug: string;
	organization_name: string;
	bot_username: string;
	// Raw token is write-only.  Read responses only ever include the
	// masked preview (``bot_id:••••••••XYZ``).
	bot_token_masked: string;
	is_configured: boolean;
	is_active: boolean;
	is_primary: boolean;
	webhook_url: string;
	webhook_secret: string;
	last_tested_at: string | null;
	last_test_ok: boolean | null;
	last_test_error: string;
	created_at: string;
	updated_at: string;
}

export interface OrganizationBotListResponse {
	count: number;
	next: string | null;
	previous: string | null;
	results: OrganizationBot[];
}

export interface OrganizationBotCreateData {
	organization: number;
	bot_username: string;
	bot_token?: string;
	is_active?: boolean;
	is_primary?: boolean;
}

export interface OrganizationBotUpdateData {
	bot_username?: string;
	// Leave blank to preserve existing token.
	bot_token?: string;
	is_active?: boolean;
	is_primary?: boolean;
}

export interface OrganizationBotTestResult {
	ok: boolean;
	error: string;
	username: string;
}

/**
 * Minimal org shape returned by the ``/notifications/telegram-bots/organizations/``
 * super_admin helper action — used to populate the "Organization" dropdown
 * when creating a new bot.  ``pkid`` is the autoincrement PK the bot API
 * expects as the FK value; ``id`` is the UUID used everywhere else.
 */
export interface OrganizationSummary {
	pkid: number;
	id: string;
	name: string;
	slug: string;
	is_active: boolean;
}

// ── PR-14: Telegram Profile (user-side linking UI) ────────────────────────

export interface TelegramStatus {
  connected: boolean;
  feature_enabled: boolean;
  bot_configured: boolean;
  // Present only when connected=true:
  chat_id?: number;
  is_active?: boolean;
  notify_issues?: boolean;
  notify_passes?: boolean;
  notify_announcements?: boolean;
  notify_emergency?: boolean;
  notify_visits?: boolean;
  telegram_username?: string | null;
  organization_slug?: string;
  created_at?: string;
}

export interface TelegramGenerateTokenResponse {
  token: string;
  expires_at: string;
  bot_username: string;
  deep_link: string;
  organization_slug: string;
}

export interface TelegramSettingsData {
  notify_issues?: boolean;
  notify_passes?: boolean;
  notify_announcements?: boolean;
  notify_emergency?: boolean;
  notify_visits?: boolean;
}
