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
				electricIndigo: "#6610F2",
				veryBlack: "#000000",
				babyPowder: "#FBFEF9",
				pumpkin: "#F17105",
				platinum: "#DDE1E4",
				lightGrey: "#EEEEEE",
				eerieBlack: "#171D1C",
				deepBlueGrey: "#263238",
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
				robotoSlab: ["var(--font-robotoSlab)"],
			},
		},
	},
	plugins: [require("tailwindcss-animate")],
} satisfies Config;

export default config;
