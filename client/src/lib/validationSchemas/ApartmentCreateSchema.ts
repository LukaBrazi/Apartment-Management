import * as z from "zod";

export const apartmentCreateSchema = z.object({
	unit_number: z.string().trim().min(1, "Номер квартири є обов'язковим"),
	building: z.string().trim().min(1, "Оберіть будинок зі списку"),
	floor: z
		.number()
		.nonnegative({ message: "Поверх не може бути від'ємним" })
		.max(50, { message: "Поверх не може бути більше 50" }),
});

export type TApartmentCreateSchema = z.infer<typeof apartmentCreateSchema>;
