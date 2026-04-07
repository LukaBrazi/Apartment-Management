import { Input } from "@/components/ui/input";
import { PasswordInput } from "@/components/ui/password-input";
import { Textarea } from "@/components/ui/textarea";
import Link from "next/link";
import React from "react";
import {
	FieldErrors,
	FieldValues,
	Path,
	UseFormRegister,
} from "react-hook-form";

type FormFieldComponentProps<TFieldValues extends FieldValues> = {
	label?: string;
	name: Path<TFieldValues>;
	register: UseFormRegister<TFieldValues>;
	errors: FieldErrors<TFieldValues>;
	type?: React.HTMLInputTypeAttribute;
	placeholder?: string;
	required?: boolean;
	startIcon?: React.ReactNode;
	endIcon?: React.ReactNode;
	isPassword?: boolean;
	isTextArea?: boolean;
	link?: {
		linkText: string;
		linkUrl: string;
	};
	className?: string;
	disabled?: boolean;
};
export function FormFieldComponent<TFieldValues extends FieldValues>({
	label,
	name,
	register,
	disabled = false,
	errors,
	type = "text",
	placeholder,
	required = false,
	startIcon,
	endIcon,
	link,
	className,
	isPassword = false,
	isTextArea = false,
}: FormFieldComponentProps<TFieldValues>) {
	const errorMessage = typeof errors[name]?.message === "string" ? errors[name]?.message : undefined;

	const sharedInputClass =
		"rounded-xl border border-[#E2E5E8] bg-white text-[#1C2B3A] placeholder:text-[#6B7F8C] focus:border-[#3D7A8A] focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-[#3D7A8A] dark:border-[#2D3D4F] dark:bg-[#1E2D3D] dark:text-[#F0EDE6] dark:placeholder:text-[#8FA8B8] dark:focus:border-[#5BA3B5] dark:focus-visible:ring-2 dark:focus-visible:ring-offset-2 dark:focus-visible:ring-[#5BA3B5] transition-colors";

	const renderInputComponent = () => {
		if (isTextArea) {
			return (
				<Textarea
					{...register(name, { required })}
					placeholder={placeholder}
					className={`min-h-[100px] ${sharedInputClass} ${className}`}
				/>
			);
		} else if (isPassword) {
			return (
				<PasswordInput
					{...register(name, { required })}
					placeholder={placeholder}
					className={sharedInputClass}
				/>
			);
		} else {
			return (
				<Input
					id={name}
					{...register(name, { required })}
					type={type}
					placeholder={placeholder}
					startIcon={startIcon}
					endIcon={endIcon}
					disabled={disabled}
					className={`${sharedInputClass} ${className}`}
				/>
			);
		}
	};

	return (
		<div className="flex flex-col gap-1.5">
			<div className="flex justify-between items-center">
				<label
					htmlFor={name}
					className="text-sm font-medium text-[#1C2B3A] dark:text-[#F0EDE6]"
				>
					{label}
				</label>
				{link && (
					<Link
						href={link.linkUrl}
						className="text-sm text-[#3D7A8A] hover:text-[#2E6070] dark:text-[#5BA3B5] dark:hover:text-[#4A8FA0] underline-offset-4 hover:underline"
					>
						{link.linkText}
					</Link>
				)}
			</div>
			<div>{renderInputComponent()}</div>
			{errorMessage && (
				<span className="text-xs text-red-500 font-medium">{errorMessage}</span>
			)}
		</div>
	);
}
