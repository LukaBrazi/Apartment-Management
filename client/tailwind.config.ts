import type { Config } from "tailwindcss";

const config = {
	darkMode: ["class"],
	content: [
		"./pages/**/*.{ts,tsx}",
		"./components/**/*.{ts,tsx}",
		"./app/**/*.{ts,tsx}",
		"./src/**/*.{ts,tsx}",
	],
	prefix: "",
	theme: {
		container: {
			center: true,
			padding: "2rem",
			screens: {
				"2xl": "1400px",
			},
		},
		extend: {
			colors: {
				// SaaS Dashboard Design System
				primary: { DEFAULT: '#2F6FED', hover: '#2460d4', light: '#EEF3FD' },
				saas: { bg: '#F7F8FA', card: '#FFFFFF', text: '#111827', muted: '#6B7280', border: '#E5E7EB' },
				// Legacy (kept for backward compat)
				googleBlue: "#4285F4",
				electricIndigo: "#6610F2",
				richBlack: "#0D1317",
				veryBlack: "#000000",
				babyPowder: "#FBFEF9",
				pumpkin: "#F17105",
				platinum: "#DDE1E4",
				lightGrey: "#EEEEEE",
				eerieBlack: "#171D1C",
				ballonWhite: "#dfe6f6",
				deepBlueGrey: "#263238",
				// Nordic design system
				nordic: {
					navy:     "#1C2B3A",   // primary dark, headings
					teal:     "#3D7A8A",   // accent / CTA
					frost:    "#5BA3B5",   // accent dark mode
					cream:    "#F7F6F2",   // warm off-white bg
					stone:    "#EFEDE6",   // secondary surface light
					ice:      "#EBF3F5",   // teal tint surface
					silver:   "#E2E5E8",   // borders light
					slate:    "#6B7F8C",   // muted / placeholder text
					midnight: "#0F1923",   // dark bg
					charcoal: "#162032",   // dark surface
					dusk:     "#1E2D3D",   // dark elevated
					warm:     "#C9C4BC",   // border dark mode
				},
			},
			borderRadius: {
				"4xl": "2rem",
			},
			keyframes: {
				"accordion-down": {
					from: { height: "0" },
					to: { height: "var(--radix-accordion-content-height)" },
				},
				"accordion-up": {
					from: { height: "var(--radix-accordion-content-height)" },
					to: { height: "0" },
				},
			},
			animation: {
				"accordion-down": "accordion-down 0.2s ease-out",
				"accordion-up": "accordion-up 0.2s ease-out",
			},
			fontFamily: {
				inter: ["var(--font-inter)"],
				openSans: ["var(--font-openSans)"],
				robotoSlab: ["var(--font-robotoSlab)"],
			},
		},
	},
	plugins: [require("tailwindcss-animate")],
} satisfies Config;

export default config;
