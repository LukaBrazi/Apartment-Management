import * as z from "zod";

export const issueCreateSchema = z.object({
	title: z.string().trim().min(1, "Заявка повинна мати назву"),
	description: z.string().min(1, "Будь ласка, опишіть проблему"),
	location_note: z.string().optional(),
});

export type TIssueCreateSchema = z.infer<typeof issueCreateSchema>;
