import * as z from "zod";

export const postSchema = z.object({
	title: z.string().trim().min(1, "Заголовок публікації є обов'язковим"),
	tags: z.array(z.string()).min(1, "Додайте щонайменше один тег"),
	body: z.string().min(1, "Текст публікації є обов'язковим"),
});

export type TPostSchema = z.infer<typeof postSchema>;
