"use client";

import { useState, useEffect } from "react";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useAuthNavigation } from "@/hooks";
import About from "@/components/profile/About";
import Posts from "@/components/profile/Posts";
import Issues from "@/components/profile/Issues";
import AssignedIssues from "@/components/profile/AssignedIssues";
import Reports from "@/components/profile/Reports";
import TelegramSettings from "@/components/profile/TelegramSettings";
import { useSearchParams } from "next/navigation";

export default function ProfileTabs() {
	const { isTenant, isAuthenticated } = useAuthNavigation();
	const searchParams = useSearchParams();
	const tabFromUrl = searchParams.get("tab") ?? "about";
	const [activeTab, setActiveTab] = useState(tabFromUrl);

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
				{/* Mobile-first: horizontal scroll when 4-5 Ukrainian tab labels
				    overflow a 375px viewport. `-webkit-overflow-scrolling:touch`
				    is handled by modern mobile browsers by default. Desktop
				    keeps the space-x-4 flex layout, no scroll needed. */}
				<div className="overflow-x-auto scrollbar-none">
					<TabsList className="bg-baby_rich flex w-max gap-2 px-2 md:w-full md:space-x-4 md:gap-0 md:px-0">
						<TabsTrigger
							value="about"
							className="h3-semibold tab whitespace-nowrap"
						>
							Про мене
						</TabsTrigger>
						<TabsTrigger
							value="posts"
							className="h3-semibold tab whitespace-nowrap"
						>
							Публікації
						</TabsTrigger>
						<TabsTrigger
							value="my-issues"
							className="h3-semibold tab whitespace-nowrap"
						>
							Мої заявки
						</TabsTrigger>
						<TabsTrigger
							value="my-reports"
							className="h3-semibold tab whitespace-nowrap"
						>
							Мої скарги
						</TabsTrigger>
						{isAuthenticated && (
							<TabsTrigger
								value="notifications"
								className="h3-semibold tab whitespace-nowrap"
							>
								Сповіщення
							</TabsTrigger>
						)}
						{!isTenant && (
							<TabsTrigger
								value="assigned-issues"
								className="h3-semibold tab whitespace-nowrap"
							>
								Призначені заявки
							</TabsTrigger>
						)}
					</TabsList>
				</div>

				<About />
				<Posts />
				<Issues />
				<Reports />
				{isAuthenticated && <TelegramSettings />}
				{!isTenant && <AssignedIssues />}
			</Tabs>
		</div>
	);
}
