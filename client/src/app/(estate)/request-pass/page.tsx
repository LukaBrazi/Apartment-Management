import { AuthFormHeader } from "@/components/forms/auth";
import CreatePassForm from "@/components/forms/request-pass/CreatePassForm";
import type { Metadata } from "next";

export const metadata: Metadata = {
	title: "Alpha Apartments | Request Vehicle Pass",
	description: "Submit a vehicle pass request so the guard can let your visitor through",
};

export default function RequestPassPage() {
	return (
		<div>
			<AuthFormHeader title="Замовити перепустку для авто" />
			<div className="mt-7 sm:mx-auto sm:w-full sm:max-w-[480px]">
				<div className="bg-lightGrey dark:bg-deepBlueGrey rounded-xl px-6 py-12 shadow sm:rounded-lg sm:px-12 md:rounded-3xl">
					<CreatePassForm />
				</div>
			</div>
		</div>
	);
}
