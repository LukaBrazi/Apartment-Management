import { AuthFormHeader } from "@/components/forms/auth";
import EditProfileForm from "@/components/forms/profile/EditProfileForm";
import type { Metadata } from "next";

export const metadata: Metadata = {
	title: "ApartmentOS | Profile Edit",
	description: "Signed in users can edit their profile information",
};

export default function EditProfilePage() {
	// Mobile-first: migrated from legacy `bg-lightGrey` / `bg-deepBlueGrey`
	// Nordic tokens to unified SaaS surface; padding tightened on phones
	// (p-5) and restored to the original airy desktop layout at sm+.
	return (
		<div>
			<AuthFormHeader title="Update Profile" />
			<div className="mt-6 sm:mx-auto sm:mt-7 sm:w-full sm:max-w-[480px]">
				<div className="rounded-2xl border border-[#E5E7EB] bg-white p-5 shadow-sm sm:rounded-lg sm:px-12 sm:py-12 md:rounded-3xl dark:border-[#2D3D4F] dark:bg-[#162032]">
					<EditProfileForm />
				</div>
			</div>
		</div>
	);
}
