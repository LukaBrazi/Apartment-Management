"use client";

/**
 * ConsentSummary — read-only display of the user's GDPR consent state
 * (PR-5).  Mounted inside the "Про мене" tab on the profile page.
 *
 * Shows the latest accepted version of ToS and Privacy with timestamps.
 * No re-accept button: the audit log is immutable, and outdated versions
 * are surfaced via the global ConsentGate modal — not here.
 */
import { useGetMyConsentQuery } from "@/lib/redux/features/consent/consentApiSlice";
import type { Consent } from "@/types";
import { formatDate } from "@/utils";
import { ShieldCheck } from "lucide-react";

interface RowProps {
	label: string;
	consent: Consent | null;
}

function ConsentRow({ label, consent }: RowProps) {
	return (
		<div className="flex items-start justify-between gap-3 rounded-xl border border-[#E5E7EB] p-3 dark:border-[#2D3D4F]">
			<div className="flex items-start gap-3">
				<ShieldCheck className="mt-0.5 h-5 w-5 text-[#1E2761] dark:text-[#8FA8FF]" />
				<div>
					<div className="text-sm font-medium text-[#0F172A] dark:text-white">
						{label}
					</div>
					{consent ? (
						<div className="text-xs text-[#475569] dark:text-[#8FA8B8]">
							Версія {consent.version} · прийнято{" "}
							{formatDate(consent.accepted_at).toString()}
						</div>
					) : (
						<div className="text-xs text-[#94A3B8]">Ще не прийнято</div>
					)}
				</div>
			</div>
			{consent && (
				<span
					className={
						consent.current
							? "rounded-full bg-[#DCFCE7] px-2 py-0.5 text-xs font-medium text-[#166534]"
							: "rounded-full bg-[#FEF3C7] px-2 py-0.5 text-xs font-medium text-[#92400E]"
					}
				>
					{consent.current ? "Актуальна" : "Застаріла"}
				</span>
			)}
		</div>
	);
}

export default function ConsentSummary() {
	const { data, isLoading } = useGetMyConsentQuery();

	if (isLoading || !data) return null;

	return (
		<div className="space-y-3 px-4 pb-4">
			<h3 className="text-sm font-semibold text-[#0F172A] dark:text-white">
				Згоди
			</h3>
			<ConsentRow label="Умови користування" consent={data.tos} />
			<ConsentRow label="Політика приватності" consent={data.privacy} />
		</div>
	);
}
