"use client";

import AdminGuard from "./AdminGuard";
import AdminResidents from "./AdminResidents";
import AdminWorkers from "./AdminWorkers";
import AdminIssues from "./AdminIssues";
import AdminPasses from "./AdminPasses";
import AdminPosts from "./AdminPosts";
import { useState } from "react";
import {
	Users,
	Wrench,
	ClipboardList,
	Car,
	Megaphone,
	LayoutDashboard,
} from "lucide-react";

const tabs = [
	{ id: "residents", label: "Мешканці", icon: Users },
	{ id: "workers", label: "Майстри", icon: Wrench },
	{ id: "issues", label: "Заявки", icon: ClipboardList },
	{ id: "passes", label: "Пропуски", icon: Car },
	{ id: "posts", label: "Новини", icon: Megaphone },
] as const;

type TabId = (typeof tabs)[number]["id"];

export default function AdminDashboard() {
	const [activeTab, setActiveTab] = useState<TabId>("issues");

	return (
		<AdminGuard>
			<div className="space-y-6">
				{/* Header */}
				<div className="flex items-center gap-3">
					<div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[#3D7A8A] text-white dark:bg-[#5BA3B5]">
						<LayoutDashboard className="h-5 w-5" />
					</div>
					<div>
						<h1 className="text-xl font-bold text-[#1C2B3A] dark:text-white">
							Адмін панель
						</h1>
						<p className="text-sm text-[#6B7F8C] dark:text-[#8FA8B8]">
							Управління мешканцями, заявками та публікаціями
						</p>
					</div>
				</div>

				{/* Tab Nav */}
				<div className="flex flex-wrap gap-1 rounded-xl border border-[#E2E5E8] bg-white p-1 dark:border-[#2D3D4F] dark:bg-[#162032]">
					{tabs.map((tab) => {
						const Icon = tab.icon;
						const isActive = activeTab === tab.id;
						return (
							<button
								key={tab.id}
								onClick={() => setActiveTab(tab.id)}
								className={`flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-all ${
									isActive
										? "bg-[#3D7A8A] text-white dark:bg-[#5BA3B5]"
										: "text-[#6B7F8C] hover:bg-[#F7F6F2] hover:text-[#1C2B3A] dark:text-[#8FA8B8] dark:hover:bg-[#1E2D3D] dark:hover:text-white"
								}`}
							>
								<Icon className="h-4 w-4" />
								<span className="hidden sm:inline">{tab.label}</span>
							</button>
						);
					})}
				</div>

				{/* Tab Content */}
				<div>
					{activeTab === "residents" && <AdminResidents />}
					{activeTab === "workers" && <AdminWorkers />}
					{activeTab === "issues" && <AdminIssues />}
					{activeTab === "passes" && <AdminPasses />}
					{activeTab === "posts" && <AdminPosts />}
				</div>
			</div>
		</AdminGuard>
	);
}
