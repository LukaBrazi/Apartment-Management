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
					<TabsList className="flex w-max gap-1 bg-[#F8FAFC] p-1 md:w-full dark:bg-[#1A2B3C]">
						<TabsTrigger
							value="about"
							className="rounded-xl px-3 py-2 text-sm font-medium whitespace-nowrap
								data-[state=active]:bg-[#1E2761] data-[state=active]:text-white data-[state=active]:shadow-sm
								data-[state=inactive]:bg-transparent data-[state=inactive]:text-[#475569] dark:data-[state=inactive]:text-[#8FA8B8]"
						>
							Про мене
						</TabsTrigger>
						<TabsTrigger
							value="posts"
							className="rounded-xl px-3 py-2 text-sm font-medium whitespace-nowrap
								data-[state=active]:bg-[#1E2761] data-[state=active]:text-white data-[state=active]:shadow-sm
								data-[state=inactive]:bg-transparent data-[state=inactive]:text-[#475569] dark:data-[state=inactive]:text-[#8FA8B8]"
						>
							Публікації
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
						{isAuthenticated && (
							<TabsTrigger
								value="notifications"
								className="rounded-xl px-3 py-2 text-sm font-medium whitespace-nowrap
									data-[state=active]:bg-[#1E2761] data-[state=active]:text-white data-[state=active]:shadow-sm
									data-[state=inactive]:bg-transparent data-[state=inactive]:text-[#475569] dark:data-[state=inactive]:text-[#8FA8B8]"
							>
								Сповіщення
							</TabsTrigger>
						)}
						{!isTenant && (
							<TabsTrigger
								value="assigned-issues"
								className="rounded-xl px-3 py-2 text-sm font-medium whitespace-nowrap
									data-[state=active]:bg-[#1E2761] data-[state=active]:text-white data-[state=active]:shadow-sm
									data-[state=inactive]:bg-transparent data-[state=inactive]:text-[#475569] dark:data-[state=inactive]:text-[#8FA8B8]"
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
