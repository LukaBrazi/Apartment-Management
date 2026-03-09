import { LeftNavLink } from "@/types";

// Import your IssueData interface if it's defined in another file
// import { IssueData } from '@/types';

type OptionType = {
	value: "reported" | "resolved" | "in_progress" | "low" | "medium" | "high";
	label: string;
};

export const statusOptions: OptionType[] = [
	{ value: "reported", label: "Подано" },
	{ value: "resolved", label: "Вирішено" },
	{ value: "in_progress", label: "Виконується" },
];

export const priorityOptions: OptionType[] = [
	{ value: "low", label: "Низький" },
	{ value: "medium", label: "Середній" },
	{ value: "high", label: "Високий" },
];

export const occupationOptions = [
	{ value: "mason", label: "Муляр" },
	{ value: "carpenter", label: "Тесляр" },
	{ value: "plumber", label: "Сантехнік" },
	{ value: "roofer", label: "Покрівельник" },
	{ value: "painter", label: "Маляр" },
	{ value: "electrician", label: "Електрик" },
	{ value: "hvac", label: "Вентиляція/Кондиціювання" },
	{ value: "tenant", label: "Мешканець" },
	{ value: "guard", label: "Охоронець" },
];

export const leftNavLinks: LeftNavLink[] = [
	{
		path: "/welcome",
		label: "Головна",
		imgLocation: "/assets/icons/home.svg",
	},
	{
		// Admin-only: filtered out for non-staff in useAuthNavigation
		path: "/admin",
		label: "Адмін панель",
		imgLocation: "/assets/icons/tenants.svg",
	},
	{
		path: "/profile",
		label: "Профіль",
		imgLocation: "/assets/icons/user-profile.svg",
	},
	{
		path: "/tenants",
		label: "Мешканці",
		imgLocation: "/assets/icons/tenants.svg",
	},
	{
		path: "/technicians",
		label: "Майстри",
		imgLocation: "/assets/icons/technician.svg",
	},
	{
		path: "/report-issue",
		label: "Подати заявку",
		imgLocation: "/assets/icons/report.svg",
	},
	{
		path: "/report-tenant",
		label: "Поскаржитися",
		imgLocation: "/assets/icons/speak.svg",
	},
	{
		path: "/bookmark",
		label: "Збережені публікації",
		imgLocation: "/assets/icons/bookmark.svg",
	},
	{
		// Admin-only: filtered out for tenants/guards in useAuthNavigation
		path: "/add-post",
		label: "Написати новину",
		imgLocation: "/assets/icons/question-file.svg",
	},
	{
		path: "/request-pass",
		label: "Перепустка для авто",
		imgLocation: "/assets/icons/report.svg",
	},
	{
		path: "/guard-portal",
		label: "Портал охорони",
		imgLocation: "/assets/icons/tenants.svg",
	},
];
