import Link from "next/link";
import { Plus, Car, AlertTriangle, Star } from "lucide-react";

const PRIMARY_BTN =
	"flex items-center gap-2 whitespace-nowrap rounded-xl bg-[#2F6FED] px-4 py-2.5 text-sm font-medium text-white shadow-sm hover:bg-[#2460d4] transition-colors flex-shrink-0";

const SECONDARY_BTN =
	"flex items-center gap-2 whitespace-nowrap rounded-xl border border-[#E5E7EB] bg-white px-4 py-2.5 text-sm font-medium text-[#374151] hover:bg-[#F7F8FA] transition-colors flex-shrink-0 dark:border-[#2D3D4F] dark:bg-[#162032] dark:text-[#D1D5DB] dark:hover:bg-[#1E2D3D]";

export default function QuickActions() {
	return (
		<div className="flex items-center gap-3 overflow-x-auto pb-1 [&::-webkit-scrollbar]:hidden [-ms-overflow-style:none] [scrollbar-width:none]">
			<Link href="/report-issue" className={PRIMARY_BTN}>
				<Plus className="h-4 w-4" />
				Нова заявка
			</Link>
			<Link href="/request-pass" className={SECONDARY_BTN}>
				<Car className="h-4 w-4" />
				Запросити гостя
			</Link>
			<Link href="/report-tenant" className={SECONDARY_BTN}>
				<AlertTriangle className="h-4 w-4" />
				Подати скаргу
			</Link>
			<Link href="/add-rating" className={SECONDARY_BTN}>
				<Star className="h-4 w-4" />
				Оцінити майстра
			</Link>
		</div>
	);
}
