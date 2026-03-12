import Link from "next/link";
import type { ReactNode } from "react";

interface KpiCardProps {
	label: string;
	value: string | number;
	icon: ReactNode;
	iconBg: string;
	iconColor: string;
	href?: string;
}

function CardInner({ label, value, icon, iconBg, iconColor }: Omit<KpiCardProps, "href">) {
	return (
		<div className="flex flex-col gap-3 rounded-2xl border border-[#E5E7EB] bg-white p-5 shadow-[0_1px_3px_rgba(0,0,0,0.06)] transition-shadow hover:shadow-[0_4px_12px_rgba(0,0,0,0.08)] dark:border-[#2D3D4F] dark:bg-[#162032]">
			<div className={`flex h-10 w-10 items-center justify-center rounded-xl ${iconBg} ${iconColor}`}>
				{icon}
			</div>
			<div>
				<p className="text-2xl font-bold text-[#111827] dark:text-[#F0EDE6]">{value}</p>
				<p className="mt-0.5 text-sm text-[#6B7280] dark:text-[#8FA8B8]">{label}</p>
			</div>
		</div>
	);
}

export default function KpiCard(props: KpiCardProps) {
	if (props.href) {
		return (
			<Link href={props.href} className="block">
				<CardInner {...props} />
			</Link>
		);
	}
	return <CardInner {...props} />;
}
