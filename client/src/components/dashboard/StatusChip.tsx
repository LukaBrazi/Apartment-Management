import { CheckCircle2 } from "lucide-react";

type IssueStatus = "reported" | "accepted" | "in_progress" | "done" | "rejected";

interface StatusChipProps {
	status: IssueStatus;
}

const CONFIG: Record<IssueStatus, { label: string; classes: string; icon?: boolean }> = {
	reported:    { label: "Подано",    classes: "bg-blue-50 text-blue-600" },
	accepted:    { label: "Прийнято", classes: "bg-indigo-50 text-indigo-600" },
	in_progress: { label: "В роботі", classes: "bg-amber-50 text-amber-600" },
	done:        { label: "Виконано", classes: "bg-green-50 text-green-700", icon: true },
	rejected:    { label: "Відхилено",classes: "bg-red-50 text-red-600" },
};

export default function StatusChip({ status }: StatusChipProps) {
	const cfg = CONFIG[status] ?? { label: status, classes: "bg-gray-50 text-gray-500" };
	return (
		<span className={`inline-flex flex-shrink-0 items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium ${cfg.classes}`}>
			{cfg.icon && <CheckCircle2 className="h-3 w-3 flex-shrink-0" />}
			{cfg.label}
		</span>
	);
}
