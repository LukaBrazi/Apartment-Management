import Link from "next/link";
import type { ReactNode } from "react";

interface KpiCardProps {
	label: string;
	value: string | number;
	icon: ReactNode;
	iconBg: string;
	iconColor: string;
	href?: string;
	actionText?: string;
}

function CardInner({ label, value, icon, iconBg, iconColor, actionText = "Переглянути →" }: Omit<KpiCardProps, "href">) {
	return (
		<div className="flex flex-col gap-3 rounded-2xl border border-[#F1F5F9] bg-white p-5 shadow-[0_1px_2px_rgba(0,0,0,0.05)] transition-shadow hover:shadow-[0_4px_12px_rgba(0,0,0,0.08)] dark:border-[#2D3D4F] dark:bg-[#162032]">
			<div className="flex items-center justify-between">
				<p className="text-sm text-[#6B7280] dark:text-[#8FA8B8]">{label}</p>
				<div className={`flex h-10 w-10 items-center justify-center rounded-xl ${iconBg} ${iconColor}`}>
					{icon}
				</div>
			</div>
			<p className="text-4xl font-bold text-[#0F172A] dark:text-[#F0EDE6]">{value}</p>
			<p className="text-sm font-medium text-[#4A90D9]">{actionText}</p>
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
