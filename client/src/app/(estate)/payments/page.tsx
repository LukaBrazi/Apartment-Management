import type { Metadata } from "next";
import ComingSoon from "@/components/shared/ComingSoon";

export const metadata: Metadata = { title: "ApartmentOS | Платежі" };

export default function PaymentsPage() {
  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold text-[#111827]">Платежі</h1>
        <p className="text-sm text-[#6B7280] mt-1">Квитанції та оплата комунальних послуг</p>
      </div>
      <ComingSoon
        serviceName="Платежі"
        microserviceKey="PAYMENTS_SERVICE"
        description="Інтеграція з платіжним сервісом незабаром буде доступна."
      />
    </div>
  );
}
