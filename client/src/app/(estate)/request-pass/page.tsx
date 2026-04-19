import { AuthFormHeader } from "@/components/forms/auth";
import CreatePassForm from "@/components/forms/request-pass/CreatePassForm";
import type { Metadata } from "next";

export const metadata: Metadata = {
	title: "ApartmentOS | Request Vehicle Pass",
	description: "Submit a vehicle pass request so the guard can let your visitor through",
};

export default function RequestPassPage() {
	return (
		<div>
			<AuthFormHeader title="Замовити перепустку для авто" />
			{/* Mobile-first container: tight padding on narrow phones, the
			    original generous card layout at sm+ (480px) and above. Also
			    migrated from the legacy `bg-lightGrey` Nordic token to the
			    unified `saas.card` surface so this page participates in the
			    Phase 1 token consolidation. */}
			<div className="mt-6 sm:mx-auto sm:mt-7 sm:w-full sm:max-w-[480px]">
				<div className="rounded-2xl border border-[#E5E7EB] bg-white p-5 shadow-sm sm:rounded-lg sm:px-12 sm:py-12 md:rounded-3xl dark:border-[#2D3D4F] dark:bg-[#162032]">
					<CreatePassForm />
				</div>
			</div>
		</div>
	);
}
