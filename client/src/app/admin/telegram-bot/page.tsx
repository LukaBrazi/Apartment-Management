"use client";

/**
 * Super_admin-only page for managing per-organization Telegram bots
 * (PR-14 phase 6).
 *
 * The Django admin remains the fallback / incident-recovery surface, but
 * the day-to-day workflow is here:
 *   1. Pick an organization from the dropdown that doesn't yet have a
 *      bot (or edit an existing row inline).
 *   2. Paste the ``bot_token`` from BotFather — it's sent once and
 *      stored Fernet-encrypted server-side; the UI only ever shows the
 *      masked preview (``123456789:••••••••XYZ``).
 *   3. Click "Перевірити" to hit ``getMe`` — we compare the returned
 *      username against ``bot_username`` and surface a mismatch as a
 *      failure, because the most common mistake is pasting a token
 *      from a different bot.
 *   4. Click "Встановити webhook" once the bot is healthy.  Requires
 *      ``PLATFORM_PUBLIC_URL`` to be set on the server; the API will
 *      refuse otherwise (400) and we show the error here.
 *
 * Access control: the page is wrapped in ``SuperAdminGuard`` and every
 * endpoint on the API is ``IsSuperAdmin``, so a director who somehow
 * lands on this URL sees a redirect to ``/admin`` rather than a 403
 * rendered page.
 */

import { useMemo, useState } from "react";
import { toast } from "react-toastify";
import { Plus, X, Check, Pencil, Trash2, CheckCircle2, XCircle, Webhook, Link as LinkIcon, AlertTriangle } from "lucide-react";
import { format } from "date-fns";

import SuperAdminGuard from "@/components/admin/SuperAdminGuard";
import {
	useListTelegramBotsQuery,
	useListBotOrganizationsQuery,
	useCreateTelegramBotMutation,
	useUpdateTelegramBotMutation,
	useDeleteTelegramBotMutation,
	useTestTelegramBotMutation,
	useSetTelegramBotWebhookMutation,
	useDeleteTelegramBotWebhookMutation,
} from "@/lib/redux/features/telegramBots/telegramBotsApiSlice";
import {
	OrganizationBot,
	OrganizationBotCreateData,
	OrganizationBotUpdateData,
} from "@/types";
import { extractErrorMessage } from "@/utils";

const inputCls =
	"rounded-xl border border-[#E2E5E8] bg-[#F7F6F2] px-3 py-2 text-sm dark:border-[#2D3D4F] dark:bg-[#1C2B3A] dark:text-white focus:outline-none focus:border-[#3D7A8A] focus:ring-1 focus:ring-[#3D7A8A] w-full";
const labelCls = "text-xs font-medium text-[#6B7F8C]";
const btnPrimaryCls =
	"inline-flex items-center gap-2 rounded-xl bg-[#3D7A8A] px-4 py-2 text-sm font-medium text-white hover:bg-[#2E6070] dark:bg-[#5BA3B5] dark:hover:bg-[#4A8FA0] disabled:opacity-60 transition-colors";
const btnGhostCls =
	"inline-flex items-center gap-1 rounded-lg border border-[#E2E5E8] dark:border-[#2D3D4F] px-3 py-1.5 text-xs font-medium text-[#3D7A8A] hover:bg-[#EBF3F5] dark:hover:bg-[#1A2E3A] transition-colors disabled:opacity-60";

interface CreateFormState {
	organization: number | "";
	bot_username: string;
	bot_token: string;
	is_active: boolean;
	is_primary: boolean;
}

interface EditFormState {
	bot_username: string;
	bot_token: string;
	is_active: boolean;
	is_primary: boolean;
}

const emptyCreate: CreateFormState = {
	organization: "",
	bot_username: "",
	bot_token: "",
	is_active: true,
	is_primary: true,
};

function StatusChip({ configured, ok }: { configured: boolean; ok: boolean | null }) {
	if (!configured) {
		return (
			<span className="inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium bg-slate-100 text-slate-600 dark:bg-slate-800/40 dark:text-slate-400">
				<AlertTriangle className="h-3 w-3" />
				Не налаштовано
			</span>
		);
	}
	if (ok === true) {
		return (
			<span className="inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300">
				<CheckCircle2 className="h-3 w-3" />
				Живий
			</span>
		);
	}
	if (ok === false) {
		return (
			<span className="inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300">
				<XCircle className="h-3 w-3" />
				Помилка
			</span>
		);
	}
	return (
		<span className="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300">
			Не перевірявся
		</span>
	);
}

function TelegramBotAdmin() {
	const { data: listData, isLoading } = useListTelegramBotsQuery();
	const { data: orgsData, isLoading: isLoadingOrgs } =
		useListBotOrganizationsQuery();

	const [createBot, { isLoading: isCreating }] = useCreateTelegramBotMutation();
	const [updateBot, { isLoading: isUpdating }] = useUpdateTelegramBotMutation();
	const [deleteBot, { isLoading: isDeleting }] = useDeleteTelegramBotMutation();
	const [testBot, { isLoading: isTesting }] = useTestTelegramBotMutation();
	const [setWebhook, { isLoading: isSettingWebhook }] =
		useSetTelegramBotWebhookMutation();
	const [deleteWebhook, { isLoading: isDeletingWebhook }] =
		useDeleteTelegramBotWebhookMutation();

	const [showCreateForm, setShowCreateForm] = useState(false);
	const [createForm, setCreateForm] = useState<CreateFormState>(emptyCreate);
	const [createErrors, setCreateErrors] = useState<
		Partial<Record<keyof CreateFormState, string>>
	>({});

	const [editingId, setEditingId] = useState<string | null>(null);
	const [editForm, setEditForm] = useState<EditFormState>({
		bot_username: "",
		bot_token: "",
		is_active: true,
		is_primary: true,
	});

	const [deletingId, setDeletingId] = useState<string | null>(null);
	const [busyRowId, setBusyRowId] = useState<string | null>(null);

	// Freeze array identity off the RTK-Query data blocks — a fresh
	// ``listData?.results ?? []`` on every render would force every
	// downstream ``useMemo`` to recompute forever, which is the exact
	// footgun ESLint is warning about.
	const bots: OrganizationBot[] = useMemo(
		() => listData?.results ?? [],
		[listData],
	);
	const orgs = useMemo(() => orgsData ?? [], [orgsData]);

	// Orgs that don't yet have a bot — lets the dropdown default to the
	// obvious choice (you typically add the bot you *don't* have).  Edit
	// flow is a separate path so this only matters for create.
	const orgsWithoutBot = useMemo(() => {
		const usedPkids = new Set(bots.map((b) => b.organization));
		return orgs.filter((o) => !usedPkids.has(o.pkid));
	}, [bots, orgs]);

	const validateCreate = (): boolean => {
		const errs: Partial<Record<keyof CreateFormState, string>> = {};
		if (!createForm.organization)
			errs.organization = "Виберіть організацію";
		if (!createForm.bot_username.trim())
			errs.bot_username = "Обов'язкове поле";
		if (!createForm.bot_token.trim())
			errs.bot_token = "Обов'язкове поле при створенні";
		setCreateErrors(errs);
		return Object.keys(errs).length === 0;
	};

	const handleCreate = async (e: React.FormEvent) => {
		e.preventDefault();
		if (!validateCreate()) return;
		const payload: OrganizationBotCreateData = {
			organization: createForm.organization as number,
			bot_username: createForm.bot_username.trim().replace(/^@/, ""),
			bot_token: createForm.bot_token.trim(),
			is_active: createForm.is_active,
			is_primary: createForm.is_primary,
		};
		try {
			await createBot(payload).unwrap();
			toast.success("Бот створено");
			setCreateForm(emptyCreate);
			setCreateErrors({});
			setShowCreateForm(false);
		} catch (err) {
			toast.error(extractErrorMessage(err) || "Помилка створення бота");
		}
	};

	const openEdit = (bot: OrganizationBot) => {
		setEditingId(bot.id);
		setEditForm({
			bot_username: bot.bot_username,
			bot_token: "",
			is_active: bot.is_active,
			is_primary: bot.is_primary,
		});
	};

	const handleEdit = async (id: string) => {
		const payload: OrganizationBotUpdateData = {
			bot_username: editForm.bot_username.trim().replace(/^@/, ""),
			is_active: editForm.is_active,
			is_primary: editForm.is_primary,
		};
		// Send token only if the super_admin actually typed one — blank
		// means "keep the existing encrypted value".
		if (editForm.bot_token.trim()) {
			payload.bot_token = editForm.bot_token.trim();
		}
		try {
			await updateBot({ id, ...payload }).unwrap();
			toast.success("Бот оновлено");
			setEditingId(null);
		} catch (err) {
			toast.error(extractErrorMessage(err) || "Помилка оновлення");
		}
	};

	const handleDelete = async (id: string) => {
		try {
			await deleteBot(id).unwrap();
			toast.success("Бот видалено");
			setDeletingId(null);
		} catch (err) {
			toast.error(extractErrorMessage(err) || "Помилка видалення");
		}
	};

	const handleTest = async (bot: OrganizationBot) => {
		setBusyRowId(bot.id);
		try {
			const result = await testBot(bot.id).unwrap();
			if (result.ok) {
				toast.success(`OK — @${result.username || bot.bot_username}`);
			} else {
				toast.error(result.error || "Перевірка не вдалася");
			}
		} catch (err) {
			toast.error(extractErrorMessage(err) || "Помилка перевірки");
		} finally {
			setBusyRowId(null);
		}
	};

	const handleSetWebhook = async (bot: OrganizationBot) => {
		setBusyRowId(bot.id);
		try {
			const result = await setWebhook(bot.id).unwrap();
			toast.success(`Webhook встановлено: ${result.webhook_url}`);
		} catch (err) {
			toast.error(
				extractErrorMessage(err) ||
					"Помилка встановлення webhook (перевірте PLATFORM_PUBLIC_URL)",
			);
		} finally {
			setBusyRowId(null);
		}
	};

	const handleDeleteWebhook = async (bot: OrganizationBot) => {
		setBusyRowId(bot.id);
		try {
			await deleteWebhook(bot.id).unwrap();
			toast.success("Webhook знято (режим polling)");
		} catch (err) {
			toast.error(extractErrorMessage(err) || "Помилка зняття webhook");
		} finally {
			setBusyRowId(null);
		}
	};

	return (
		<div className="space-y-6">
			<div className="flex items-center justify-between">
				<div>
					<h2 className="text-2xl font-bold text-[#1C2B3A] dark:text-white">
						Telegram боти
					</h2>
					<p className="text-[#6B7F8C] text-sm mt-1">
						Налаштування ботів по організаціях. Тільки super_admin.
					</p>
				</div>
				<button
					onClick={() => {
						setCreateForm(emptyCreate);
						setCreateErrors({});
						setShowCreateForm((v) => !v);
					}}
					className={btnPrimaryCls}
				>
					{showCreateForm ? (
						<>
							<X className="h-4 w-4" />
							Скасувати
						</>
					) : (
						<>
							<Plus className="h-4 w-4" />
							Додати бота
						</>
					)}
				</button>
			</div>

			{showCreateForm && (
				<div className="rounded-2xl border border-[#3D7A8A] bg-white p-6 dark:border-[#5BA3B5] dark:bg-[#162032]">
					<h3 className="text-base font-semibold text-[#1C2B3A] dark:text-white mb-4">
						Новий бот
					</h3>
					<form onSubmit={handleCreate} className="space-y-4">
						<div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
							<div className="space-y-1">
								<label className={labelCls}>Організація</label>
								<select
									value={createForm.organization}
									onChange={(e) =>
										setCreateForm((f) => ({
											...f,
											organization: e.target.value
												? Number(e.target.value)
												: "",
										}))
									}
									className={inputCls}
									disabled={isLoadingOrgs}
								>
									<option value="">— Виберіть —</option>
									{orgsWithoutBot.map((o) => (
										<option key={o.pkid} value={o.pkid}>
											{o.name} ({o.slug})
										</option>
									))}
								</select>
								{createErrors.organization && (
									<p className="text-xs text-red-500">
										{createErrors.organization}
									</p>
								)}
								{orgsWithoutBot.length === 0 && !isLoadingOrgs && (
									<p className="text-xs text-[#6B7F8C]">
										У всіх організацій вже є бот — редагуйте існуючий.
									</p>
								)}
							</div>
							<div className="space-y-1">
								<label className={labelCls}>
									Username бота (без @)
								</label>
								<input
									value={createForm.bot_username}
									onChange={(e) =>
										setCreateForm((f) => ({
											...f,
											bot_username: e.target.value,
										}))
									}
									placeholder="MyOrgBot"
									className={inputCls}
								/>
								{createErrors.bot_username && (
									<p className="text-xs text-red-500">
										{createErrors.bot_username}
									</p>
								)}
							</div>
							<div className="space-y-1 sm:col-span-2">
								<label className={labelCls}>
									Токен з BotFather
								</label>
								<input
									type="password"
									autoComplete="new-password"
									value={createForm.bot_token}
									onChange={(e) =>
										setCreateForm((f) => ({
											...f,
											bot_token: e.target.value,
										}))
									}
									placeholder="123456789:AAE-xxxxxxxxxxxxxxxxxxxxxxxxxxxx"
									className={inputCls}
								/>
								{createErrors.bot_token && (
									<p className="text-xs text-red-500">
										{createErrors.bot_token}
									</p>
								)}
								<p className="text-xs text-[#6B7F8C]">
									Зберігається зашифровано (Fernet). Відображається маскованим.
								</p>
							</div>
							<div className="flex items-center gap-3">
								<button
									type="button"
									role="switch"
									aria-checked={createForm.is_active}
									onClick={() =>
										setCreateForm((f) => ({
											...f,
											is_active: !f.is_active,
										}))
									}
									className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors focus-visible:outline-none ${
										createForm.is_active
											? "bg-[#3D7A8A]"
											: "bg-[#E2E5E8] dark:bg-[#2D3D4F]"
									}`}
								>
									<span
										className={`inline-block h-3.5 w-3.5 transform rounded-full bg-white transition-transform ${
											createForm.is_active
												? "translate-x-[18px]"
												: "translate-x-0.5"
										}`}
									/>
								</button>
								<span className="text-sm text-[#1C2B3A] dark:text-[#D1DCE5]">
									Активний
								</span>
							</div>
							<div className="flex items-center gap-3">
								<button
									type="button"
									role="switch"
									aria-checked={createForm.is_primary}
									onClick={() =>
										setCreateForm((f) => ({
											...f,
											is_primary: !f.is_primary,
										}))
									}
									className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors focus-visible:outline-none ${
										createForm.is_primary
											? "bg-[#3D7A8A]"
											: "bg-[#E2E5E8] dark:bg-[#2D3D4F]"
									}`}
								>
									<span
										className={`inline-block h-3.5 w-3.5 transform rounded-full bg-white transition-transform ${
											createForm.is_primary
												? "translate-x-[18px]"
												: "translate-x-0.5"
										}`}
									/>
								</button>
								<span className="text-sm text-[#1C2B3A] dark:text-[#D1DCE5]">
									Основний (webhook піде на нього)
								</span>
							</div>
						</div>
						<div className="flex justify-end">
							<button
								type="submit"
								disabled={isCreating}
								className={btnPrimaryCls}
							>
								{isCreating ? "Створення..." : "Створити"}
							</button>
						</div>
					</form>
				</div>
			)}

			<div className="bg-white dark:bg-[#162032] rounded-xl border border-[#E2E5E8] dark:border-[#2D3D4F] shadow-sm overflow-hidden">
				{isLoading ? (
					<div className="p-12 text-center text-[#6B7F8C] text-sm">
						Завантаження...
					</div>
				) : bots.length === 0 ? (
					<div className="p-12 text-center text-[#6B7F8C] text-sm">
						Ще немає жодного бота. Натисніть «Додати бота» щоб почати.
					</div>
				) : (
					<div className="overflow-x-auto">
						<table className="w-full text-sm">
							<thead className="bg-[#F7F6F2] dark:bg-[#1C2B3A] text-left text-xs text-[#6B7F8C] uppercase">
								<tr>
									<th className="px-4 py-3 font-medium">Організація</th>
									<th className="px-4 py-3 font-medium">Бот</th>
									<th className="px-4 py-3 font-medium">Токен</th>
									<th className="px-4 py-3 font-medium">Статус</th>
									<th className="px-4 py-3 font-medium">Остання перевірка</th>
									<th className="px-4 py-3 font-medium">Дії</th>
								</tr>
							</thead>
							<tbody className="divide-y divide-[#E2E5E8] dark:divide-[#2D3D4F]">
								{bots.map((bot) => {
									const isEditing = editingId === bot.id;
									const isDeletingRow = deletingId === bot.id;
									const rowBusy =
										busyRowId === bot.id &&
										(isTesting || isSettingWebhook || isDeletingWebhook);

									return (
										<tr
											key={bot.id}
											className="hover:bg-[#F7F6F2]/60 dark:hover:bg-[#1C2B3A]/40"
										>
											<td className="px-4 py-3 align-top">
												<div className="font-medium text-[#1C2B3A] dark:text-white">
													{bot.organization_name}
												</div>
												<div className="text-xs text-[#6B7F8C]">
													{bot.organization_slug}
												</div>
											</td>
											<td className="px-4 py-3 align-top">
												{isEditing ? (
													<input
														value={editForm.bot_username}
														onChange={(e) =>
															setEditForm((f) => ({
																...f,
																bot_username: e.target.value,
															}))
														}
														className={inputCls}
													/>
												) : (
													<div className="flex flex-col">
														<span className="font-mono text-[#1C2B3A] dark:text-white">
															@{bot.bot_username}
														</span>
														<span className="text-xs text-[#6B7F8C] flex items-center gap-1 mt-0.5">
															{bot.is_primary && (
																<span className="inline-flex items-center rounded px-1.5 py-0.5 text-[10px] font-medium bg-[#EBF3F5] text-[#3D7A8A] dark:bg-[#1A2E3A] dark:text-[#5BA3B5]">
																	primary
																</span>
															)}
															{!bot.is_active && (
																<span className="inline-flex items-center rounded px-1.5 py-0.5 text-[10px] font-medium bg-slate-100 text-slate-600 dark:bg-slate-800/40 dark:text-slate-400">
																	paused
																</span>
															)}
														</span>
													</div>
												)}
											</td>
											<td className="px-4 py-3 align-top">
												{isEditing ? (
													<input
														type="password"
														autoComplete="new-password"
														value={editForm.bot_token}
														onChange={(e) =>
															setEditForm((f) => ({
																...f,
																bot_token: e.target.value,
															}))
														}
														placeholder="(залишити як є)"
														className={inputCls}
													/>
												) : (
													<span className="font-mono text-xs text-[#6B7F8C]">
														{bot.bot_token_masked || "—"}
													</span>
												)}
											</td>
											<td className="px-4 py-3 align-top">
												<StatusChip
													configured={bot.is_configured}
													ok={bot.last_test_ok}
												/>
												{bot.last_test_error && !bot.last_test_ok && (
													<p className="text-xs text-red-500 mt-1 max-w-[220px] truncate">
														{bot.last_test_error}
													</p>
												)}
											</td>
											<td className="px-4 py-3 align-top text-xs text-[#6B7F8C]">
												{bot.last_tested_at ? (
													(() => {
														try {
															return format(
																new Date(bot.last_tested_at),
																"dd.MM.yyyy HH:mm",
															);
														} catch {
															return bot.last_tested_at;
														}
													})()
												) : (
													"—"
												)}
											</td>
											<td className="px-4 py-3 align-top">
												{isDeletingRow ? (
													<div className="flex items-center gap-2">
														<span className="text-xs text-[#6B7F8C]">
															Видалити?
														</span>
														<button
															onClick={() => handleDelete(bot.id)}
															disabled={isDeleting}
															className="inline-flex items-center gap-1 rounded-lg px-3 py-1.5 text-xs font-medium bg-red-600 text-white hover:bg-red-700 disabled:opacity-60"
														>
															{isDeleting ? "..." : "Так"}
														</button>
														<button
															onClick={() => setDeletingId(null)}
															className="inline-flex items-center gap-1 rounded-lg px-2 py-1.5 text-xs font-medium text-[#6B7F8C] hover:bg-slate-100 dark:hover:bg-slate-800"
														>
															Ні
														</button>
													</div>
												) : isEditing ? (
													<div className="flex items-center gap-2">
														<button
															onClick={() => handleEdit(bot.id)}
															disabled={isUpdating}
															className="inline-flex items-center gap-1 rounded-lg px-3 py-1.5 text-xs font-medium bg-[#3D7A8A] text-white hover:bg-[#2E6070] disabled:opacity-60"
														>
															<Check className="h-3.5 w-3.5" />
															Зберегти
														</button>
														<button
															onClick={() => setEditingId(null)}
															className="inline-flex items-center gap-1 rounded-lg px-2 py-1.5 text-xs font-medium text-[#6B7F8C] hover:bg-red-50 hover:text-red-500"
														>
															<X className="h-3.5 w-3.5" />
														</button>
													</div>
												) : (
													<div className="flex flex-wrap items-center gap-2">
														<button
															onClick={() => handleTest(bot)}
															disabled={rowBusy}
															className={btnGhostCls}
															title="Перевірити (getMe)"
														>
															<LinkIcon className="h-3.5 w-3.5" />
															Перевірити
														</button>
														<button
															onClick={() => handleSetWebhook(bot)}
															disabled={rowBusy}
															className={btnGhostCls}
															title="Встановити webhook на цей бот"
														>
															<Webhook className="h-3.5 w-3.5" />
															Webhook
														</button>
														<button
															onClick={() => handleDeleteWebhook(bot)}
															disabled={rowBusy}
															className="inline-flex items-center gap-1 rounded-lg border border-[#E2E5E8] dark:border-[#2D3D4F] px-2 py-1.5 text-xs font-medium text-[#6B7F8C] hover:bg-slate-100 dark:hover:bg-slate-800 disabled:opacity-60"
															title="Зняти webhook (polling mode)"
														>
															<X className="h-3.5 w-3.5" />
														</button>
														<button
															onClick={() => openEdit(bot)}
															className={btnGhostCls}
														>
															<Pencil className="h-3.5 w-3.5" />
															Редагувати
														</button>
														<button
															onClick={() => setDeletingId(bot.id)}
															className="inline-flex items-center gap-1 rounded-lg border border-red-200 dark:border-red-900 px-2 py-1.5 text-xs font-medium text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20"
														>
															<Trash2 className="h-3.5 w-3.5" />
														</button>
													</div>
												)}
											</td>
										</tr>
									);
								})}
							</tbody>
						</table>
					</div>
				)}
			</div>

			<div className="rounded-xl border border-[#E2E5E8] dark:border-[#2D3D4F] bg-[#F7F6F2] dark:bg-[#1C2B3A] p-4 text-xs text-[#6B7F8C]">
				<p className="font-medium text-[#1C2B3A] dark:text-white mb-2">
					Підказки
				</p>
				<ul className="list-disc pl-4 space-y-1">
					<li>
						Один бот на організацію — позначайте його як{" "}
						<code className="text-[#3D7A8A]">primary</code>, щоб він обробляв
						webhook для цього ЖК.
					</li>
					<li>
						Токен передається лише один раз — потім у відповідях завжди
						маскований.
					</li>
					<li>
						«Webhook» вимагає <code>PLATFORM_PUBLIC_URL</code> на сервері.
						Без нього API поверне 400.
					</li>
					<li>
						Коли немає бота для ЖК — надсилання «тихе» (резиденти нічого не
						бачать, помилки в лог).
					</li>
				</ul>
			</div>
		</div>
	);
}

export default function Page() {
	return (
		<SuperAdminGuard>
			<TelegramBotAdmin />
		</SuperAdminGuard>
	);
}
