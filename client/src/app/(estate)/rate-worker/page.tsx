"use client";

import { useState } from "react";
import { Star, CheckCircle, UserCog, CalendarDays } from "lucide-react";
import { toast } from "react-toastify";
import ProtectedRoute from "@/components/shared/ProtectedRoutes";
import Spinner from "@/components/shared/Spinner";
import {
	useGetMyReviewableIssuesQuery,
	useReviewIssueMutation,
} from "@/lib/redux/features/issues/issueApiSlice";
import { ReviewableIssue } from "@/types";

// ── Star selector ────────────────────────────────────────────────────────────

function StarSelector({
	value,
	onChange,
}: {
	value: number;
	onChange: (v: number) => void;
}) {
	const [hovered, setHovered] = useState(0);
	return (
		<div className="flex gap-1">
			{[1, 2, 3, 4, 5].map((star) => (
				<button
					key={star}
					type="button"
					onClick={() => onChange(star)}
					onMouseEnter={() => setHovered(star)}
					onMouseLeave={() => setHovered(0)}
					className="transition-transform hover:scale-110"
					aria-label={`${star} зірок`}
				>
					<Star
						className={`h-7 w-7 transition-colors ${
							star <= (hovered || value)
								? "fill-amber-400 text-amber-400"
								: "fill-none text-gray-300 dark:text-gray-600"
						}`}
					/>
				</button>
			))}
		</div>
	);
}

function StarReadOnly({ value }: { value: number }) {
	return (
		<div className="flex gap-0.5">
			{[1, 2, 3, 4, 5].map((star) => (
				<Star
					key={star}
					className={`h-5 w-5 ${
						star <= value
							? "fill-amber-400 text-amber-400"
							: "fill-none text-gray-300 dark:text-gray-600"
					}`}
				/>
			))}
		</div>
	);
}

// ── Issue card ───────────────────────────────────────────────────────────────

function IssueCard({ issue }: { issue: ReviewableIssue }) {
	const [rating, setRating] = useState(0);
	const [comment, setComment] = useState("");
	const [reviewIssue, { isLoading }] = useReviewIssueMutation();

	const dateLabel = issue.resolved_on
		? new Date(issue.resolved_on).toLocaleDateString("uk-UA", {
				day: "numeric",
				month: "long",
				year: "numeric",
		  })
		: new Date(issue.created_at).toLocaleDateString("uk-UA", {
				day: "numeric",
				month: "long",
				year: "numeric",
		  });

	const handleSubmit = async () => {
		if (rating === 0) {
			toast.error("Оберіть оцінку від 1 до 5 зірок");
			return;
		}
		try {
			await reviewIssue({ issueId: issue.id, rating, comment }).unwrap();
			toast.success("Оцінку надіслано — дякуємо!");
		} catch {
			toast.error("Не вдалося надіслати оцінку. Спробуйте ще раз.");
		}
	};

	const isRated = !!issue.my_review;

	return (
		<div
			className={`overflow-hidden rounded-2xl border bg-white shadow-sm transition-colors dark:bg-[#162032] ${
				isRated
					? "border-[#D1FAE5] dark:border-[#1A3A2E]"
					: "border-[#E5E7EB] dark:border-[#2D3D4F]"
			}`}
		>
			{/* Card header */}
			<div
				className={`flex items-start justify-between gap-3 px-5 py-4 ${
					isRated
						? "bg-[#F0FDF4] dark:bg-[#0F2820]"
						: "bg-white dark:bg-[#162032]"
				} border-b border-[#E5E7EB] dark:border-[#2D3D4F]`}
			>
				<div className="min-w-0">
					<p className="truncate text-sm font-semibold text-[#111827] dark:text-[#F0EDE6]">
						{issue.title}
					</p>
					<div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-[#6B7280] dark:text-[#8FA8B8]">
						<span className="flex items-center gap-1">
							<UserCog className="h-3.5 w-3.5" />
							{issue.assigned_to_name || issue.assigned_to_username}
						</span>
						<span className="flex items-center gap-1">
							<CalendarDays className="h-3.5 w-3.5" />
							{dateLabel}
						</span>
					</div>
				</div>
				{isRated && (
					<div className="flex flex-shrink-0 items-center gap-1.5 rounded-full bg-[#D1FAE5] px-2.5 py-1 text-xs font-medium text-[#065F46]">
						<CheckCircle className="h-3.5 w-3.5" />
						Оцінено
					</div>
				)}
			</div>

			{/* Card body */}
			<div className="px-5 py-4">
				{isRated ? (
					// Read-only state
					<div className="space-y-2">
						<StarReadOnly value={issue.my_review!.rating} />
						{issue.my_review!.comment && (
							<p className="text-sm text-[#374151] dark:text-[#A0B3C1]">
								{issue.my_review!.comment}
							</p>
						)}
					</div>
				) : (
					// Rating form
					<div className="space-y-3">
						<StarSelector value={rating} onChange={setRating} />
						<textarea
							value={comment}
							onChange={(e) => setComment(e.target.value)}
							placeholder="Коментар (необов'язково)"
							rows={2}
							className="w-full resize-none rounded-xl border border-[#E2E8F0] bg-[#F8FAFC] px-3 py-2 text-sm text-[#374151] outline-none placeholder:text-[#94A3B8] focus:border-[#CADCFC] focus:ring-2 focus:ring-[#CADCFC]/30 dark:border-[#2D3D4F] dark:bg-[#1C2B3A] dark:text-gray-200"
						/>
						<button
							onClick={handleSubmit}
							disabled={isLoading || rating === 0}
							className="flex items-center gap-2 rounded-xl bg-[#1E2761] px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-[#2d3a8c] disabled:cursor-not-allowed disabled:opacity-50 dark:bg-[#CADCFC] dark:text-[#1E2761] dark:hover:bg-[#b8ccf8]"
						>
							{isLoading ? (
								<Spinner size="sm" />
							) : (
								<>
									<Star className="h-4 w-4" />
									Надіслати оцінку
								</>
							)}
						</button>
					</div>
				)}
			</div>
		</div>
	);
}

// ── Page ─────────────────────────────────────────────────────────────────────

function RateWorkerContent() {
	const { data: issues, isLoading, isError } = useGetMyReviewableIssuesQuery();

	if (isLoading) {
		return (
			<div className="flex justify-center pt-20">
				<Spinner size="xl" />
			</div>
		);
	}

	if (isError) {
		return (
			<div className="flex justify-center pt-20">
				<p className="text-sm text-red-500">Помилка завантаження. Спробуйте оновити сторінку.</p>
			</div>
		);
	}

	const pending = (issues ?? []).filter((i) => !i.my_review);
	const rated = (issues ?? []).filter((i) => !!i.my_review);

	return (
		<div className="mx-auto max-w-2xl space-y-6 px-4 py-6">
			{/* Page header */}
			<div>
				<h1 className="text-xl font-bold text-[#111827] dark:text-[#F0EDE6]">
					Оцінити майстра
				</h1>
				<p className="mt-1 text-sm text-[#6B7280] dark:text-[#8FA8B8]">
					Ваші відгуки допомагають покращити якість сервісу
				</p>
			</div>

			{/* Empty state */}
			{(issues ?? []).length === 0 && (
				<div className="flex flex-col items-center justify-center gap-3 rounded-2xl border border-dashed border-[#E5E7EB] py-16 text-center dark:border-[#2D3D4F]">
					<Star className="h-10 w-10 text-[#D1D5DB] dark:text-[#3D5166]" />
					<p className="text-sm font-medium text-[#374151] dark:text-[#A0B3C1]">
						Виконаних заявок з призначеним майстром поки немає
					</p>
					<p className="text-xs text-[#9CA3AF]">
						Тут з'являться заявки після їх виконання
					</p>
				</div>
			)}

			{/* Pending reviews */}
			{pending.length > 0 && (
				<section className="space-y-3">
					<h2 className="text-sm font-semibold uppercase tracking-wide text-[#6B7280] dark:text-[#8FA8B8]">
						Очікують оцінки — {pending.length}
					</h2>
					{pending.map((issue) => (
						<IssueCard key={issue.id} issue={issue} />
					))}
				</section>
			)}

			{/* Already rated */}
			{rated.length > 0 && (
				<section className="space-y-3">
					<h2 className="text-sm font-semibold uppercase tracking-wide text-[#6B7280] dark:text-[#8FA8B8]">
						Вже оцінено — {rated.length}
					</h2>
					{rated.map((issue) => (
						<IssueCard key={issue.id} issue={issue} />
					))}
				</section>
			)}
		</div>
	);
}

export default function RateWorkerPage() {
	return (
		<ProtectedRoute>
			<RateWorkerContent />
		</ProtectedRoute>
	);
}
