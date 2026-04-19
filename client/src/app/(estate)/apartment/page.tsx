/**
 * PR-4: the self-serve "Add apartment" page is gone.  Unit membership
 * is admin-managed now, so this route no longer makes sense.  The file
 * is kept as a 404 stub until the deletion lands alongside PR-6 cleanup.
 */
import { notFound } from "next/navigation";

export default function DeprecatedAddApartmentPage() {
	notFound();
}
