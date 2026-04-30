"use client";

import { useGetMyAssignedIssuesQuery } from "@/lib/redux/features/issues/issueApiSlice";
import React from "react";
import Spinner from "../shared/Spinner";
import IssueCard from "../cards/IssueCard";

/**
 * PR-16: refactored from a Tabs-bound `<TabsContent>` wrapper to a
 * standalone container so the same component can render inside the
 * dedicated `/assigned-issues` page (sidebar nav target) without
 * depending on the Radix Tabs context.
 */
export default function AssignedIssues() {
	const { data: assignedIssues, isLoading } = useGetMyAssignedIssuesQuery("");

	const myAssignedIssues = assignedIssues?.assigned_issues;

	if (isLoading) {
		return (
			<div className="flex-center pt-32">
				<Spinner size="xl" />
			</div>
		);
	}

	return (
		<div className="w-full">
			<h2 className="h2-semibold flex-center font-robotoSlab dark:text-pumpkin text-xl">
				Всього: ({myAssignedIssues?.count ?? 0})
			</h2>
			<div className="mt-4 grid cursor-pointer grid-cols-1 gap-4 p-1.5 md:grid-cols-2 lg:grid-cols-3">
				{myAssignedIssues && myAssignedIssues.results.length > 0 ? (
					myAssignedIssues.results.map((issue) => (
						<IssueCard key={issue.id} issue={issue} />
					))
				) : (
					<p className="h2-semibold dark:text-lime-500">
						Жодних призначених заявок поки немає.
					</p>
				)}
			</div>
		</div>
	);
}
