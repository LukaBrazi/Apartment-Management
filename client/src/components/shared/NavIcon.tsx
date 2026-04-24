import {
	Building2,
	ClipboardList,
	CreditCard,
	Megaphone,
	Phone,
	LayoutDashboard,
	ShieldCheck,
	Plus,
	Car,
	Settings,
	Bookmark,
} from "lucide-react";
import React from "react";

const iconMap: Record<string, React.ComponentType<{ className?: string; style?: React.CSSProperties }>> = {
	"/welcome":                Building2,
	"/profile":                ClipboardList,
	"/profile?tab=my-issues":  ClipboardList,
	"/payments":               CreditCard,
	"/announcements":          Megaphone,
	"/news":                   Megaphone,
	"/contacts":               Phone,
	"/admin":                  Settings,
	"/request-pass":           Car,
	"/my-passes":              Car,
	"/guard-portal":           ShieldCheck,
	"/report-issue":           Plus,
	"/bookmark":               Bookmark,
};

export function NavIcon({
	path,
	className,
	style,
}: {
	path: string;
	className?: string;
	style?: React.CSSProperties;
}) {
	const Icon = iconMap[path] ?? LayoutDashboard;
	return <Icon className={className ?? "size-5"} style={style} />;
}
