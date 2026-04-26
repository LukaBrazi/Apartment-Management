"use client";

import { useState } from "react";
import { toast } from "react-toastify";
import { useSubmitFeedbackMutation } from "@/lib/redux/features/feedback/feedbackApiSlice";

export default function FeedbackForm() {
	const [message, setMessage] = useState("");
	const [submitted, setSubmitted] = useState(false);
	const [submitFeedback, { isLoading }] = useSubmitFeedbackMutation();

	const handleSubmit = async (e: React.FormEvent) => {
		e.preventDefault();

		try {
			await submitFeedback({ message }).unwrap();
			setSubmitted(true);
		} catch (err: any) {
			const status = err?.status;
			if (status === 429) {
				toast.error("Ви надсилаєте повідомлення надто часто. Спробуйте пізніше.");
			} else {
				toast.error("Помилка. Спробуйте ще раз.");
			}
		}
	};

	if (submitted) {
		return (
			<div className="rounded-xl border border-[#E2E8F0] bg-[#F8FAFC] p-6 text-center">
				<p className="text-lg font-medium text-[#0F172A]">Дякуємо за ваш відгук!</p>
				<p className="mt-1 text-sm text-[#6B7280]">
					Ми обов&apos;язково розглянемо його та врахуємо у подальшому розвитку застосунку.
				</p>
				<button
					onClick={() => {
						setSubmitted(false);
						setMessage("");
					}}
					className="mt-4 rounded-xl bg-[#1E2761] px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-[#2d3a8c] dark:bg-[#CADCFC] dark:text-[#1E2761] dark:hover:bg-[#b8ccf8]"
				>
					Надіслати ще одне
				</button>
			</div>
		);
	}

	return (
		<form onSubmit={handleSubmit} className="flex flex-col gap-3">
			<textarea
				value={message}
				onChange={(e) => setMessage(e.target.value)}
				maxLength={2000}
				placeholder="Ваш відгук..."
				rows={5}
				className="w-full resize-none rounded-xl border border-[#E2E8F0] bg-[#F8FAFC] px-3 py-2 text-sm text-[#374151] outline-none placeholder:text-[#94A3B8] focus:border-[#CADCFC] focus:ring-2 focus:ring-[#CADCFC]/30 dark:border-[#2D3D4F] dark:bg-[#1C2B3A] dark:text-gray-200"
			/>
			<div className="flex items-center justify-between">
				<span
					className={`text-xs ${
						message.length > 1900 ? "text-red-500" : "text-[#94A3B8]"
					}`}
				>
					{message.length} / 2000
				</span>
				<button
					type="submit"
					disabled={isLoading || message.length < 10}
					className="rounded-xl bg-[#1E2761] px-5 py-2 text-sm font-medium text-white transition-colors hover:bg-[#2d3a8c] disabled:cursor-not-allowed disabled:opacity-50 dark:bg-[#CADCFC] dark:text-[#1E2761] dark:hover:bg-[#b8ccf8]"
				>
					{isLoading ? "Надсилаємо..." : "Надіслати"}
				</button>
			</div>
		</form>
	);
}
