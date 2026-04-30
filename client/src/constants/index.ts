import { LeftNavLink } from "@/types";

// Import your IssueData interface if it's defined in another file
// import { IssueData } from '@/types';

type OptionType = {
	value: "reported" | "accepted" | "in_progress" | "done" | "rejected" | "low" | "medium" | "high";
	label: string;
};

export const statusOptions: OptionType[] = [
	{ value: "reported", label: "Подано" },
	{ value: "accepted", label: "Прийнято" },
	{ value: "in_progress", label: "В роботі" },
	{ value: "done", label: "Виконано" },
	{ value: "rejected", label: "Відхилено" },
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
	{ value: "owner", label: "Власник" },
	{ value: "guard", label: "Охоронець" },
];

// Options shown to residents (tenant / owner) in the profile edit form.
// Workers and guards have their occupation assigned by admin and cannot change it.
export const residentOccupationOptions = [
	{ value: "tenant", label: "Мешканець" },
	{ value: "owner", label: "Власник" },
];

export const leftNavLinks: LeftNavLink[] = [
	{ path: "/welcome",       label: "Мій будинок",    imgLocation: "/assets/icons/home.svg" },
	{ path: "/profile?tab=my-issues", label: "Мої заявки", imgLocation: "/assets/icons/report.svg" },
	// PR-16: видно тільки worker/staff/dispatcher/guard (не tenant) — gating у `useAuthNavigation`.
	{ path: "/assigned-issues", label: "Призначені заявки", imgLocation: "/assets/icons/report.svg" },
	{ path: "/my-passes",     label: "Мої перепустки",  imgLocation: "/assets/icons/report.svg" },
	{ path: "/payments",      label: "Платежі",        imgLocation: "/assets/icons/bookmark.svg" },
	{ path: "/news",          label: "Новини",         imgLocation: "/assets/icons/speak.svg" },
	{ path: "/contacts",      label: "Контакти",       imgLocation: "/assets/icons/user-profile.svg" },
	{ path: "/profile",       label: "Профіль",        imgLocation: "/assets/icons/user-profile.svg" },
	// Staff/guard only (filtered in useAuthNavigation):
	{ path: "/admin",         label: "Адмін панель",   imgLocation: "/assets/icons/tenants.svg" },
	{ path: "/request-pass",  label: "Створити перепустку", imgLocation: "/assets/icons/report.svg" },
	{ path: "/guard-portal",  label: "Портал охорони", imgLocation: "/assets/icons/tenants.svg" },
	{ path: "/report-issue",  label: "Подати заявку",  imgLocation: "/assets/icons/report.svg" },
];
