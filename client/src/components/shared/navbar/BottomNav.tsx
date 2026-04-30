"use client";

/**
 * Mobile bottom-tab navigation.
 *
 * Rendered ONLY below the `md` breakpoint (handled by the parent
 * layout — see `(estate)/layout.tsx`). Desktop keeps the existing
 * LeftNavbar/RightNavbar stack.
 *
 * Tabs are role-aware:
 *   - tenant  →  Головна · Заявки · Перепустка · Новини · Профіль
 *   - guard   →  Головна · Портал · Перепустки · Новини · Профіль
 *   - staff   →  Головна · Заявки · Перепустки · Новини · Адмін
 *
 * WCAG 2.5.5: every tab is ≥ 44×44 CSS px via the `.tap` utility.
 * Active state uses the `primary.*` token; inactive uses `saas.muted`.
 *
 * The bar is fixed to the viewport bottom and honours
 * `env(safe-area-inset-bottom)` via `.safe-area-pb` so it never lands
 * under the iPhone gesture indicator.
 */

import { useAuthNavigation } from "@/hooks";
import { useGetMyAssignedStatsQuery } from "@/lib/redux/features/issues/issueApiSlice";
import { useAppSelector } from "@/lib/redux/hooks/typedHooks";
import Link from "next/link";
import { usePathname } from "next/navigation";
import React from "react";

type TabItem = {
	/** Pathname to link to. Active-state check is a prefix match. */
	href: string;
	/** Visible label (Ukrainian). */
	label: string;
	/** Optional stricter active-state match — receives the current
	 *  `pathname` and must return true/false. When `undefined` we fall
	 *  back to prefix matching against `href`'s pathname portion. */
	match?: (pathname: string) => boolean;
	icon: React.ReactNode;
	/** Badge counter — non-zero number renders a small red pill over
	 *  the icon. Use for tabs that surface "needs your attention" state
	 *  (e.g. accepted-but-not-started assignments for workers). */
	badge?: number;
};

// ── Icons (inline SVGs to keep this component zero-dep + tree-shakeable) ──
const IconHome = () => (
	<svg className="size-6" viewBox="0 0 24 24" fill="currentColor" aria-hidden>
		<path d="M12 3l9 8h-3v9h-5v-6H11v6H6v-9H3z" />
	</svg>
);
const IconIssue = () => (
	<svg className="size-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" aria-hidden>
		<path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
		<line x1="12" y1="9" x2="12" y2="13" />
		<line x1="12" y1="17" x2="12.01" y2="17" />
	</svg>
);
const IconPass = () => (
	<svg className="size-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" aria-hidden>
		<path d="M14 16H9m10 0h3v-3.15a1 1 0 0 0-.84-.99L16 11l-2.7-3.6a1 1 0 0 0-.8-.4H5.24a2 2 0 0 0-1.8 1.1l-.8 1.63A6 6 0 0 0 2 12.42V15c0 .55.45 1 1 1h2" />
		<circle cx="6.5" cy="16.5" r="2.5" />
		<circle cx="16.5" cy="16.5" r="2.5" />
	</svg>
);
const IconNews = () => (
	<svg className="size-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" aria-hidden>
		<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
	</svg>
);
const IconProfile = () => (
	<svg className="size-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" aria-hidden>
		<circle cx="12" cy="8" r="4" />
		<path d="M4 21a8 8 0 0 1 16 0" />
	</svg>
);
const IconShield = () => (
	<svg className="size-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" aria-hidden>
		<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
	</svg>
);
const IconAdmin = () => (
	<svg className="size-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" aria-hidden>
		<rect x="3" y="3" width="7" height="7" rx="1" />
		<rect x="14" y="3" width="7" height="7" rx="1" />
		<rect x="3" y="14" width="7" height="7" rx="1" />
		<rect x="14" y="14" width="7" height="7" rx="1" />
	</svg>
);

// ── Tab sets per role ──
//
// `/profile?tab=my-issues` is the existing canonical "my issues" route —
// we reuse it for the tenant "Заявки" tab rather than introducing a new
// listing page. That keeps the RTK Query cache + back-button semantics
// identical to what the LeftNavbar already produces.
const TENANT_TABS: TabItem[] = [
	{ href: "/welcome",                   label: "Головна",    icon: <IconHome /> },
	// Active on any sub-route of /profile (including the my-issues tab).
	// If we later introduce a dedicated /issues route we'll split this.
	{ href: "/profile?tab=my-issues",     label: "Заявки",     icon: <IconIssue /> },
	{ href: "/request-pass",              label: "Перепустка", icon: <IconPass /> },
	{ href: "/news",                      label: "Новини",     icon: <IconNews /> },
	{ href: "/profile",                   label: "Профіль",    icon: <IconProfile /> },
];

const GUARD_TABS: TabItem[] = [
	{ href: "/welcome",      label: "Головна",    icon: <IconHome /> },
	{ href: "/guard-portal", label: "Портал",     icon: <IconShield /> },
	{ href: "/request-pass", label: "Перепустки", icon: <IconPass /> },
	{ href: "/news",         label: "Новини",     icon: <IconNews /> },
	{ href: "/profile",      label: "Профіль",    icon: <IconProfile /> },
];

// STAFF (worker / dispatcher) — workers rarely report their own issues,
// they receive assignments. So the second tab is the assignments page
// instead of /profile?tab=my-issues. Badge surfaces accepted-but-not-
// started count from /api/v1/issues/assigned/stats/ (PR-16).
const STAFF_TABS: TabItem[] = [
	{ href: "/welcome",                   label: "Головна",    icon: <IconHome /> },
	{ href: "/assigned-issues",           label: "Призначені", icon: <IconIssue /> },
	{ href: "/request-pass",              label: "Перепустки", icon: <IconPass /> },
	{ href: "/news",                      label: "Новини",     icon: <IconNews /> },
	{ href: "/admin",                     label: "Адмін",      icon: <IconAdmin /> },
];

function pickTabs(opts: {
	isStaff: boolean;
	isGuard: boolean;
	acceptedAssignedCount: number;
}): TabItem[] {
	if (opts.isGuard) return GUARD_TABS;
	if (opts.isStaff) {
		// Inject the accepted-issues badge into the "Призначені" tab.
		return STAFF_TABS.map((t) =>
			t.href === "/assigned-issues"
				? { ...t, badge: opts.acceptedAssignedCount }
				: t,
		);
	}
	return TENANT_TABS;
}

/** Strip `?query` / `#hash` from an href before comparing with `pathname`. */
function hrefPath(href: string): string {
	return href.split(/[?#]/)[0] || "/";
}

export default function BottomNav() {
	const pathname = usePathname() || "/";
	const { isAuthenticated, isStaff, isGuard } = useAuthNavigation();
	const { isAuthenticated: authState } = useAppSelector((state) => state.auth);

	// PR-16: assigned-issues badge (only fetched for staff; tenant gets
	// `accepted: 0` from server but we skip the request entirely to save
	// bandwidth and reduce noise on the read receipts side).
	const { data: assignedStatsData } = useGetMyAssignedStatsQuery(undefined, {
		skip: !authState || !isStaff,
	});
	const acceptedAssignedCount = assignedStatsData?.stats?.accepted ?? 0;

	// Login / auth screens should not show the tab bar — the ProtectedRoute
	// wrapper kicks unauthenticated users to /login anyway, but double-check
	// here so the bar never flashes during redirect.
	if (!isAuthenticated) return null;

	const tabs = pickTabs({ isStaff, isGuard, acceptedAssignedCount });

	return (
		<nav
			aria-label="Мобільна навігація"
			className="fixed inset-x-0 bottom-0 z-40 border-t border-saas-border bg-white/95 backdrop-blur-md safe-area-pb md:hidden dark:border-[#2D3D4F] dark:bg-[#162032]/95"
		>
			<ul className="grid grid-cols-5">
				{tabs.map((tab) => {
					const tabPath = hrefPath(tab.href);
					const isActive = tab.match
						? tab.match(pathname)
						: pathname === tabPath || pathname.startsWith(tabPath + "/");

					return (
						<li key={tab.label}>
							<Link
								href={tab.href}
								aria-current={isActive ? "page" : undefined}
								aria-label={
									tab.badge && tab.badge > 0
										? `${tab.label} (${tab.badge} нових)`
										: tab.label
								}
								className={`tap flex flex-col items-center justify-center gap-1 py-2 transition-colors motion-reduce:transition-none ${
									isActive
										? "text-primary"
										: "text-saas-muted hover:text-saas-text"
								}`}
							>
								<span className="relative inline-flex">
									{tab.icon}
									{tab.badge !== undefined && tab.badge > 0 && (
										<span
											className="absolute -right-2 -top-1 flex h-4 min-w-[16px] items-center justify-center rounded-full bg-red-500 px-1 text-[9px] font-semibold leading-none text-white"
											aria-hidden
										>
											{tab.badge > 99 ? "99+" : tab.badge}
										</span>
									)}
								</span>
								<span className="text-[10px] font-medium leading-none">{tab.label}</span>
							</Link>
						</li>
					);
				})}
			</ul>
		</nav>
	);
}
