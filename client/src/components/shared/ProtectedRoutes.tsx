"use client";
import { setAuth, setLogout } from "@/lib/redux/features/auth/authSlice";
import { useAppDispatch } from "@/lib/redux/hooks/typedHooks";
import { getCookie } from "cookies-next";
import { useRouter } from "next/navigation";
import React, { useEffect, useState } from "react";
import Spinner from "@/components/shared/Spinner";

/**
 * Auth state machine:
 *   "checking"      → mount, before cookie read (renders spinner)
 *   "authenticated" → cookie present (renders children)
 *   "redirecting"   → cookie missing, navigation to /login in flight
 *                     (renders spinner — must NOT render children, otherwise
 *                     unauthenticated users briefly see protected pages
 *                     like /welcome before the router.push resolves).
 */
type AuthState = "checking" | "authenticated" | "redirecting";

function ProtectedRoute({ children }: { children: React.ReactNode }) {
	const dispatch = useAppDispatch();
	const router = useRouter();
	const [authState, setAuthState] = useState<AuthState>("checking");

	useEffect(() => {
		const isLoggedIn = getCookie("logged_in") === "true";

		if (isLoggedIn) {
			dispatch(setAuth());
			setAuthState("authenticated");
		} else {
			dispatch(setLogout());
			setAuthState("redirecting");
			router.replace("/login");
		}
	}, [dispatch, router]);

	if (authState !== "authenticated") {
		return (
			<div className="flex-center pt-32">
				<Spinner size="xl" />
			</div>
		);
	}

	return <>{children}</>;
}

export default ProtectedRoute;
