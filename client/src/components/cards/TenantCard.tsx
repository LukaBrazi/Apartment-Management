"use client";
import { useGetAllUsersQuery } from "@/lib/redux/features/users/usersApiSlice";
import { useAppSelector } from "@/lib/redux/hooks/typedHooks";
import { formatDate } from "@/utils";
import { Users } from "lucide-react";
import ProtectedRoute from "../shared/ProtectedRoutes";
import PaginationSection from "../shared/PaginationSection";
import UsersSearch from "../shared/search/UsersSearch";
import { Avatar, AvatarFallback, AvatarImage } from "../ui/avatar";
import { Badge } from "../ui/badge";
import { Skeleton } from "../ui/skeleton";
import type { Profile } from "@/types";

const OCCUPATION_LABELS: Record<string, string> = {
	tenant: "Мешканець",
	mason: "Муляр",
	carpenter: "Тесля",
	plumber: "Сантехнік",
	roofer: "Покрівельник",
	painter: "Маляр",
	electrician: "Електрик",
	hvac: "Вентиляція",
	guard: "Охоронець",
	dispatcher: "Диспетчер",
};

const OCCUPATION_VARIANT: Record<
	string,
	"default" | "secondary" | "outline" | "destructive"
> = {
	tenant: "secondary",
	guard: "outline",
};

function occupationVariant(
	occ: string,
): "default" | "secondary" | "outline" | "destructive" {
	return OCCUPATION_VARIANT[occ] ?? "default";
}

function TenantRow({ tenant }: { tenant: Profile }) {
	const initials = `${tenant.first_name?.[0] ?? ""}${tenant.last_name?.[0] ?? ""}`.toUpperCase();

	return (
		<tr className="border-b border-[--border] transition-colors hover:bg-[--bg-stone]">
			{/* Name + avatar */}
			<td className="px-4 py-3">
				<div className="flex items-center gap-3">
					<Avatar className="size-9 shrink-0">
						<AvatarImage src={tenant.avatar} alt={tenant.full_name} />
						<AvatarFallback className="bg-[--accent-light] text-[--accent] text-xs font-semibold">
							{initials || "?"}
						</AvatarFallback>
					</Avatar>
					<div className="min-w-0">
						<p className="truncate text-sm font-semibold text-[--text-primary]">
							{tenant.full_name}
						</p>
						<p className="truncate text-xs text-[--text-muted]">
							@{tenant.username}
						</p>
					</div>
				</div>
			</td>

			{/* Occupation */}
			<td className="px-4 py-3">
				<Badge variant={occupationVariant(tenant.occupation)}>
					{OCCUPATION_LABELS[tenant.occupation] ?? tenant.occupation}
				</Badge>
			</td>

			{/* Country */}
			<td className="hidden px-4 py-3 text-sm text-[--text-muted] md:table-cell">
				{tenant.country_of_origin || "—"}
			</td>

			{/* Unit — PR-4: read from canonical profile.unit_* fields. */}
			<td className="hidden px-4 py-3 text-sm text-[--text-muted] lg:table-cell">
				{tenant.unit_number ? (
					<span>
						<span className="font-medium text-[--text-primary]">
							кв.&nbsp;{tenant.unit_number}
						</span>
						{tenant.building_name && (
							<span className="ml-1 text-xs text-[--text-muted]">
								· {tenant.building_name}
							</span>
						)}
					</span>
				) : (
					<span className="text-xs text-[--text-muted]">не вказано</span>
				)}
			</td>

			{/* Date joined */}
			<td className="hidden px-4 py-3 text-sm text-[--text-muted] xl:table-cell">
				{formatDate(tenant.date_joined).toString()}
			</td>
		</tr>
	);
}

function SkeletonRows() {
	return (
		<>
			{Array.from({ length: 6 }).map((_, i) => (
				<tr key={i} className="border-b border-[--border]">
					<td className="px-4 py-3">
						<div className="flex items-center gap-3">
							<Skeleton className="size-9 rounded-full" />
							<div className="space-y-1.5">
								<Skeleton className="h-3.5 w-32" />
								<Skeleton className="h-3 w-20" />
							</div>
						</div>
					</td>
					<td className="px-4 py-3">
						<Skeleton className="h-5 w-20 rounded-full" />
					</td>
					<td className="hidden px-4 py-3 md:table-cell">
						<Skeleton className="h-3.5 w-16" />
					</td>
					<td className="hidden px-4 py-3 lg:table-cell">
						<Skeleton className="h-3.5 w-24" />
					</td>
					<td className="hidden px-4 py-3 xl:table-cell">
						<Skeleton className="h-3.5 w-24" />
					</td>
				</tr>
			))}
		</>
	);
}

function TenantCardContent() {
	const searchTerm = useAppSelector((state) => state.user.searchTerm);
	const page = useAppSelector((state) => state.user.page);

	const { data, isLoading } = useGetAllUsersQuery({ searchTerm, page });

	const total = data?.profiles.count ?? 0;
	const totalPages = Math.ceil(total / 9);

	return (
		<div className="space-y-4">
			{/* Page header */}
			<div className="flex items-center justify-between">
				<div className="flex items-center gap-2">
					<Users className="size-5 text-[--accent]" />
					<h1 className="text-xl font-semibold text-[--text-primary]">
						Мешканці
					</h1>
					{!isLoading && (
						<Badge variant="secondary" className="ml-1">
							{total}
						</Badge>
					)}
				</div>
			</div>

			{/* Search */}
			<UsersSearch />

			{/* Mobile cards (< lg) — PR-17 mobile-first: stacked card list
			    replaces the horizontal table on narrow viewports.  Avatar +
			    name go top, role/unit/country wrap underneath. */}
			<div className="lg:hidden space-y-3">
				{isLoading ? (
					Array.from({ length: 6 }).map((_, i) => (
						<div
							key={i}
							className="rounded-lg border border-[--border] bg-[--bg-surface] p-4 space-y-2 animate-pulse"
						>
							<div className="flex items-center gap-3">
								<Skeleton className="size-9 rounded-full" />
								<div className="space-y-1.5 flex-1">
									<Skeleton className="h-3.5 w-32" />
									<Skeleton className="h-3 w-20" />
								</div>
							</div>
							<Skeleton className="h-3.5 w-24" />
						</div>
					))
				) : data && data.profiles.results.length > 0 ? (
					data.profiles.results.map((tenant) => {
						const initials = `${tenant.first_name?.[0] ?? ""}${tenant.last_name?.[0] ?? ""}`.toUpperCase();
						return (
							<div
								key={tenant.id}
								className="rounded-lg border border-[--border] bg-[--bg-surface] p-4 space-y-3"
							>
								<div className="flex items-center gap-3">
									<Avatar className="size-10 shrink-0">
										<AvatarImage src={tenant.avatar} alt={tenant.full_name} />
										<AvatarFallback className="bg-[--accent-light] text-[--accent] text-xs font-semibold">
											{initials || "?"}
										</AvatarFallback>
									</Avatar>
									<div className="min-w-0 flex-1">
										<p className="truncate text-sm font-semibold text-[--text-primary]">
											{tenant.full_name}
										</p>
										<p className="truncate text-xs text-[--text-muted]">
											@{tenant.username}
										</p>
									</div>
									<Badge variant={occupationVariant(tenant.occupation)}>
										{OCCUPATION_LABELS[tenant.occupation] ?? tenant.occupation}
									</Badge>
								</div>
								<div className="grid grid-cols-2 gap-2 text-xs text-[--text-muted]">
									<div>
										<span className="block text-[10px] font-semibold uppercase tracking-wider">
											Квартира
										</span>
										<span>
											{tenant.unit_number ? (
												<>
													<span className="font-medium text-[--text-primary]">
														кв.&nbsp;{tenant.unit_number}
													</span>
													{tenant.building_name && (
														<span className="ml-1">
															· {tenant.building_name}
														</span>
													)}
												</>
											) : (
												<span>не вказано</span>
											)}
										</span>
									</div>
									<div>
										<span className="block text-[10px] font-semibold uppercase tracking-wider">
											Країна
										</span>
										<span>{tenant.country_of_origin || "—"}</span>
									</div>
								</div>
								<p className="text-[11px] text-[--text-muted]">
									Зареєстровано: {formatDate(tenant.date_joined).toString()}
								</p>
							</div>
						);
					})
				) : (
					<p className="px-4 py-12 text-center text-sm text-[--text-muted]">
						Мешканців не знайдено
					</p>
				)}
			</div>

			{/* Desktop table (>= lg) */}
			<div className="hidden lg:block overflow-x-auto rounded-lg border border-[--border] bg-[--bg-surface]">
				<table className="w-full text-left text-sm">
					<thead>
						<tr className="border-b border-[--border] bg-[--bg-stone]">
							<th className="px-4 py-3 text-xs font-semibold uppercase tracking-wide text-[--text-muted]">
								Ім&apos;я
							</th>
							<th className="px-4 py-3 text-xs font-semibold uppercase tracking-wide text-[--text-muted]">
								Роль
							</th>
							<th className="hidden px-4 py-3 text-xs font-semibold uppercase tracking-wide text-[--text-muted] md:table-cell">
								Країна
							</th>
							<th className="hidden px-4 py-3 text-xs font-semibold uppercase tracking-wide text-[--text-muted] lg:table-cell">
								Квартира
							</th>
							<th className="hidden px-4 py-3 text-xs font-semibold uppercase tracking-wide text-[--text-muted] xl:table-cell">
								Дата реєстрації
							</th>
						</tr>
					</thead>
					<tbody>
						{isLoading ? (
							<SkeletonRows />
						) : data && data.profiles.results.length > 0 ? (
							data.profiles.results.map((tenant) => (
								<TenantRow key={tenant.id} tenant={tenant} />
							))
						) : (
							<tr>
								<td
									colSpan={5}
									className="px-4 py-12 text-center text-sm text-[--text-muted]"
								>
									Мешканців не знайдено
								</td>
							</tr>
						)}
					</tbody>
				</table>
			</div>

			<PaginationSection totalPages={totalPages} entityType="user" />
		</div>
	);
}

export default function TenantCard() {
	return (
		<ProtectedRoute>
			<TenantCardContent />
		</ProtectedRoute>
	);
}
