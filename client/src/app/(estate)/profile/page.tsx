import ProtectedRoute from "@/components/shared/ProtectedRoutes";

import React from "react";

import type { Metadata } from "next";
import Header from "@/components/profile/Header";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import ProfileTabs from "@/components/profile/ProfileTabs";

export const metadata: Metadata = {
	title: "Skandi Apartments | User Profile",
	description: "Signed in users can view all their profile information",
};

function ProfilePageContent() {
	return (
		<>
			<div className="grid items-start gap-4 px-4 pb-4 md:gap-6 md:px-6">
				<Header />
				<ProfileTabs />
			</div>
			<div className="flex cursor-pointer flex-row justify-between">
				<Link href="/profile/edit">
					<Button className="h3-semibold electricIndigo-gradient text-babyPowder w-64 rounded-lg">
						Оновити профіль
					</Button>
				</Link>
				<Link href="/apartment">
					<Button className="h3-semibold electricIndigo-gradient text-babyPowder w-64 rounded-lg">
						Додати квартиру
					</Button>
				</Link>
			</div>
		</>
	);
}

export default function ProfilePage() {
	return (
		<ProtectedRoute>
			<ProfilePageContent />
		</ProtectedRoute>
	);
}
