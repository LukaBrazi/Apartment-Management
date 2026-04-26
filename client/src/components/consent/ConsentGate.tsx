"use client";

/**
 * ConsentGate — GDPR ToS + Privacy modal blocker (PR-5).
 *
 * Wraps the estate layout's children. While the user has either no
 * consent record or an outdated record (server-side `current === false`)
 * for ToS or Privacy, a fixed-overlay modal renders and prevents UI
 * interaction.
 *
 * Behaviour:
 *   · `useGetMyConsentQuery` is loading             → render children
 *     unchanged (do not block on auth bootstrap or initial fetch).
 *   · query errored (e.g. 401 on logged-out users)  → render children;
 *     the gate is not the auth boundary.
 *   · `tos === null || tos.current === false` (or
 *     same for privacy)                              → render children +
 *     modal overlay.  Once both checkboxes are ticked and the user
 *     clicks "Прийняти", the component fires one POST per missing /
 *     outdated type, then refetches and dismisses itself.
 */
import { Button } from "@/components/ui/button";
import {
	useAcceptConsentMutation,
	useGetMyConsentQuery,
} from "@/lib/redux/features/consent/consentApiSlice";
import type { ConsentMeResponse, ConsentType } from "@/types";
import Link from "next/link";
import React from "react";

interface ConsentGateProps {
	children: React.ReactNode;
}

/** Returns the list of consent types that the user must (re-)accept. */
function missingTypes(data: ConsentMeResponse | undefined): ConsentType[] {
	if (!data) return [];
	const out: ConsentType[] = [];
	if (!data.tos || data.tos.current === false) out.push("tos");
	if (!data.privacy || data.privacy.current === false) out.push("privacy");
	return out;
}

export default function ConsentGate({ children }: ConsentGateProps) {
	const { data, isLoading, isError, refetch } = useGetMyConsentQuery();
	const [acceptConsent, { isLoading: isSubmitting }] =
		useAcceptConsentMutation();

	const [tosChecked, setTosChecked] = React.useState(false);
	const [privacyChecked, setPrivacyChecked] = React.useState(false);
	const [submitError, setSubmitError] = React.useState<string | null>(null);

	// Don't gate on first paint or when the user is not authenticated —
	// EstateAuthGate handles the auth redirect, and the consent endpoint
	// returns 401 for anonymous users which surfaces here as `isError`.
	if (isLoading || isError || !data) {
		return <>{children}</>;
	}

	const required = missingTypes(data);
	if (required.length === 0) {
		return <>{children}</>;
	}

	const tosNeeded = required.includes("tos");
	const privacyNeeded = required.includes("privacy");
	const canSubmit =
		(!tosNeeded || tosChecked) && (!privacyNeeded || privacyChecked);

	const handleAccept = async () => {
		setSubmitError(null);
		try {
			// Hotfix 2026-04-26: use server-provided current versions from
			// /consent/me/. Previously we sent data.tos?.version (which echoes
			// the user's stale version) or "current" sentinel — both never
			// matched settings.TOS_VERSION on next GET, so `current` stayed
			// false and the modal looped forever.
			const targets: { type: ConsentType; version: string }[] = [];
			if (tosNeeded) {
				targets.push({ type: "tos", version: data.tos_current_version });
			}
			if (privacyNeeded) {
				targets.push({
					type: "privacy",
					version: data.privacy_current_version,
				});
			}

			for (const t of targets) {
				await acceptConsent({
					consent_type: t.type,
					version: t.version,
				}).unwrap();
			}

			await refetch();
			setTosChecked(false);
			setPrivacyChecked(false);
		} catch (err) {
			setSubmitError(
				"Не вдалося зберегти згоду. Спробуйте ще раз.",
			);
			// eslint-disable-next-line no-console
			console.error("ConsentGate: acceptConsent failed", err);
		}
	};

	return (
		<>
			{children}
			<div
				className="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 px-4"
				role="dialog"
				aria-modal="true"
				aria-labelledby="consent-gate-title"
			>
				<div className="w-full max-w-lg rounded-2xl bg-white p-6 shadow-2xl dark:bg-[#1A2B3C]">
					<h2
						id="consent-gate-title"
						className="text-xl font-semibold text-[#0F172A] dark:text-white"
					>
						Оновіть свої згоди
					</h2>
					<p className="mt-2 text-sm text-[#475569] dark:text-[#8FA8B8]">
						Щоб продовжити користуватися ApartmentOS, прийміть
						актуальні редакції умов користування та політики
						приватності.
					</p>

					<div className="mt-5 space-y-4">
						{tosNeeded && (
							<label className="flex items-start gap-3 text-sm text-[#0F172A] dark:text-white">
								<input
									type="checkbox"
									className="mt-0.5 h-4 w-4 rounded border-[#CBD5E1] text-[#1E2761] focus:ring-[#1E2761]"
									checked={tosChecked}
									onChange={(e) =>
										setTosChecked(e.target.checked)
									}
								/>
								<span>
									Я прочитав(-ла) і приймаю{" "}
									<Link
										href="/terms"
										target="_blank"
										className="text-[#1E2761] underline dark:text-[#8FA8FF]"
									>
										Умови користування
									</Link>
									.
								</span>
							</label>
						)}

						{privacyNeeded && (
							<label className="flex items-start gap-3 text-sm text-[#0F172A] dark:text-white">
								<input
									type="checkbox"
									className="mt-0.5 h-4 w-4 rounded border-[#CBD5E1] text-[#1E2761] focus:ring-[#1E2761]"
									checked={privacyChecked}
									onChange={(e) =>
										setPrivacyChecked(e.target.checked)
									}
								/>
								<span>
									Я ознайомлений(-а) з{" "}
									<Link
										href="/privacy"
										target="_blank"
										className="text-[#1E2761] underline dark:text-[#8FA8FF]"
									>
										Політикою приватності
									</Link>
									.
								</span>
							</label>
						)}
					</div>

					{submitError && (
						<p className="mt-4 text-sm text-[#DC2626]">
							{submitError}
						</p>
					)}

					<div className="mt-6 flex justify-end">
						<Button
							onClick={handleAccept}
							disabled={!canSubmit || isSubmitting}
							className="bg-[#1E2761] text-white hover:bg-[#1A2150] disabled:opacity-50"
						>
							{isSubmitting ? "Зберігаємо…" : "Прийняти"}
						</Button>
					</div>
				</div>
			</div>
		</>
	);
}
