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

	return (
		<Link href={`/issue/${issue.id}`} key={issue.id}>
			<Card
				key={issue.id}
				className="hover:border-pumpkin dark:border-gray hover:dark:border-platinum rounded-xl border border-dashed"
			>
				<CardHeader>
					<CardTitle className="flex-center h3-semibold font-robotoSlab dark:text-pumpkin" title={issue.title}>
						{issue.title.length > 20
							? `${issue.title.substring(0, 20)}....`
							: issue.title}
					</CardTitle>
				</CardHeader>
				<CardContent>
					<CardDescription className="dark:text-platinum">
						<p className="h4-semibold" title={issue.description}>
							{issue.description.length > 35
								? `${issue.description.substring(0, 35)}....`
								: issue.description}
						</p>
					</CardDescription>
				</CardContent>

				<CardContent>
					<CardDescription className="dark:text-platinum">
						<p className="flex items-center space-x-2">
							<Hotel className="tab-icon" />
							<span className="tab-font">Номер квартири: </span>
							<span className="text-lg">{issue.unit_number ?? "—"}</span>
						</p>
					</CardDescription>
				</CardContent>

				<CardFooter className="dark:text-babyPowder flex flex-row justify-between">
					<p className="flex items-center gap-1.5">
						<span className="mr-0.5 font-bold">Статус: </span>
						<StatusBadge value={issue.status} />
					</p>

					{isStaff && (
						<p className="flex items-center gap-1.5">
							<span className="mr-0.5 font-bold">Пріоритет: </span>
							<StatusBadge value={issue.priority} type="priority" />
						</p>
					)}
				</CardFooter>
			</Card>
		</Link>
	);
}
