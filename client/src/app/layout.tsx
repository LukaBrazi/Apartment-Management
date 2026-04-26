import { ThemeProvider } from "@/components/theme-provider";
import { inter, robotoSlab } from "@/lib/fonts";
import type { Metadata, Viewport } from "next";
import React from "react";
import "./globals.css";

import Toast from "@/components/shared/Toast";
import ReduxProvider from "@/lib/redux/provider";
import { PersistAuth } from "@/utils";

export const metadata: Metadata = {
	title: "Home | ApartmentOS",
	description: "Welcome home",
};

// Mobile-first viewport config. `viewport-fit=cover` is required so the
// browser reports env(safe-area-inset-*) values on iPhone notch / Dynamic
// Island devices; the bottom tab bar uses that inset to stay clear of the
// system gesture area. `maximumScale: 1` intentionally omitted so users
// can still pinch-zoom for accessibility (WCAG 1.4.4).
export const viewport: Viewport = {
	width: "device-width",
	initialScale: 1,
	viewportFit: "cover",
	themeColor: [
		{ media: "(prefers-color-scheme: light)", color: "#FFFFFF" },
		{ media: "(prefers-color-scheme: dark)",  color: "#0F1923" },
	],
};

export default function RootLayout({
	children,
}: Readonly<{
	children: React.ReactNode;
}>) {
	return (
		<html lang="uk" suppressHydrationWarning>
			<body className={`${inter.variable} ${robotoSlab.variable} font-inter antialiased`}>
				<Toast />
				<ReduxProvider>
					<PersistAuth />
					<ThemeProvider
						attribute="class"
						defaultTheme="system"
						enableSystem
						disableTransitionOnChange
					>
						{children}
					</ThemeProvider>
				</ReduxProvider>
			</body>
		</html>
	);
}
