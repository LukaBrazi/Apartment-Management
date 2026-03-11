import type { Metadata } from "next";

export const metadata: Metadata = { title: "Skandi Apartments | Контакти" };

export default function ContactsPage() {
	return (
		<div className="flex flex-col gap-6">
			<div>
				<h1 className="text-2xl font-bold text-[#111827]">Контакти</h1>
				<p className="text-sm text-[#6B7280] mt-1">Контакти управителя та аварійні служби</p>
			</div>
			<div className="grid gap-4 sm:grid-cols-2">
				{[
					{ title: "Управитель будинку", value: "В розробці", icon: "user" },
					{ title: "Аварійна служба", value: "В розробці", icon: "phone" },
					{ title: "Електрик", value: "В розробці", icon: "zap" },
					{ title: "Сантехнік", value: "В розробці", icon: "droplet" },
				].map((c) => (
					<div key={c.title} className="rounded-2xl border border-[#E5E7EB] bg-white p-6 shadow-sm">
						<p className="text-xs font-medium uppercase tracking-wider text-[#6B7280]">{c.title}</p>
						<p className="mt-2 text-sm font-medium text-[#2F6FED]">В розробці</p>
					</div>
				))}
			</div>
		</div>
	);
}
