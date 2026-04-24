import ProtectedRoute from "@/components/shared/ProtectedRoutes";

import React from "react";

import type { Metadata } from "next";
import Header from "@/components/profile/Header";
import ProfileTabs from "@/components/profile/ProfileTabs";

export const metadata: Metadata = {
	title: "ApartmentOS | User Profile",
	description: "Signed in users can view all their profile information",
};

function ProfilePageContent() {
	return (
		<>
			<div className="flex flex-col gap-4 px-0 pb-4 md:gap-6">
				<Header />
				<ProfileTabs />
			</div>
			{/* Buttons moved to About.tsx — only visible on the "Про мене" tab */}
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
