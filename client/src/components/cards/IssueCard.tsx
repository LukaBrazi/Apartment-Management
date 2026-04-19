"use client";

import Link from "next/link";
import React from "react";
import {
	Card,
	CardContent,
	CardDescription,
	CardFooter,
	CardHeader,
	CardTitle,
} from "@/components/ui/card";
import { Hotel } from "lucide-react";
import StatusBadge from "@/components/admin/StatusBadge";
import { useGetUserProfileQuery } from "@/lib/redux/features/users/usersApiSlice";

interface Issue {
	id: string;
	title: string;
	description: string;
	unit_number: string | null;
	status: string;
	priority: string;
}

interface IssueCardProps {
	issue: Issue;
}

export default function IssueCard({ issue }: IssueCardProps) {
	const { data: currentUser } = useGetUserProfileQuery();
	const isStaff = currentUser?.profile.is_staff ?? false;

	// Mobile-first: padded card with line-clamp (instead of string .substring
	// which strips diacritics mid-word) so long Ukrainian titles/descriptions
	// wrap cleanly on 375px viewports. Footer uses flex-wrap so Status and
	// Priority chips stack onto a second row when both visible.
	return (
		<Link href={`/issue/${issue.id}`} key={issue.id} className="block">
			<Card
				key={issue.id}
				className="rounded-xl border border-dashed border-[#E5E7EB] transition-colors hover:border-pumpkin dark:border-[#2D3D4F] hover:dark:border-platinum"
			>
				<CardHeader className="p-4 md:p-6">
					<CardTitle
						className="h3-semibold font-robotoSlab line-clamp-2 text-base md:text-xl dark:text-pumpkin"
						title={issue.title}
					>
						{issue.title}
					</CardTitle>
				</CardHeader>
				<CardContent className="space-y-3 px-4 pb-2 md:px-6">
					<CardDescription className="dark:text-platinum">
						<p
							className="h4-semibold line-clamp-3 text-sm md:text-base"
							title={issue.description}
						>
							{issue.description}
						</p>
					</CardDescription>

					<CardDescription className="dark:text-platinum">
						<p className="flex flex-wrap items-center gap-x-2 gap-y-1">
							<Hotel className="tab-icon flex-shrink-0" />
							<span className="tab-font text-sm">Номер квартири:</span>
							<span className="text-base md:text-lg">
								{issue.unit_number ?? "—"}
							</span>
						</p>
					</CardDescription>
				</CardContent>

				<CardFooter className="flex flex-row flex-wrap justify-between gap-2 p-4 md:p-6 dark:text-babyPowder">
					<p className="flex items-center gap-1.5 text-sm">
						<span className="mr-0.5 font-bold">Статус:</span>
						<StatusBadge value={issue.status} />
					</p>

					{isStaff && (
						<p className="flex items-center gap-1.5 text-sm">
							<span className="mr-0.5 font-bold">Пріоритет:</span>
							<StatusBadge value={issue.priority} type="priority" />
						</p>
					)}
				</CardFooter>
			</Card>
		</Link>
	);
}
