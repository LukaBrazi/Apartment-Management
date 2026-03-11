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
	{ path: "/welcome",       label: "Мій будинок",    imgLocation: "/assets/icons/home.svg" },
	{ path: "/profile",       label: "Мої заявки",     imgLocation: "/assets/icons/report.svg" },
	{ path: "/payments",      label: "Платежі",        imgLocation: "/assets/icons/bookmark.svg" },
	{ path: "/announcements", label: "Оголошення",     imgLocation: "/assets/icons/speak.svg" },
	{ path: "/contacts",      label: "Контакти",       imgLocation: "/assets/icons/user-profile.svg" },
	// Staff/guard only (filtered in useAuthNavigation):
	{ path: "/admin",         label: "Адмін панель",   imgLocation: "/assets/icons/tenants.svg" },
	{ path: "/request-pass",  label: "Перепустка",     imgLocation: "/assets/icons/report.svg" },
	{ path: "/guard-portal",  label: "Портал охорони", imgLocation: "/assets/icons/tenants.svg" },
	{ path: "/report-issue",  label: "Подати заявку",  imgLocation: "/assets/icons/report.svg" },
];
