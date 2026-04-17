import { ThemeProvider } from "@/components/theme-provider";
import { inter, robotoSlab } from "@/lib/fonts";
import type { Metadata } from "next";
import React from "react";
import "./globals.css";

import Toast from "@/components/shared/Toast";
import ReduxProvider from "@/lib/redux/provider";
import { PersistAuth } from "@/utils";

export const metadata: Metadata = {
	title: "Home | ApartmentOS",
	description: "Welcome home",
};

export default function RootLayout({
	children,
}: Readonly<{
	children: React.ReactNode;
}>) {
	return (
		<html lang="en" suppressHydrationWarning>
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
