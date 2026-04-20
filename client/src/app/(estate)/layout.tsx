import EstateAuthGate from "@/components/shared/EstateAuthGate";
import BottomNav from "@/components/shared/navbar/BottomNav";
import LeftNavbar from "@/components/shared/navbar/LeftNavbar";
import MobileHeader from "@/components/shared/navbar/MobileHeader";
import Navbar from "@/components/shared/navbar/Navbar";
import RightNavbar from "@/components/shared/navbar/RightNavbar";
import React from "react";

interface LayoutProps {
	children: React.ReactNode;
}

/**
 * Estate (tenant-facing) shell. Phase 1 — mobile-first split:
 *
 *   · < md  (mobile):  MobileHeader (top) + BottomNav (bottom).
 *                      LeftNavbar/RightNavbar/Navbar are hidden.
 *   · ≥ md  (desktop): Existing Navbar + LeftNavbar + RightNavbar.
 *                      MobileHeader + BottomNav are hidden.
 *
 * The responsive switch is done via Tailwind utilities on each nav
 * component (`md:hidden` vs `hidden md:block`) rather than conditional
 * rendering, so the server-rendered markup is identical for every
 * client and we avoid hydration flicker.
 *
 * Content padding:
 *   - Mobile: top 14 (header) + bottom 20 (tab bar + safe-area) = pt-14 pb-20
 *   - Desktop: original pt-24 lg:pt-32 preserved
 */
export default function layout({ children }: LayoutProps) {
	return (
		<main className="relative min-h-screen bg-[#F7F8FA] dark:bg-[#0F1923]">
			{/* Mobile shell */}
			<MobileHeader />

			{/* Desktop shell — kept intact */}
			<div className="hidden md:block">
				<Navbar />
			</div>

			<div className="flex">
				{/* LeftNavbar + RightNavbar are desktop-only. We wrap them in
				    a `hidden md:contents` gate so their own breakpoint classes
				    (`max-sm:hidden`, `max-xl:hidden`) are additive, not
				    overriding — the gate guarantees they never appear below
				    `md`, preventing collision with the mobile shell at the
				    640–767px range. */}
				<div className="hidden md:contents">
					<LeftNavbar />
				</div>
				<section className="flex min-h-screen flex-1 flex-col px-4 pb-20 pt-16 sm:px-6 md:pb-6 md:pt-24 lg:px-8 lg:pt-32">
					<div>
						<EstateAuthGate>{children}</EstateAuthGate>
					</div>
				</section>
				<div className="hidden md:contents">
					<RightNavbar />
				</div>
			</div>

			<BottomNav />
		</main>
	);
}
