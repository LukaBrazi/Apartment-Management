import { differenceInDays } from "date-fns";

interface SlaChipProps {
	slaDeadline?: string | null;
}

export default function SlaChip({ slaDeadline }: SlaChipProps) {
	if (!slaDeadline) return null;

	const daysLeft = differenceInDays(new Date(slaDeadline), new Date());

	if (daysLeft > 2) {
		return (
			<span className="flex-shrink-0 rounded-full bg-[#EDFAF6] px-2 py-0.5 text-xs font-medium text-[#2E7D6B]">
				SLA: {daysLeft}д
			</span>
		);
	}

	if (daysLeft >= 0) {
		return (
			<span className="flex-shrink-0 rounded-full bg-[#FEF9EE] px-2 py-0.5 text-xs font-medium text-[#D6A14A]">
				SLA: {daysLeft}д
			</span>
		);
	}

	return (
		<span className="flex-shrink-0 rounded-full bg-[#FEF2F2] px-2 py-0.5 text-xs font-medium text-[#C0392B]">
			Прострочено
		</span>
	);
}
