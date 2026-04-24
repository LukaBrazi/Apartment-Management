import React from "react";

interface ProfileItemProps {
	icon: React.ReactNode;
	label: string;
	value: string;
}

export const ProfileItem: React.FC<ProfileItemProps> = ({ icon, label, value }) => (
	<div className="flex items-start gap-2.5 rounded-xl bg-[#F8FAFC] px-3 py-2.5 dark:bg-[#1E2D3D]">
		<div className="mt-0.5 flex-shrink-0 text-[#1E2761] dark:text-[#CADCFC]">{icon}</div>
		<div className="min-w-0">
			<p className="text-xs font-medium text-[#64748B] dark:text-[#8FA8B8]">{label}</p>
			<p className="break-words text-sm font-semibold text-[#0F172A] dark:text-[#F0EDE6]">{value || "—"}</p>
		</div>
	</div>
);
