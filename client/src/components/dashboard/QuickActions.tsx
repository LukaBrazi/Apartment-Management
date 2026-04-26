import Link from "next/link";
import { Plus, Car, AlertTriangle, Star } from "lucide-react";

/**
 * Dashboard quick-action shortcuts.
 *
 * Mobile-first layout (Phase 2, PR feat/mobile-first-app-shell):
 *   < md: 2x2 grid — every action visible, no horizontal scroll.
 *         Each card is full-height with icon+title+subtitle, so users
 *         actually understand the action before tapping it.
 *   ≥ md: Horizontal row (the pre-existing desktop layout), using
 *         overflow-x-auto as a defensive fallback if the 4 CTAs ever
 *         expand past the container width.
 *
 * The mobile grid fixes the bug flagged by the Developer-agent review:
 * previously `overflow-x-auto` on a 360px viewport hid "Подати скаргу"
 * and "Оцінити майстра" behind a horizontal scroll that most tenants
 * never discovered.
 */

type Action = {
	href: string;
	label: string;
	subtitle: string;
	icon: React.ReactNode;
	variant: "primary" | "warning" | "success" | "neutral";
};

const ACTIONS: Action[] = [
	{
		href: "/report-issue",
		label: "Нова заявка",
		subtitle: "Повідомити про проблему",
		icon: <Plus className="h-5 w-5" />,
		variant: "primary",
	},
	{
		href: "/request-pass",
		label: "Перепустка",
		subtitle: "Запросити гостя",
		icon: <Car className="h-5 w-5" />,
		variant: "warning",
	},
	{
		href: "/report-tenant",
		label: "Скарга",
		subtitle: "На сусіда",
		icon: <AlertTriangle className="h-5 w-5" />,
		variant: "neutral",
	},
	{
		href: "/rate-worker",
		label: "Оцінити",
		subtitle: "Роботу майстра",
		icon: <Star className="h-5 w-5" />,
		variant: "success",
	},
];

const VARIANT_ICON_BG: Record<Action["variant"], string> = {
	primary: "bg-[#EEF3FD] text-[#2F6FED]",
	warning: "bg-[#FEF9EE] text-[#D6A14A]",
	success: "bg-[#EDFAF6] text-[#2E7D6B]",
	neutral: "bg-[#F3F4F6] text-[#6B7280]",
};

// Desktop row button styling, kept identical to the previous design
// so the md+ viewport sees no visual change.
const DESKTOP_BTN_PRIMARY =
	"flex items-center gap-2 whitespace-nowrap rounded-xl bg-[#2F6FED] px-4 py-2.5 text-sm font-medium text-white shadow-sm hover:bg-[#2460d4] transition-colors flex-shrink-0";
const DESKTOP_BTN_SECONDARY =
	"flex items-center gap-2 whitespace-nowrap rounded-xl border border-[#E5E7EB] bg-white px-4 py-2.5 text-sm font-medium text-[#374151] hover:bg-[#F7F8FA] transition-colors flex-shrink-0 dark:border-[#2D3D4F] dark:bg-[#162032] dark:text-[#D1D5DB] dark:hover:bg-[#1E2D3D]";

export default function QuickActions() {
	return (
		<>
			{/* Mobile: 2x2 grid. Each cell is full card with icon + copy,
			    ≥ 88px tall to comfortably clear 44x44 tap targets plus
			    two lines of text. */}
			<div className="grid grid-cols-2 gap-3 md:hidden">
				{ACTIONS.map((a) => (
					<Link
						key={a.href}
						href={a.href}
						className="tap flex flex-col gap-2 rounded-2xl border border-[#E5E7EB] bg-white p-4 shadow-sm transition-colors hover:bg-[#F7F8FA] dark:border-[#2D3D4F] dark:bg-[#162032] dark:hover:bg-[#1E2D3D]"
					>
						<div className={`flex h-10 w-10 items-center justify-center rounded-xl ${VARIANT_ICON_BG[a.variant]}`}>
							{a.icon}
						</div>
						<div className="min-w-0">
							<div className="text-sm font-semibold text-[#111827] dark:text-[#F0EDE6]">{a.label}</div>
							<div className="truncate text-xs text-[#6B7280] dark:text-[#8FA8B8]">{a.subtitle}</div>
						</div>
					</Link>
				))}
			</div>

			{/* Desktop: horizontal row, preserved from the original
			    component so no existing screenshot regresses. */}
			<div className="hidden md:flex md:items-center md:gap-3 md:overflow-x-auto md:pb-1 [&::-webkit-scrollbar]:hidden [-ms-overflow-style:none] [scrollbar-width:none]">
				<Link href="/report-issue" className={DESKTOP_BTN_PRIMARY}>
					<Plus className="h-4 w-4" />
					Нова заявка
				</Link>
				<Link href="/request-pass" className={DESKTOP_BTN_SECONDARY}>
					<Car className="h-4 w-4" />
					Запросити гостя
				</Link>
				<Link href="/report-tenant" className={DESKTOP_BTN_SECONDARY}>
					<AlertTriangle className="h-4 w-4" />
					Подати скаргу
				</Link>
				<Link href="/rate-worker" className={DESKTOP_BTN_SECONDARY}>
					<Star className="h-4 w-4" />
					Оцінити майстра
				</Link>
			</div>
		</>
	);
}
