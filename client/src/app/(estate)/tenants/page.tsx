import TenantCard from "@/components/cards/TenantCard";
import ProtectedRoute from "@/components/shared/ProtectedRoutes";
import type { Metadata } from "next";

export const metadata: Metadata = {
	title: "Alpha Apartments | Мешканці",
	description:
		"Авторизовані користувачі можуть переглядати базову інформацію про інших мешканців",
};

function TenantsPageContent() {
	return (
		<div>
			<TenantCard />
		</div>
	);
}

export default function TenantsPage() {
	return (
		<ProtectedRoute>
			<TenantsPageContent />
		</ProtectedRoute>
	);
}
