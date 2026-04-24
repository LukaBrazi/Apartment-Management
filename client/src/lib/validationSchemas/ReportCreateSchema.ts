import * as z from "zod";

export const reportCreateSchema = z.object({
	title: z.string().trim().min(1, "Вкажіть назву скарги"),
	description: z.string().min(1, "Опишіть ситуацію"),
	reported_person_name: z
		.string()
		.min(1, "Вкажіть ім'я або опис особи (квартира, посада тощо)"),
});

export type TReportCreateSchema = z.infer<typeof reportCreateSchema>;
