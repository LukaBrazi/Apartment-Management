"use client";

interface StatusBadgeProps {
	value: string;
	type?: "status" | "priority";
}

const statusConfig: Record<string, { label: string; classes: string }> = {
	reported: {
		label: "Подано",
		classes:
			"bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300",
	},
	accepted: {
		label: "Прийнято",
		classes:
			"bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-300",
	},
	in_progress: {
		label: "В роботі",
		classes:
			"bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300",
	},
	done: {
		label: "Виконано",
		classes:
			"bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300",
	},
	rejected: {
		label: "Відхилено",
		classes: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300",
	},
	// Pass statuses
	pending: {
		label: "Очікує",
		classes:
			"bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300",
	},
	closed: {
		label: "Закрито",
		classes:
			"bg-slate-100 text-slate-600 dark:bg-slate-800/40 dark:text-slate-400",
	},
};

const priorityConfig: Record<string, { label: string; classes: string }> = {
	low: {
		label: "Низький",
		classes:
			"bg-slate-100 text-slate-600 dark:bg-slate-800/40 dark:text-slate-400",
	},
	medium: {
		label: "Середній",
		classes:
			"bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300",
	},
	high: {
		label: "Високий",
		classes: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300",
	},
};

export default function StatusBadge({ value, type = "status" }: StatusBadgeProps) {
	const config =
		type === "priority"
			? priorityConfig[value]
			: statusConfig[value];

	if (!config) {
		return (
			<span className="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium bg-slate-100 text-slate-600 dark:bg-slate-800/40 dark:text-slate-400">
				{value}
			</span>
		);
	}

	return (
		<span
			className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${config.classes}`}
		>
			{config.label}
		</span>
	);
}
