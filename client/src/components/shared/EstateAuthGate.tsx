"use client";

import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import ProtectedRoute from "./ProtectedRoutes";

/**
 * EstateAuthGate — централізований auth-захист усіх сторінок під
 * `(estate)/`. Виклик відбувається один раз у `(estate)/layout.tsx`,
 * тож окремі сторінки більше не зобовʼязані памʼятати про обгортку
 * в `<ProtectedRoute>` — новий файл автоматично захищений.
 *
 * Публічні маршрути (login / forgot-password / password-reset) живуть
 * всередині `(estate)/(auth)/` та мають бути пропущені без перевірки,
 * інакше користувач застрягне в нескінченному редіректі `/login → /login`.
 */
const PUBLIC_PATH_PREFIXES = [
	"/login",
	"/forgot-password",
	"/password-reset",
	"/activation",
];

export default function EstateAuthGate({ children }: { children: ReactNode }) {
	const pathname = usePathname() ?? "";
	const isPublic = PUBLIC_PATH_PREFIXES.some((prefix) =>
		pathname.startsWith(prefix),
	);

	if (isPublic) {
		return <>{children}</>;
	}

	return <ProtectedRoute>{children}</ProtectedRoute>;
}
