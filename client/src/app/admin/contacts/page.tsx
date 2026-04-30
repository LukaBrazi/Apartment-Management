"use client";

import { useState } from "react";
import { ColumnDef } from "@tanstack/react-table";
import { toast } from "react-toastify";
import {
	BookUser,
	Pencil,
	Plus,
	Trash2,
	X,
	Check,
	Phone,
	Mail,
	AlertTriangle,
} from "lucide-react";

import { DataTable } from "@/components/admin/DataTable";
import { Button } from "@/components/ui/button";
import {
	Dialog,
	DialogContent,
	DialogFooter,
	DialogHeader,
	DialogTitle,
} from "@/components/ui/dialog";
import {
	Select,
	SelectContent,
	SelectItem,
	SelectTrigger,
	SelectValue,
} from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import {
	useGetAdminContactsQuery,
	useAdminCreateContactMutation,
	useAdminUpdateContactMutation,
	useAdminDeleteContactMutation,
	AdminContactPerson,
	AdminContactCreateData,
} from "@/lib/redux/features/siteSettings/siteSettingsApiSlice";
import { extractErrorMessage } from "@/utils";

const ROLE_OPTIONS: Array<{ value: AdminContactPerson["role"]; label: string }> = [
	{ value: "manager", label: "Управитель" },
	{ value: "technician", label: "Технічний спеціаліст" },
	{ value: "guard", label: "Охорона" },
	{ value: "accountant", label: "Бухгалтерія" },
	{ value: "emergency", label: "Аварійна служба" },
	{ value: "other", label: "Інше" },
];

const ROLE_LABELS: Record<string, string> = Object.fromEntries(
	ROLE_OPTIONS.map((o) => [o.value, o.label]),
);

const inputCls =
	"rounded-xl border border-[#E2E5E8] bg-[#F7F6F2] px-3 py-2 text-sm dark:border-[#2D3D4F] dark:bg-[#1C2B3A] dark:text-white focus:outline-none focus:border-[#3D7A8A] focus:ring-1 focus:ring-[#3D7A8A] w-full";
const labelCls = "text-xs font-medium text-[#6B7F8C]";

const emptyForm: AdminContactCreateData = {
	name: "",
	role: "manager",
	position: "",
	phone: "",
	email: "",
	telegram: "",
	working_hours: "",
	is_emergency: false,
	is_active: true,
};

export default function AdminContactsPage() {
	const { data, isLoading } = useGetAdminContactsQuery();
	const [createContact, { isLoading: isCreating }] = useAdminCreateContactMutation();
	const [updateContact, { isLoading: isUpdating }] = useAdminUpdateContactMutation();
	const [deleteContact, { isLoading: isDeleting }] = useAdminDeleteContactMutation();

	const [createOpen, setCreateOpen] = useState(false);
	const [createForm, setCreateForm] = useState<AdminContactCreateData>(emptyForm);

	const [editing, setEditing] = useState<AdminContactPerson | null>(null);
	const [editForm, setEditForm] = useState<AdminContactCreateData>(emptyForm);

	const [deletingId, setDeletingId] = useState<number | null>(null);

	const contacts = data ?? [];

	// ── Handlers ─────────────────────────────────────────────────────────

	const handleCreate = async () => {
		if (!createForm.name.trim()) {
			toast.error("Імʼя обовʼязкове");
			return;
		}
		try {
			await createContact(createForm).unwrap();
			toast.success("Контакт створено");
			setCreateOpen(false);
			setCreateForm(emptyForm);
		} catch (err) {
			toast.error(extractErrorMessage(err) || "Не вдалося створити контакт");
		}
	};

	const openEdit = (contact: AdminContactPerson) => {
		setEditing(contact);
		setEditForm({
			name: contact.name,
			role: contact.role,
			position: contact.position ?? "",
			phone: contact.phone ?? "",
			email: contact.email ?? "",
			telegram: contact.telegram ?? "",
			working_hours: contact.working_hours ?? "",
			is_emergency: contact.is_emergency,
			is_active: contact.is_active,
			order: contact.order,
		});
	};

	const handleUpdate = async () => {
		if (!editing) return;
		try {
			await updateContact({ id: editing.id, ...editForm }).unwrap();
			toast.success("Контакт оновлено");
			setEditing(null);
		} catch (err) {
			toast.error(extractErrorMessage(err) || "Не вдалося оновити контакт");
		}
	};

	const handleDelete = async (id: number) => {
		try {
			await deleteContact(id).unwrap();
			toast.success("Контакт видалено");
			setDeletingId(null);
		} catch (err) {
			toast.error(extractErrorMessage(err) || "Не вдалося видалити контакт");
		}
	};

	// ── Table columns ────────────────────────────────────────────────────

	const columns: ColumnDef<AdminContactPerson, unknown>[] = [
		{
			accessorKey: "name",
			header: "Імʼя",
			cell: ({ row }) => (
				<div className="font-medium text-[#1C2B3A] dark:text-white">
					{row.original.name}
				</div>
			),
		},
		{
			accessorKey: "position",
			header: "Посада",
			cell: ({ row }) => (
				<span className="text-sm text-[#6B7F8C]">
					{row.original.position || "—"}
				</span>
			),
		},
		{
			accessorKey: "role",
			header: "Роль",
			cell: ({ row }) => (
				<span className="text-sm text-[#1C2B3A] dark:text-white">
					{ROLE_LABELS[row.original.role] ?? row.original.role}
				</span>
			),
		},
		{
			accessorKey: "phone",
			header: "Телефон",
			cell: ({ row }) =>
				row.original.phone ? (
					<a
						href={`tel:${row.original.phone}`}
						className="text-sm text-[#3D7A8A] hover:underline"
					>
						<Phone className="inline mr-1 h-3.5 w-3.5" />
						{row.original.phone}
					</a>
				) : (
					<span className="text-sm text-[#6B7F8C]">—</span>
				),
		},
		{
			accessorKey: "email",
			header: "Email",
			cell: ({ row }) =>
				row.original.email ? (
					<a
						href={`mailto:${row.original.email}`}
						className="text-sm text-[#3D7A8A] hover:underline"
					>
						<Mail className="inline mr-1 h-3.5 w-3.5" />
						{row.original.email}
					</a>
				) : (
					<span className="text-sm text-[#6B7F8C]">—</span>
				),
		},
		{
			accessorKey: "is_emergency",
			header: "Аварійна",
			cell: ({ row }) =>
				row.original.is_emergency ? (
					<span className="inline-flex items-center gap-1 rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-700 dark:bg-red-900/30 dark:text-red-300">
						<AlertTriangle className="h-3 w-3" /> так
					</span>
				) : (
					<span className="text-xs text-[#6B7F8C]">—</span>
				),
		},
		{
			accessorKey: "is_active",
			header: "Активний",
			cell: ({ row }) =>
				row.original.is_active ? (
					<span className="inline-flex items-center gap-1 rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-700 dark:bg-green-900/30 dark:text-green-300">
						<Check className="h-3 w-3" /> так
					</span>
				) : (
					<span className="inline-flex items-center gap-1 rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-600 dark:bg-gray-800 dark:text-gray-300">
						<X className="h-3 w-3" /> ні
					</span>
				),
		},
		{
			id: "actions",
			header: "",
			cell: ({ row }) => (
				<div className="flex items-center gap-1">
					<Button
						variant="ghost"
						size="sm"
						onClick={() => openEdit(row.original)}
						className="h-7 px-2 text-[#3D7A8A] hover:bg-[#EBF3F5] dark:hover:bg-[#1A2E3A]"
						title="Редагувати"
					>
						<Pencil className="h-3.5 w-3.5" />
					</Button>
					<Button
						variant="ghost"
						size="sm"
						onClick={() => setDeletingId(row.original.id)}
						className="h-7 px-2 text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20"
						title="Видалити"
					>
						<Trash2 className="h-3.5 w-3.5" />
					</Button>
				</div>
			),
		},
	];

	return (
		<div className="space-y-6">
			<div className="flex items-start justify-between gap-4">
				<div>
					<h2 className="flex items-center gap-2 text-2xl font-bold text-[#1C2B3A] dark:text-white">
						<BookUser className="h-6 w-6" /> Контакти
					</h2>
					<p className="mt-1 text-sm text-[#6B7F8C]">
						Управителі, аварійні служби, технічні спеціалісти. Контакти
						відображаються мешканцям на сторінці «/contacts».
					</p>
				</div>
				<Button
					onClick={() => setCreateOpen(true)}
					className="bg-[#3D7A8A] text-white hover:bg-[#336678]"
				>
					<Plus className="mr-1 h-4 w-4" />
					Додати контакт
				</Button>
			</div>

			<div className="rounded-xl border border-[#E2E5E8] bg-white p-6 shadow-sm dark:border-[#2D3D4F] dark:bg-[#162032]">
				<DataTable
					columns={columns}
					data={contacts}
					isLoading={isLoading}
					searchPlaceholder="Пошук контактів..."
				/>
			</div>

			{/* Create dialog */}
			<Dialog open={createOpen} onOpenChange={setCreateOpen}>
				<DialogContent className="max-w-lg bg-white dark:bg-[#1C2B3A]">
					<DialogHeader>
						<DialogTitle>Додати контакт</DialogTitle>
					</DialogHeader>
					<ContactForm form={createForm} setForm={setCreateForm} />
					<DialogFooter className="pt-2">
						<Button
							variant="outline"
							onClick={() => setCreateOpen(false)}
							className="border-[#E2E5E8] dark:border-[#2D3D4F]"
						>
							Скасувати
						</Button>
						<Button
							onClick={handleCreate}
							disabled={isCreating}
							className="bg-[#3D7A8A] text-white hover:bg-[#336678]"
						>
							{isCreating ? "Збереження..." : "Створити"}
						</Button>
					</DialogFooter>
				</DialogContent>
			</Dialog>

			{/* Edit dialog */}
			<Dialog open={editing !== null} onOpenChange={(o) => !o && setEditing(null)}>
				<DialogContent className="max-w-lg bg-white dark:bg-[#1C2B3A]">
					<DialogHeader>
						<DialogTitle>Редагувати контакт</DialogTitle>
					</DialogHeader>
					<ContactForm form={editForm} setForm={setEditForm} />
					<DialogFooter className="pt-2">
						<Button
							variant="outline"
							onClick={() => setEditing(null)}
							className="border-[#E2E5E8] dark:border-[#2D3D4F]"
						>
							Скасувати
						</Button>
						<Button
							onClick={handleUpdate}
							disabled={isUpdating}
							className="bg-[#3D7A8A] text-white hover:bg-[#336678]"
						>
							{isUpdating ? "Збереження..." : "Зберегти"}
						</Button>
					</DialogFooter>
				</DialogContent>
			</Dialog>

			{/* Delete confirm */}
			<Dialog open={deletingId !== null} onOpenChange={(o) => !o && setDeletingId(null)}>
				<DialogContent className="max-w-sm bg-white dark:bg-[#1C2B3A]">
					<DialogHeader>
						<DialogTitle>Видалити контакт?</DialogTitle>
					</DialogHeader>
					<p className="text-sm text-[#6B7F8C]">
						Цю дію неможливо скасувати. Контакт зникне зі сторінки
						«/contacts».
					</p>
					<DialogFooter>
						<Button
							variant="outline"
							onClick={() => setDeletingId(null)}
							className="border-[#E2E5E8] dark:border-[#2D3D4F]"
						>
							Скасувати
						</Button>
						<Button
							onClick={() => deletingId !== null && handleDelete(deletingId)}
							disabled={isDeleting}
							className="bg-red-600 text-white hover:bg-red-700"
						>
							{isDeleting ? "Видалення..." : "Видалити"}
						</Button>
					</DialogFooter>
				</DialogContent>
			</Dialog>
		</div>
	);
}

interface ContactFormProps {
	form: AdminContactCreateData;
	setForm: (next: AdminContactCreateData) => void;
}

function ContactForm({ form, setForm }: ContactFormProps) {
	const update = <K extends keyof AdminContactCreateData>(
		key: K,
		value: AdminContactCreateData[K],
	) => setForm({ ...form, [key]: value });

	return (
		<div className="grid grid-cols-1 gap-4 md:grid-cols-2">
			<div className="md:col-span-2">
				<label className={labelCls}>Імʼя *</label>
				<Input
					value={form.name}
					onChange={(e) => update("name", e.target.value)}
					className={inputCls}
					placeholder="Іван Петренко"
				/>
			</div>
			<div>
				<label className={labelCls}>Роль</label>
				<Select
					value={form.role}
					onValueChange={(v) => update("role", v as AdminContactPerson["role"])}
				>
					<SelectTrigger className={inputCls}>
						<SelectValue />
					</SelectTrigger>
					<SelectContent>
						{ROLE_OPTIONS.map((opt) => (
							<SelectItem key={opt.value} value={opt.value}>
								{opt.label}
							</SelectItem>
						))}
					</SelectContent>
				</Select>
			</div>
			<div>
				<label className={labelCls}>Посада</label>
				<Input
					value={form.position ?? ""}
					onChange={(e) => update("position", e.target.value)}
					className={inputCls}
					placeholder="Головний інженер"
				/>
			</div>
			<div>
				<label className={labelCls}>Телефон</label>
				<Input
					value={form.phone ?? ""}
					onChange={(e) => update("phone", e.target.value)}
					className={inputCls}
					placeholder="+380501234567"
				/>
			</div>
			<div>
				<label className={labelCls}>Email</label>
				<Input
					type="email"
					value={form.email ?? ""}
					onChange={(e) => update("email", e.target.value)}
					className={inputCls}
					placeholder="ivan@example.com"
				/>
			</div>
			<div>
				<label className={labelCls}>Telegram</label>
				<Input
					value={form.telegram ?? ""}
					onChange={(e) => update("telegram", e.target.value)}
					className={inputCls}
					placeholder="ivan_pm (без @)"
				/>
			</div>
			<div>
				<label className={labelCls}>Години роботи</label>
				<Input
					value={form.working_hours ?? ""}
					onChange={(e) => update("working_hours", e.target.value)}
					className={inputCls}
					placeholder="Пн-Пт 09:00-18:00"
				/>
			</div>
			<div className="flex items-center gap-2 pt-5">
				<input
					id="is_emergency"
					type="checkbox"
					checked={!!form.is_emergency}
					onChange={(e) => update("is_emergency", e.target.checked)}
					className="h-4 w-4 rounded border-[#E2E5E8] text-[#3D7A8A] focus:ring-[#3D7A8A]"
				/>
				<label htmlFor="is_emergency" className="text-sm text-[#1C2B3A] dark:text-white">
					Аварійна служба (показувати у спецсекції)
				</label>
			</div>
			<div className="flex items-center gap-2">
				<input
					id="is_active"
					type="checkbox"
					checked={form.is_active !== false}
					onChange={(e) => update("is_active", e.target.checked)}
					className="h-4 w-4 rounded border-[#E2E5E8] text-[#3D7A8A] focus:ring-[#3D7A8A]"
				/>
				<label htmlFor="is_active" className="text-sm text-[#1C2B3A] dark:text-white">
					Активний (показувати на сайті)
				</label>
			</div>
		</div>
	);
}
