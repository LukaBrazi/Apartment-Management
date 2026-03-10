import RoleGuard from "@/components/shared/RoleGuard";
import GuardPortalView from "@/components/guard/GuardPortalView";
import type { Metadata } from "next";

export const metadata: Metadata = {
	title: "Skandi Apartments | Портал охорони",
	description: "Портал охорони — перегляд та управління заявками на в'їзд авто",
};

export default function GuardPortalPage() {
	return (
		<RoleGuard role="guard">
			<GuardPortalView />
		</RoleGuard>
	);
}
