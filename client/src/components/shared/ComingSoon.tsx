interface ComingSoonProps {
  serviceName: string;
  microserviceKey: string;
  description?: string;
}

export default function ComingSoon({ serviceName, microserviceKey, description }: ComingSoonProps) {
  const serviceUrl = process.env[`NEXT_PUBLIC_${microserviceKey}_URL`];

  if (serviceUrl) {
    return (
      <div className="rounded-2xl border border-[#E5E7EB] bg-white shadow-sm overflow-hidden">
        <iframe src={serviceUrl} className="w-full h-[600px]" title={serviceName} />
      </div>
    );
  }

  return (
    <div className="rounded-2xl border border-[#E5E7EB] bg-white p-8 text-center shadow-sm">
      <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-[#EEF3FD]">
        <svg className="h-8 w-8 text-[#2F6FED]" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
          <path d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
        </svg>
      </div>
      <h2 className="text-lg font-semibold text-[#111827]">{serviceName}</h2>
      <p className="mt-2 text-sm text-[#6B7280]">
        {description ?? "Цей розділ незабаром буде доступний."}
      </p>
      <p className="mt-3 text-xs text-[#9CA3AF] font-mono">
        {`NEXT_PUBLIC_${microserviceKey}_URL`}
      </p>
    </div>
  );
}
