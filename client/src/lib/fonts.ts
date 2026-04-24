// eslint-disable-next-line camelcase
import { Inter, Roboto_Slab } from "next/font/google";

export const inter = Inter({
	subsets: ["latin", "cyrillic", "latin-ext"],
	variable: "--font-inter",
	display: "swap",
});

export const robotoSlab = Roboto_Slab({
	subsets: ["latin"],
	variable: "--font-robotoSlab",
});
