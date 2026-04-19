"use client";

import {
	useDeleteIssueMutation,
	useGetSingleIssueQuery,
} from "@/lib/redux/features/issues/issueApiSlice";
import { useGetUserProfileQuery } from "@/lib/redux/features/users/usersApiSlice";
import { extractErrorMessage } from "@/utils";
import { useRouter } from "next/navigation";
import React from "react";
import { toast } from "react-toastify";
import {
	Card,
	CardContent,
	CardDescription,
	CardFooter,
	CardHeader,
	CardTitle,
} from "../ui/card";
import { AuthFormHeader } from "../forms/auth";
import { CheckCheck, CircleDot, EyeIcon, Hotel } from "lucide-react";
import Link from "next/link";
import { Button } from "../ui/button";
import StatusBadge from "../admin/StatusBadge";

interface IssueDetailsProps {
	params: {
		id: string;
	};
}

export default function IssueDetails({ params }: IssueDetailsProps) {
	const id = params.id;
	const { data } = useGetSingleIssueQuery(id);
	const issue = data?.issue;
	const router = useRouter();

	const { data: currentUser } = useGetUserProfileQuery();

	const isStaff = currentUser?.profile.is_staff ?? false;

	const canUpdate = issue?.assigned_to === currentUser?.profile.full_name;

	const canDelete = issue?.reported_by === currentUser?.profile.full_name;

	const [deleteIssue] = useDeleteIssueMutation();

	const handleDeleteIssue = async () => {
		if (issue?.id) {
			try {
				await deleteIssue(issue.id).unwrap();
				router.push("/profile");
				toast.success("Заявку видалено");
			} catch (e) {
				const errorMessage = extractErrorMessage(e);
				toast.error(errorMessage || "An error occurred");
			}
		}
	};
	return (
		<Card className="rounded-xl border border-dashed dark:border-gray-700">
			<AuthFormHeader
				title={issue?.title}
				linkText="До профілю"
				linkHref="/profile"
			/>

			{/* Header — mobile-first: content stacks (unit info on top,
			    action buttons below as a full-width pair). At md+ the
			    original two-column layout returns. */}
			<CardHeader className="flex flex-col gap-4 border-b border-[#E5E7EB] p-4 sm:p-6 md:flex-row md:items-center md:justify-between md:gap-6 dark:border-[#2D3D4F]">
				<div className="grid min-w-0 gap-1">
					<CardTitle className="dark:text-platinum">
						<p className="flex flex-wrap items-center gap-x-2 gap-y-1">
							<Hotel className="tab-icon flex-shrink-0" />
							<span className="text-sm font-bold dark:text-babyPowder md:text-base">
								Номер квартири:
							</span>
							<span className="text-xl md:text-2xl">
								{issue?.unit_number ?? "—"}
							</span>
						</p>
					</CardTitle>

					<CardDescription className="mt-1">
						<p className="flex flex-wrap items-center gap-x-2 gap-y-1">
							<CheckCheck className="tab-icon flex-shrink-0" />
							<span className="text-sm font-semibold md:text-lg">
								Мешканець:
							</span>
							<span className="truncate text-sm md:text-lg">
								{issue?.reported_by}
							</span>
						</p>
					</CardDescription>
				</div>

				{/* Action buttons: stacked full-width on mobile, compact
				    top-right on desktop. `flex-row` at mobile lets both
				    buttons sit side-by-side when both are visible. */}
				{(canUpdate || canDelete) && (
					<div className="flex flex-row gap-3 md:flex-col md:gap-y-3">
						{canUpdate && (
							<Link
								href={`/issue/update-issue/${id}`}
								className="flex-1 md:flex-none"
							>
								<Button
									className="tap h-10 w-full bg-electricIndigo text-babyPowder md:ml-auto md:max-w-[300px] dark:bg-electricIndigo dark:text-babyPowder"
									size="sm"
									variant="outline"
								>
									Update Issue
								</Button>
							</Link>
						)}

						{canDelete && (
							<Button
								onClick={handleDeleteIssue}
								className="tap h-10 flex-1 bg-red-500 text-babyPowder md:ml-auto md:max-w-[300px] md:flex-none dark:bg-red-500 dark:text-babyPowder"
								size="sm"
								variant="outline"
							>
								Delete Issue
							</Button>
						)}
					</div>
				)}
			</CardHeader>

			<CardContent className="border-b border-[#E5E7EB] dark:border-[#2D3D4F]">
				<CardDescription className="mt-3">
					<div className="flex items-start gap-2">
						<CircleDot className="tab-icon mt-1 flex-shrink-0" />
						<span className="text-sm md:text-lg">{issue?.description}</span>
					</div>
				</CardDescription>
			</CardContent>

			{/* Footer — mobile-first: 2-column grid, then flex-row on md+.
			    Four metadata entries never fit in a single row on 375px;
			    the grid gives them reliable line breaks. */}
			<CardFooter className="mt-2 grid grid-cols-2 gap-3 md:flex md:flex-row md:justify-between dark:text-lime-500">
				<p className="min-w-0 truncate text-sm md:text-lg">
					Призначено:{" "}
					<span className="dark:text-platinum">
						{issue?.assigned_to || "Не призначено"}
					</span>
				</p>
				<p className="flex items-center gap-2 text-sm md:text-lg">
					Статус:{" "}
					{issue?.status && <StatusBadge value={issue.status} />}
				</p>
				{isStaff && (
					<p className="flex items-center gap-2 text-sm md:text-lg">
						Пріоритет:{" "}
						{issue?.priority && (
							<StatusBadge value={issue.priority} type="priority" />
						)}
					</p>
				)}
				<p className="flex flex-row items-center">
					<EyeIcon className="mr-1 size-5 flex-shrink-0" />
					<span className="text-sm dark:text-platinum md:text-lg">
						Переглядів: {issue?.view_count}
					</span>
				</p>
			</CardFooter>
		</Card>
	);
}
