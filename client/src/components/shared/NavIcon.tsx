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

const iconMap: Record<string, React.ComponentType<{ className?: string }>> = {
	"/welcome":        Building2,
	"/profile":        ClipboardList,
	"/payments":       CreditCard,
	"/announcements":  Megaphone,
	"/contacts":       Phone,
	"/admin":          Settings,
	"/request-pass":   Car,
	"/guard-portal":   ShieldCheck,
	"/report-issue":   Plus,
	"/bookmark":       Bookmark,
};

export function NavIcon({ path, className }: { path: string; className?: string }) {
	const Icon = iconMap[path] ?? LayoutDashboard;
	return <Icon className={className ?? "size-5"} />;
}
