"use client";

import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useAuthNavigation } from "@/hooks";
import About from "@/components/profile/About";
import Posts from "@/components/profile/Posts";
import Issues from "@/components/profile/Issues";
import AssignedIssues from "@/components/profile/AssignedIssues";
import Reports from "@/components/profile/Reports";
import { useSearchParams } from "next/navigation";

export default function ProfileTabs() {
	const { isTenant } = useAuthNavigation();
	const searchParams = useSearchParams();
	const defaultTab = searchParams.get("tab") ?? "about";

	return (
		<div className="w-full">
			<Tabs
				className="dark:border-eerieBlack rounded-lg border"
				defaultValue={defaultTab}
			>
				<TabsList className="bg-baby_rich flex space-x-4">
					<TabsTrigger value="about" className="h3-semibold tab">
						Про мене
					</TabsTrigger>
					<TabsTrigger value="posts" className="h3-semibold tab">
						Публікації
					</TabsTrigger>
					<TabsTrigger value="my-issues" className="h3-semibold tab">
						Мої заявки
					</TabsTrigger>
					<TabsTrigger value="my-reports" className="h3-semibold tab">
						Мої скарги
					</TabsTrigger>
					{!isTenant && (
						<TabsTrigger value="assigned-issues" className="h3-semibold tab">
							Призначені заявки
						</TabsTrigger>
					)}
				</TabsList>

				<About />
				<Posts />
				<Issues />
				<Reports />
				{!isTenant && <AssignedIssues />}
			</Tabs>
		</div>
	);
}
