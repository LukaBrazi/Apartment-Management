import RoleGuard from "@/components/shared/RoleGuard";
import CreatePostForm from "@/components/forms/add-post/CreatePostForm";
import { AuthFormHeader } from "@/components/forms/auth";
import type { Metadata } from "next";

export const metadata: Metadata = {
	title: "Skandi Apartments | Нова публікація",
	description:
		"Авторизовані користувачі можуть задавати питання або публікувати контент для всіх",
};

export default function AddPostPage() {
	return (
		<RoleGuard role="staff">
			<div>
				<AuthFormHeader
					title="Створити публікацію"
					staticText="Ask Questions, share thoughts or information with everyone!"
					linkText="На головну"
					linkHref="/welcome"
				/>
				<div className="mt-7 sm:mx-auto sm:w-full sm:max-w-[480px]">
					<div className="bg-lightGrey dark:bg-deepBlueGrey rounded-xl px-6 py-12 shadow sm:rounded-lg sm:px-12 md:rounded-3xl">
						<CreatePostForm />
					</div>
				</div>
			</div>
		</RoleGuard>
	);
}
