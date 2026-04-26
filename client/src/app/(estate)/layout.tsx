import ConsentGate from "@/components/consent/ConsentGate";
import EstateAuthGate from "@/components/shared/EstateAuthGate";
import BottomNav from "@/components/shared/navbar/BottomNav";
import CabinetTopbar from "@/components/shared/navbar/CabinetTopbar";
import LeftNavbar from "@/components/shared/navbar/LeftNavbar";
import MobileHeader from "@/components/shared/navbar/MobileHeader";
import React from "react";

interface LayoutProps {
	children: React.ReactNode;
}

/**
 * Estate (tenant-facing) shell — indigo design system.
 *
 *   · < md  (mobile):  MobileHeader (top) + BottomNav (bottom tabs).
 *                      LeftNavbar is hidden via max-sm:hidden.
 *   · ≥ md  (desktop): LeftNavbar (indigo sidebar, 240px) + CabinetTopbar
 *                      (white 64px top bar) + scrollable content area.
 *                      MobileHeader + BottomNav are hidden.
 */
export default function layout({ children }: LayoutProps) {
	return (
		<main className="relative min-h-screen bg-[#F8FAFC] dark:bg-[#0F1923]">
			{/* Mobile shell */}
			<MobileHeader />

			<div className="flex md:h-screen md:overflow-hidden">
				{/* Desktop sidebar */}
				<div className="hidden md:flex md:flex-shrink-0">
					<LeftNavbar />
				</div>

				{/* Content column */}
				<div className="flex flex-1 flex-col md:overflow-hidden">
					<CabinetTopbar />
					<section className="flex min-h-screen flex-1 flex-col overflow-y-auto px-4 pb-20 pt-16 md:min-h-0 md:p-8 md:pt-6 md:pb-6">
						<EstateAuthGate>
							<ConsentGate>{children}</ConsentGate>
						</EstateAuthGate>
					</section>
				</div>
			</div>

			<BottomNav />
		</main>
	);
}
