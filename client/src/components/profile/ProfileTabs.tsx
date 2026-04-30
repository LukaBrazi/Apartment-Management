"use client";

import { useState, useEffect } from "react";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useAuthNavigation } from "@/hooks";
import About from "@/components/profile/About";
// Posts (форум) тимчасово приховано — фіча повернеться у наступному PR.
// import Posts from "@/components/profile/Posts";
import Issues from "@/components/profile/Issues";
import Reports from "@/components/profile/Reports";
import TelegramSettings from "@/components/profile/TelegramSettings";
import { useGetTelegramStatusQuery } from "@/lib/redux/features/telegram/telegramProfileApiSlice";
import { useSearchParams } from "next/navigation";

// PR-15: канонічний whitelist дозволених `?tab=` значень.  Додавання нового
// табу = додавання в цей масив.  Приходить ?tab=posts (legacy) → fallback
// на "about", щоб сторінка не лишалась з прихованим контентом.
// PR-16: "assigned-issues" винесено у окрему сторінку `/assigned-issues` —
// прибрано з whitelist і з рендеру.
const ALLOWED_TABS = [
	"about",
	"my-issues",
	"my-reports",
	"notifications",
] as const;
type AllowedTab = (typeof ALLOWED_TABS)[number];

function normalizeTab(raw: string | null): AllowedTab {
	if (raw && (ALLOWED_TABS as readonly string[]).includes(raw)) {
		return raw as AllowedTab;
	}
	return "about";
}

export default function ProfileTabs() {
	const { isAuthenticated } = useAuthNavigation();
	const { data: telegramStatus, isLoading: isTelegramLoading } = useGetTelegramStatusQuery(
		undefined,
		{ skip: !isAuthenticated },
	);
	const showNotificationsTab =
		isAuthenticated && (isTelegramLoading || telegramStatus?.feature_enabled === true);
	const searchParams = useSearchParams();
	const tabFromUrl = normalizeTab(searchParams.get("tab"));
	const [activeTab, setActiveTab] = useState<string>(tabFromUrl);

	useEffect(() => {
		setActiveTab(tabFromUrl);
	}, [tabFromUrl]);

	return (
		<div className="w-full">
			<Tabs
				className="rounded-lg border border-[#E5E7EB] dark:border-[#2D3D4F]"
				value={activeTab}
				onValueChange={setActiveTab}
			>
				{/* PR-17 mobile-first: tabs wrap to a 2nd row on narrow
				    viewports instead of horizontal scrolling.  `whitespace-nowrap`
				    on each TabsTrigger keeps the label intact within a tab. */}
				<div>
					<TabsList className="flex flex-wrap gap-1 bg-[#F8FAFC] p-1 md:w-full dark:bg-[#1A2B3C]">
						<TabsTrigger
							value="about"
							className="rounded-xl px-3 py-2 text-sm font-medium whitespace-nowrap
								data-[state=active]:bg-[#1E2761] data-[state=active]:text-white data-[state=active]:shadow-sm
								data-[state=inactive]:bg-transparent data-[state=inactive]:text-[#475569] dark:data-[state=inactive]:text-[#8FA8B8]"
						>
							Про мене
						</TabsTrigger>
						<TabsTrigger
							value="my-issues"
							className="rounded-xl px-3 py-2 text-sm font-medium whitespace-nowrap
								data-[state=active]:bg-[#1E2761] data-[state=active]:text-white data-[state=active]:shadow-sm
								data-[state=inactive]:bg-transparent data-[state=inactive]:text-[#475569] dark:data-[state=inactive]:text-[#8FA8B8]"
						>
							Мої заявки
						</TabsTrigger>
						<TabsTrigger
							value="my-reports"
							className="rounded-xl px-3 py-2 text-sm font-medium whitespace-nowrap
								data-[state=active]:bg-[#1E2761] data-[state=active]:text-white data-[state=active]:shadow-sm
								data-[state=inactive]:bg-transparent data-[state=inactive]:text-[#475569] dark:data-[state=inactive]:text-[#8FA8B8]"
						>
							Мої скарги
						</TabsTrigger>
						{showNotificationsTab && (
							<TabsTrigger
								value="notifications"
								className="rounded-xl px-3 py-2 text-sm font-medium whitespace-nowrap
									data-[state=active]:bg-[#1E2761] data-[state=active]:text-white data-[state=active]:shadow-sm
									data-[state=inactive]:bg-transparent data-[state=inactive]:text-[#475569] dark:data-[state=inactive]:text-[#8FA8B8]"
							>
								Сповіщення
							</TabsTrigger>
						)}
					</TabsList>
				</div>

				<About />
				{/* <Posts /> — приховано до повернення форум-фічі */}
				<Issues />
				<Reports />
				{isAuthenticated && <TelegramSettings />}
			</Tabs>
		</div>
	);
}
