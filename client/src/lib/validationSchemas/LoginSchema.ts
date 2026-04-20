import * as z from "zod";

export const loginUserSchema = z.object({
	email: z.string().trim().email({ message: "Enter a valid email address" }),
	password: z
		.string()
		.min(8, { message: "Password must be at least 8 characters long" }),
	/**
	 * When true, the backend issues a 14-day persistent session
	 * (refresh + logged_in cookies get Max-Age=14d). When false or
	 * omitted, cookies are session-only and die on browser close.
	 * The server is the source of truth — this flag is the input.
	 */
	remember_me: z.boolean().optional().default(false),
});

export type TLoginUserSchema = z.infer<typeof loginUserSchema>;
