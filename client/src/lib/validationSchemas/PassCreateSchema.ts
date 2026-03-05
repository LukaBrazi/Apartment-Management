import * as z from "zod";

export const passCreateSchema = z.object({
	car_number: z.string().max(20, "Car number is too long").optional(),
	comment: z.string().optional(),
	visit_date: z.string().min(1, "Visit date is required"),
});

export type TPassCreateSchema = z.infer<typeof passCreateSchema>;
