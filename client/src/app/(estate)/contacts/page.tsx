import type { Metadata } from "next";
import ComingSoon from "@/components/shared/ComingSoon";

export const metadata: Metadata = { title: "Skandi Apartments | Контакти" };

export default function ContactsPage() {
  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold text-[#111827]">Контакти</h1>
        <p className="text-sm text-[#6B7280] mt-1">Контакти служб та управителя будинку</p>
      </div>
      <ComingSoon
        serviceName="Контакти"
        microserviceKey="CONTACTS_SERVICE"
        description="Довідник контактів управителя та аварійних служб незабаром буде доступний."
      />
    </div>
  );
}
