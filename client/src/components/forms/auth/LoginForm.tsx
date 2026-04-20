"use client";
import * as z from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { useLoginUserMutation } from "@/lib/redux/features/auth/authApiSlice";
import { useRouter } from "next/navigation";
import { useAppDispatch } from "@/lib/redux/hooks/typedHooks";
import { useForm } from "react-hook-form";
import { useState } from "react";
import { loginUserSchema, TLoginUserSchema } from "@/lib/validationSchemas";
import { extractErrorMessage } from "@/utils";
import { toast } from "react-toastify";
import { setAuth } from "@/lib/redux/features/auth/authSlice";
import Link from "next/link";
import { MailIcon, LockIcon, EyeIcon, EyeOffIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import Spinner from "@/components/shared/Spinner";
import { cn } from "@/lib/utils";

/**
 * Login form — icons sit INSIDE each input (absolute-positioned leading
 * adornment) rather than as sibling flex items, so email + password
 * fields line up cleanly instead of producing the staircase effect the
 * previous shared `FormFieldComponent` caused when one field had a
 * startIcon and the other didn't.
 *
 * This component is deliberately self-contained (no `FormFieldComponent`)
 * so we can change the auth look-and-feel without risking the dozen
 * other forms that still lean on the shared helper.
 */
export default function LoginForm() {
	const [loginUser, { isLoading }] = useLoginUserMutation();
	const router = useRouter();
	const dispatch = useAppDispatch();
	const [showPassword, setShowPassword] = useState(false);

	const {
		register,
		handleSubmit,
		reset,
		formState: { errors },
	} = useForm<TLoginUserSchema>({
		resolver: zodResolver(loginUserSchema),
		mode: "all",
		defaultValues: {
			email: "",
			password: "",
			remember_me: false,
		},
	});

	const onSubmit = async (values: z.infer<typeof loginUserSchema>) => {
		try {
			await loginUser(values).unwrap();
			dispatch(setAuth());
			toast.success("Вхід успішний");
			router.push("/welcome");
			reset();
		} catch (error) {
			const errorMessage = extractErrorMessage(error);
			if (
				errorMessage?.toLowerCase().includes("unable to log in") ||
				errorMessage?.toLowerCase().includes("credentials")
			) {
				toast.error(
					"Неправильний email або пароль, або акаунт ще не активовано. Перевірте пошту для посилання активації."
				);
			} else {
				toast.error(errorMessage || "Помилка входу. Спробуйте ще раз.");
			}
		}
	};

	const inputBase =
		"block h-12 w-full rounded-xl border border-[#E2E5E8] bg-white pl-11 pr-4 text-sm text-[#1C2B3A] placeholder:text-[#6B7F8C] shadow-sm transition-colors focus:border-[#3D7A8A] focus:outline-none focus:ring-4 focus:ring-[#3D7A8A]/15 dark:border-[#2D3D4F] dark:bg-[#1E2D3D] dark:text-[#F0EDE6] dark:placeholder:text-[#8FA8B8] dark:focus:border-[#5BA3B5] dark:focus:ring-[#5BA3B5]/25";

	return (
		<form
			noValidate
			onSubmit={handleSubmit(onSubmit)}
			className="flex w-full flex-col gap-5"
		>
			{/* Email */}
			<div className="flex flex-col gap-1.5">
				<label
					htmlFor="login-email"
					className="text-sm font-medium text-[#1C2B3A] dark:text-[#F0EDE6]"
				>
					Електронна адреса
				</label>
				<div className="relative">
					<MailIcon
						aria-hidden
						className="pointer-events-none absolute left-3.5 top-1/2 size-5 -translate-y-1/2 text-[#6B7F8C] dark:text-[#8FA8B8]"
					/>
					<input
						id="login-email"
						type="email"
						autoComplete="email"
						placeholder="you@apartmentos.org"
						{...register("email")}
						className={cn(inputBase)}
					/>
				</div>
				{errors.email?.message && (
					<span className="text-xs font-medium text-red-500">
						{errors.email.message as string}
					</span>
				)}
			</div>

			{/* Password */}
			<div className="flex flex-col gap-1.5">
				<div className="flex items-center justify-between">
					<label
						htmlFor="login-password"
						className="text-sm font-medium text-[#1C2B3A] dark:text-[#F0EDE6]"
					>
						Пароль
					</label>
					<Link
						href="/forgot-password"
						className="text-sm font-medium text-[#3D7A8A] underline-offset-4 hover:underline dark:text-[#5BA3B5]"
					>
						Забули пароль?
					</Link>
				</div>
				<div className="relative">
					<LockIcon
						aria-hidden
						className="pointer-events-none absolute left-3.5 top-1/2 size-5 -translate-y-1/2 text-[#6B7F8C] dark:text-[#8FA8B8]"
					/>
					<input
						id="login-password"
						type={showPassword ? "text" : "password"}
						autoComplete="current-password"
						placeholder="••••••••"
						{...register("password")}
						className={cn(inputBase, "pr-11")}
					/>
					<button
						type="button"
						tabIndex={-1}
						onClick={() => setShowPassword((v) => !v)}
						aria-label={showPassword ? "Сховати пароль" : "Показати пароль"}
						className="absolute right-2 top-1/2 -translate-y-1/2 rounded-md p-2 text-[#6B7F8C] transition hover:text-[#1C2B3A] dark:text-[#8FA8B8] dark:hover:text-[#F0EDE6]"
					>
						{showPassword ? (
							<EyeIcon className="size-5" />
						) : (
							<EyeOffIcon className="size-5" />
						)}
					</button>
				</div>
				{errors.password?.message && (
					<span className="text-xs font-medium text-red-500">
						{errors.password.message as string}
					</span>
				)}
			</div>

			{/* Remember me — drives the 14-day persistent-session cookie. The
			    flag is sent to the backend as `remember_me` and baked into
			    the refresh JWT as a `remember: true` claim so it survives
			    rotation. Default unchecked is intentional: shared devices
			    must not opt into 14-day persistence silently. */}
			<label
				htmlFor="login-remember-me"
				className="-mt-1 flex cursor-pointer select-none items-center gap-2.5"
			>
				<input
					id="login-remember-me"
					type="checkbox"
					{...register("remember_me")}
					className="size-4 rounded border-[#E2E5E8] text-[#3D7A8A] focus:ring-2 focus:ring-[#3D7A8A]/30 focus:ring-offset-0 dark:border-[#2D3D4F] dark:bg-[#1E2D3D] dark:text-[#5BA3B5] dark:focus:ring-[#5BA3B5]/40"
				/>
				<span className="text-sm text-[#1C2B3A] dark:text-[#F0EDE6]">
					Запам&apos;ятати мене на 14 днів
				</span>
			</label>

			<Button
				type="submit"
				disabled={isLoading}
				className="mt-1 h-12 w-full rounded-xl bg-[#1C2B3A] text-base font-semibold text-white shadow-sm transition-all hover:bg-[#243647] hover:shadow-md disabled:opacity-60 dark:bg-[#5BA3B5] dark:hover:bg-[#4A8FA0]"
			>
				{isLoading ? <Spinner size="sm" /> : "Увійти"}
			</Button>
		</form>
	);
}
