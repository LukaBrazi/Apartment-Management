"use client";

import {
	useDeleteIssueMutation,
	useGetSingleIssueQuery,
	useGetIssueReviewsQuery,
	useReviewIssueMutation,
} from "@/lib/redux/features/issues/issueApiSlice";
import {
	useAdminUpdateIssueMutation,
	useGetAdminWorkersQuery,
} from "@/lib/redux/features/admin/adminApiSlice";
import { useGetUserProfileQuery } from "@/lib/redux/features/users/usersApiSlice";
import { extractErrorMessage } from "@/utils";
import { occupationOptions } from "@/constants";
import { useRouter } from "next/navigation";
import React, { useEffect, useState } from "react";
import { toast } from "react-toastify";
import {
	Card,
	CardContent,
	CardDescription,
	CardFooter,
	CardHeader,
	CardTitle,
} from "../ui/card";
import {
	Dialog,
	DialogContent,
	DialogFooter,
	DialogHeader,
	DialogTitle,
} from "../ui/dialog";
import {
	Select,
	SelectContent,
	SelectItem,
	SelectTrigger,
	SelectValue,
} from "../ui/select";
import { AuthFormHeader } from "../forms/auth";
import { CheckCheck, CircleDot, EyeIcon, Hotel, Pencil, Star } from "lucide-react";
import Link from "next/link";
import { Button } from "../ui/button";
import StatusBadge from "../admin/StatusBadge";

const NO_ASSIGNEE = "__none__";

const OCCUPATION_LABELS: Record<string, string> = Object.fromEntries(
	occupationOptions.map((o) => [o.value, o.label]),
);

interface IssueDetailsProps {
	params: {
		id: string;
	};
}

function StarRating({
	value,
	onChange,
	readonly = false,
}: {
	value: number;
	onChange?: (v: number) => void;
	readonly?: boolean;
}) {
	const [hovered, setHovered] = useState(0);
	return (
		<div className="flex gap-1">
			{[1, 2, 3, 4, 5].map((star) => (
				<button
					key={star}
					type="button"
					disabled={readonly}
					onClick={() => !readonly && onChange?.(star)}
					onMouseEnter={() => !readonly && setHovered(star)}
					onMouseLeave={() => !readonly && setHovered(0)}
					className={`transition-colors ${readonly ? "cursor-default" : "cursor-pointer"}`}
				>
					<Star
						className={`size-6 ${
							star <= (hovered || value)
								? "fill-yellow-400 text-yellow-400"
								: "fill-none text-gray-400 dark:text-gray-600"
						}`}
					/>
				</button>
			))}
		</div>
	);
}

export default function IssueDetails({ params }: IssueDetailsProps) {
	const id = params.id;
	const { data } = useGetSingleIssueQuery(id);
	const issue = data?.issue;
	const router = useRouter();

	const { data: currentUser } = useGetUserProfileQuery();
	const { data: reviewsData, refetch: refetchReviews } = useGetIssueReviewsQuery(id, {
		skip: issue?.status !== "done",
	});

	const isStaff = currentUser?.profile.is_staff ?? false;
	const canUpdate = issue?.assigned_to === currentUser?.profile.full_name;
	const canDelete = issue?.reported_by === currentUser?.profile.full_name;

	const isParticipant = canUpdate || canDelete;
	const isDone = issue?.status === "done";

	// Determine if current user already reviewed this issue
	const myReview = reviewsData?.reviews.find(
		(r) =>
			r.reviewer_name === currentUser?.profile.full_name
	);

	const [rating, setRating] = useState(0);
	const [comment, setComment] = useState("");
	const [reviewIssue, { isLoading: isReviewing }] = useReviewIssueMutation();

	const [deleteIssue] = useDeleteIssueMutation();

	// ── Admin edit dialog ─────────────────────────────────────────────────
	const [editOpen, setEditOpen] = useState(false);
	const [editStatus, setEditStatus] = useState<string>("");
	const [editPriority, setEditPriority] = useState<string>("");
	const [editAssignee, setEditAssignee] = useState<string>(NO_ASSIGNEE);

	const { data: workersData } = useGetAdminWorkersQuery(undefined, {
		skip: !isStaff,
	});
	const workers = workersData?.non_tenant_profiles?.results ?? [];

	const [updateIssueAdmin, { isLoading: isUpdatingAdmin }] =
		useAdminUpdateIssueMutation();

	// Hydrate the form from the loaded issue ONCE per id.  We deliberately
	// depend on the id (not the full issue object) — RTK Query refetches
	// the issue on focus, and re-running this effect would clobber the
	// user's in-flight selections inside an open dialog.
	useEffect(() => {
		if (issue) {
			setEditStatus(issue.status);
			setEditPriority(issue.priority);
			setEditAssignee(issue.assigned_to ?? NO_ASSIGNEE);
		}
		// eslint-disable-next-line react-hooks/exhaustive-deps
	}, [issue?.id]);

	const handleAdminUpdate = async () => {
		if (!issue) return;
		try {
			await updateIssueAdmin({
				issueId: issue.id,
				status: editStatus,
				priority: editPriority,
				assigned_to_username:
					editAssignee === NO_ASSIGNEE ? null : editAssignee,
			}).unwrap();
			toast.success("Заявку оновлено");
			setEditOpen(false);
		} catch (e) {
			toast.error(extractErrorMessage(e) || "Помилка оновлення");
		}
	};

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

	const handleSubmitReview = async () => {
		if (!rating) {
			toast.error("Оберіть оцінку від 1 до 5");
			return;
		}
		try {
			await reviewIssue({ issueId: id, rating, comment }).unwrap();
			toast.success("Оцінку збережено!");
			refetchReviews();
			setRating(0);
			setComment("");
		} catch (e) {
			const errorMessage = extractErrorMessage(e);
			toast.error(errorMessage || "Помилка збереження оцінки");
		}
	};

	// Label: author rates worker, worker rates author
	const reviewLabel = canDelete
		? "Оцінити виконавця"
		: "Оцінити замовника";

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
				{(canUpdate || canDelete || isStaff) && (
					<div className="flex flex-row flex-wrap gap-3 md:flex-col md:gap-y-3">
						{isStaff && (
							<Button
								onClick={() => setEditOpen(true)}
								className="tap h-10 flex-1 bg-[#3D7A8A] text-white md:ml-auto md:max-w-[300px] md:flex-none dark:bg-[#5BA3B5] dark:text-white"
								size="sm"
								variant="outline"
							>
								<Pencil className="mr-1 h-4 w-4" />
								Редагувати
							</Button>
						)}

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
									Оновити заявку
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
								Видалити заявку
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

			{/* ── Mutual review section (visible only when issue is done and user is participant) ── */}
			{isDone && isParticipant && (
				<div className="border-t border-[#E5E7EB] px-4 py-5 sm:px-6 dark:border-[#2D3D4F]">
					{/* Show existing reviews */}
					{reviewsData?.reviews && reviewsData.reviews.length > 0 && (
						<div className="mb-5 space-y-3">
							<h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300">
								Оцінки по заявці
							</h3>
							{reviewsData.reviews.map((review) => (
								<div
									key={review.id}
									className="rounded-lg border border-[#E5E7EB] bg-gray-50 p-3 dark:border-[#2D3D4F] dark:bg-gray-800/40"
								>
									<div className="flex items-center justify-between">
										<span className="text-sm font-medium dark:text-babyPowder">
											{review.reviewer_name} → {review.reviewee_name}
										</span>
										<StarRating value={review.rating} readonly />
									</div>
									{review.comment && (
										<p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
											{review.comment}
										</p>
									)}
								</div>
							))}
						</div>
					)}

					{/* Review form — only if user hasn't reviewed yet */}
					{!myReview ? (
						<div className="space-y-3">
							<h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300">
								{reviewLabel}
							</h3>
							<StarRating value={rating} onChange={setRating} />
							<textarea
								value={comment}
								onChange={(e) => setComment(e.target.value)}
								placeholder="Коментар (необов'язково)"
								rows={3}
								className="w-full rounded-lg border border-[#E5E7EB] bg-white px-3 py-2 text-sm text-gray-700 outline-none focus:ring-2 focus:ring-electricIndigo dark:border-[#2D3D4F] dark:bg-gray-800 dark:text-gray-200"
							/>
							<Button
								onClick={handleSubmitReview}
								disabled={isReviewing || rating === 0}
								className="tap bg-electricIndigo text-babyPowder dark:bg-electricIndigo dark:text-babyPowder"
								size="sm"
							>
								{isReviewing ? "Збереження..." : "Надіслати оцінку"}
							</Button>
						</div>
					) : (
						<p className="text-sm text-gray-500 dark:text-gray-400">
							✓ Ви вже залишили оцінку по цій заявці
						</p>
					)}
				</div>
			)}

			{/* ── Admin edit dialog (status / priority / assignee) ───────── */}
			<Dialog open={editOpen} onOpenChange={setEditOpen}>
				<DialogContent className="max-w-md border-[#E2E5E8] bg-white dark:border-[#2D3D4F] dark:bg-[#162032]">
					<DialogHeader>
						<DialogTitle className="text-[#1C2B3A] dark:text-white">
							Редагувати заявку
						</DialogTitle>
					</DialogHeader>

					{issue && (
						<p className="-mt-2 truncate text-sm text-[#6B7F8C]">
							{issue.title}
						</p>
					)}

					<div className="mt-2 space-y-4">
						{/* Status */}
						<div className="space-y-1">
							<label className="text-xs font-medium text-[#6B7F8C]">
								Статус
							</label>
							<Select value={editStatus} onValueChange={setEditStatus}>
								<SelectTrigger className="border-[#E2E5E8] bg-[#F7F6F2] dark:border-[#2D3D4F] dark:bg-[#1C2B3A]">
									<SelectValue placeholder="Оберіть статус" />
								</SelectTrigger>
								<SelectContent>
									<SelectItem value="reported">Подано</SelectItem>
									<SelectItem value="accepted">Прийнято</SelectItem>
									<SelectItem value="in_progress">В роботі</SelectItem>
									<SelectItem value="done">Виконано</SelectItem>
									<SelectItem value="rejected">Відхилено</SelectItem>
								</SelectContent>
							</Select>
						</div>

						{/* Priority */}
						<div className="space-y-1">
							<label className="text-xs font-medium text-[#6B7F8C]">
								Пріоритет
							</label>
							<Select value={editPriority} onValueChange={setEditPriority}>
								<SelectTrigger className="border-[#E2E5E8] bg-[#F7F6F2] dark:border-[#2D3D4F] dark:bg-[#1C2B3A]">
									<SelectValue placeholder="Оберіть пріоритет" />
								</SelectTrigger>
								<SelectContent>
									<SelectItem value="low">Низький</SelectItem>
									<SelectItem value="medium">Середній</SelectItem>
									<SelectItem value="high">Високий</SelectItem>
								</SelectContent>
							</Select>
						</div>

						{/* Assignee */}
						<div className="space-y-1">
							<label className="text-xs font-medium text-[#6B7F8C]">
								Виконавець
							</label>
							<Select value={editAssignee} onValueChange={setEditAssignee}>
								<SelectTrigger className="border-[#E2E5E8] bg-[#F7F6F2] dark:border-[#2D3D4F] dark:bg-[#1C2B3A]">
									<SelectValue placeholder="Оберіть виконавця" />
								</SelectTrigger>
								<SelectContent>
									<SelectItem value={NO_ASSIGNEE}>
										— Не призначено —
									</SelectItem>
									{workers.map((w) => (
										<SelectItem key={w.username} value={w.username}>
											{w.full_name || w.username}
											<span className="ml-1 text-xs text-[#6B7F8C]">
												{OCCUPATION_LABELS[w.occupation] ?? w.occupation}
											</span>
										</SelectItem>
									))}
								</SelectContent>
							</Select>
						</div>
					</div>

					<DialogFooter className="pt-2">
						<Button
							type="button"
							variant="outline"
							onClick={() => setEditOpen(false)}
							className="border-[#E2E5E8] dark:border-[#2D3D4F]"
						>
							Скасувати
						</Button>
						<Button
							type="button"
							onClick={handleAdminUpdate}
							disabled={isUpdatingAdmin}
							className="bg-[#3D7A8A] text-white hover:bg-[#336678]"
						>
							{isUpdatingAdmin ? "Збереження..." : "Зберегти"}
						</Button>
					</DialogFooter>
				</DialogContent>
			</Dialog>
		</Card>
	);
}
