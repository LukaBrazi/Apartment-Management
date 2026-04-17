import type { Metadata } from "next";

export const metadata: Metadata = { title: "ApartmentOS | Оголошення" };

export default function AnnouncementsPage() {
	return (
		<div className="flex flex-col gap-6">
			<div>
				<h1 className="text-2xl font-bold text-[#111827]">Оголошення</h1>
				<p className="text-sm text-[#6B7280] mt-1">Новини та повідомлення від управителя</p>
			</div>
			<div className="rounded-2xl border border-[#E5E7EB] bg-white p-8 text-center shadow-sm">
				<div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-[#EEF3FD]">
					<svg className="h-8 w-8 text-[#2F6FED]" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
						<path d="M3 11l19-9-9 19-2-8-8-2z"/>
					</svg>
				</div>
				<h2 className="text-lg font-semibold text-[#111827]">В розробці</h2>
				<p className="mt-2 text-sm text-[#6B7280]">Стрічка оголошень від управителя будинку незабаром буде доступна.</p>
			</div>
		</div>
	);
}
