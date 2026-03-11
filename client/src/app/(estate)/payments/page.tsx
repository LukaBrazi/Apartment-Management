import type { Metadata } from "next";

export const metadata: Metadata = { title: "Skandi Apartments | Платежі" };

export default function PaymentsPage() {
	return (
		<div className="flex flex-col gap-6">
			<div>
				<h1 className="text-2xl font-bold text-[#111827]">Платежі</h1>
				<p className="text-sm text-[#6B7280] mt-1">Управління комунальними платежами</p>
			</div>
			<div className="rounded-2xl border border-[#E5E7EB] bg-white p-8 text-center shadow-sm">
				<div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-[#EEF3FD]">
					<svg className="h-8 w-8 text-[#2F6FED]" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
						<rect x="1" y="4" width="22" height="16" rx="2" ry="2"/>
						<line x1="1" y1="10" x2="23" y2="10"/>
					</svg>
				</div>
				<h2 className="text-lg font-semibold text-[#111827]">В розробці</h2>
				<p className="mt-2 text-sm text-[#6B7280]">Онлайн-оплата комунальних послуг незабаром буде доступна.</p>
			</div>
		</div>
	);
}
