"use client";

import { useEffect, useState } from "react";
import { AlertCircle, Car, Check, Megaphone, Wrench } from "lucide-react";
import { toast } from "react-toastify";
import { TabsContent } from "@/components/ui/tabs";
import { TelegramLogo } from "@/components/shared/TelegramLogo";
import { Toggle } from "@/components/ui/Toggle";
import {
  useGetTelegramStatusQuery,
  useGenerateTelegramTokenMutation,
  useDisconnectTelegramMutation,
  useUpdateTelegramSettingsMutation,
} from "@/lib/redux/features/telegram/telegramProfileApiSlice";

// Decorative QR code SVG (not a real QR, purely visual)
function QRCode({ size = 180, seed = 'tg' }) {
  const cells = 21;
  const grid: Array<{ r: number; c: number }> = [];
  let h = 0;
  for (let i = 0; i < seed.length; i++) h = (h * 31 + seed.charCodeAt(i)) & 0xffff;
  for (let r = 0; r < cells; r++) {
    for (let c = 0; c < cells; c++) {
      h = (h * 1103515245 + 12345) & 0x7fffffff;
      const filled = (h % 100) > 48;
      const inCorner =
        (r < 7 && c < 7) ||
        (r < 7 && c >= cells - 7) ||
        (r >= cells - 7 && c < 7);
      if (!inCorner && filled) grid.push({ r, c });
    }
  }
  const unit = size / cells;
  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} style={{ display: 'block' }}>
      <rect width={size} height={size} fill="#fff" />
      {grid.map((g, i) => (
        <rect key={i} x={g.c * unit} y={g.r * unit} width={unit * 0.9} height={unit * 0.9} fill="#0F172A" rx={unit * 0.15} />
      ))}
      {([[0, 0], [0, cells - 7], [cells - 7, 0]] as [number, number][]).map(([r, c], i) => (
        <g key={i} transform={`translate(${c * unit} ${r * unit})`}>
          <rect width={unit * 7} height={unit * 7} rx={unit * 0.8} fill="#0F172A" />
          <rect x={unit * 0.9} y={unit * 0.9} width={unit * 5.2} height={unit * 5.2} rx={unit * 0.5} fill="#fff" />
          <rect x={unit * 2} y={unit * 2} width={unit * 3} height={unit * 3} rx={unit * 0.4} fill="#0F172A" />
        </g>
      ))}
      <g transform={`translate(${size / 2 - 18} ${size / 2 - 18})`}>
        <rect width="36" height="36" rx="8" fill="#fff" />
        <rect x="2" y="2" width="32" height="32" rx="7" fill="#229ED9" />
        <path d="M9 17 L26 10 C27 10 27 11 27 11 L24 25 C24 25 23 25 23 25 L19 22 L17 24 L17 21 L23 15 L15 20 L11 18 Z" fill="#fff" />
      </g>
    </svg>
  );
}

// Notification type definitions (real, backed by backend toggles)
const NOTIF_TYPES = [
  {
    key: "notify_announcements" as const,
    label: "Нові оголошення ОСББ",
    desc: "Коли адміністрація публікує нову новину",
    iconBg: "#CADCFC",
    iconColor: "#1E2761",
    Icon: Megaphone,
  },
  {
    key: "notify_issues" as const,
    label: "Статус моїх заявок",
    desc: "Прийнято, в процесі, виконано — кожен крок",
    iconBg: "#FEF3C7",
    iconColor: "#B45309",
    Icon: Wrench,
  },
  {
    key: "notify_passes" as const,
    label: "Заявки на в'їзд",
    desc: "Коли охорона пропускає вашого гостя",
    iconBg: "#DCFCE7",
    iconColor: "#2D8A4E",
    Icon: Car,
  },
  {
    key: "notify_emergency" as const,
    label: "Аварійні повідомлення",
    desc: "Відключення води, світла, газу",
    iconBg: "#FEE2E2",
    iconColor: "#C0392B",
    Icon: AlertCircle,
  },
  {
    key: "notify_visits" as const,
    label: "Візити гостей",
    desc: "Коли охорона пропускає гостя",
    iconBg: "#DCFCE7",
    iconColor: "#2D8A4E",
    Icon: Car,
  },
] as const;

// Preview notification list shown on the default (not-connected) panel
const PREVIEW_NOTIF = [
  {
    label: "Нові оголошення ОСББ",
    desc: "Коли адмін публікує новини",
    iconBg: "#CADCFC",
    iconColor: "#1E2761",
    Icon: Megaphone,
    on: true,
  },
  {
    label: "Статус моїх заявок",
    desc: "Кожне оновлення заявки",
    iconBg: "#FEF3C7",
    iconColor: "#B45309",
    Icon: Wrench,
    on: true,
  },
  {
    label: "Аварійні повідомлення",
    desc: "Відключення води, світла, газу",
    iconBg: "#FEE2E2",
    iconColor: "#C0392B",
    Icon: AlertCircle,
    on: true,
  },
  {
    label: "Візити гостей",
    desc: "Коли охорона пропускає гостя",
    iconBg: "#DCFCE7",
    iconColor: "#2D8A4E",
    Icon: Car,
    on: false,
  },
];

export default function TelegramSettings() {
  const [deepLink, setDeepLink] = useState<string | null>(null);
  const [botUsername, setBotUsername] = useState("");
  const [isPolling, setIsPolling] = useState(false);
  const [copied, setCopied] = useState(false);

  const { data: status, isLoading } = useGetTelegramStatusQuery(undefined, {
    pollingInterval: isPolling ? 3000 : 0,
  });

  const [generateToken, { isLoading: isGenerating }] = useGenerateTelegramTokenMutation();
  const [disconnect, { isLoading: isDisconnecting }] = useDisconnectTelegramMutation();
  const [updateSettings] = useUpdateTelegramSettingsMutation();

  // Stop polling once connected
  useEffect(() => {
    if (status?.connected && isPolling) {
      setIsPolling(false);
      setDeepLink(null);
      toast.success("Telegram успішно підключено!");
    }
  }, [status?.connected, isPolling]);

  // Feature disabled for this org — hide entirely
  if (!isLoading && !status?.feature_enabled) return null;

  const handleConnect = async () => {
    try {
      const result = await generateToken().unwrap();
      setDeepLink(result.deep_link);
      setBotUsername(result.bot_username);
      setIsPolling(true);
    } catch {
      toast.error("Не вдалось згенерувати посилання. Спробуйте ще раз.");
    }
  };

  const handleDisconnect = async () => {
    try {
      await disconnect().unwrap();
      toast.success("Telegram відключено.");
    } catch {
      toast.error("Помилка при відключенні.");
    }
  };

  const handleToggle = async (
    field:
      | "notify_issues"
      | "notify_passes"
      | "notify_announcements"
      | "notify_emergency"
      | "notify_visits",
    value: boolean,
  ) => {
    try {
      await updateSettings({ [field]: value }).unwrap();
    } catch {
      toast.error("Не вдалося оновити налаштування.");
    }
  };

  const handleCopy = (text: string) => {
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    });
  };

  // Extract token from deep_link URL
  const token = deepLink
    ? (() => {
        try {
          return new URL(deepLink).searchParams.get("start") ?? "";
        } catch {
          return deepLink.split("start=")[1] ?? "";
        }
      })()
    : "";

  const renderContent = () => {
    if (isLoading) {
      return (
        <div className="flex justify-center py-12">
          <div className="w-8 h-8 border-2 border-[#1E2761] border-t-transparent rounded-full animate-spin" />
        </div>
      );
    }

    // Bot not configured warning
    if (!status?.bot_configured) {
      return (
        <div className="rounded-2xl border border-slate-100 dark:border-[#2D3D4F] shadow-sm p-4 md:p-7">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-10 h-10 rounded-xl bg-[#CADCFC] flex items-center justify-center">
              <TelegramLogo size={22} />
            </div>
            <h3 className="font-semibold text-slate-700 dark:text-slate-300">
              Telegram сповіщення
            </h3>
          </div>
          <div className="flex items-start gap-2 text-sm text-amber-700 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/20 rounded-xl p-3">
            <AlertCircle className="size-4 mt-0.5 shrink-0" />
            <p>
              Telegram бот ще не налаштований для вашої організації. Зверніться до адміністратора.
            </p>
          </div>
        </div>
      );
    }

    // Waiting panel (deepLink set, polling for connection confirmation)
    if (!status?.connected && deepLink) {
      return (
        <div className="rounded-2xl border border-slate-100 dark:border-[#2D3D4F] shadow-sm p-4 md:p-7 text-center">
          {/* Spinning ring + TG logo */}
          <div className="relative mx-auto mb-5 w-20 h-20 md:w-24 md:h-24">
            <div className="absolute inset-0 rounded-full bg-[#CADCFC] flex items-center justify-center">
              <TelegramLogo size={44} />
            </div>
            <svg
              width="100%"
              height="100%"
              viewBox="0 0 100 100"
              style={{ position: 'absolute', inset: -10, animation: 'tgspin 1.6s linear infinite' }}
            >
              <circle
                cx="50"
                cy="50"
                r="46"
                fill="none"
                stroke="#1E2761"
                strokeWidth="3"
                strokeDasharray="18 14"
                strokeLinecap="round"
              />
            </svg>
          </div>
          <style>{`@keyframes tgspin { to { transform: rotate(360deg); } }`}</style>

          <h3 className="text-xl font-bold text-[#0F172A] dark:text-white mb-2">
            Очікуємо підтвердження…
          </h3>
          <p className="text-sm text-slate-500 dark:text-slate-400 max-w-sm mx-auto mb-6">
            Ви щойно відкрили Telegram. Надішліть боту{" "}
            <span className="font-semibold text-[#0F172A] dark:text-white">
              @{botUsername || "ApartmentOSBot"}
            </span>{" "}
            код{" "}
            <code className="bg-[#F1F5F9] dark:bg-[#1C2B3A] px-1.5 py-0.5 rounded font-mono text-[#0F172A] dark:text-white">
              {token}
            </code>
          </p>

          <div className="flex flex-col md:flex-row justify-center gap-3">
            <button
              onClick={() => {
                setDeepLink(null);
                setIsPolling(false);
              }}
              className="w-full md:w-auto px-4 py-2.5 rounded-xl text-sm font-medium border border-slate-200 dark:border-[#2D3D4F] text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-[#1C2B3A] transition-colors"
            >
              Скасувати
            </button>
            <a
              href={deepLink}
              target="_blank"
              rel="noopener noreferrer"
              className="w-full md:w-auto inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl text-sm font-medium bg-[#1E2761] hover:bg-[#16204f] text-white transition-colors"
            >
              <TelegramLogo size={16} mono />
              Відкрити Telegram знову
            </a>
          </div>
        </div>
      );
    }

    // Connected panel
    if (status?.connected) {
      const enabledCount = NOTIF_TYPES.filter((t) => status[t.key]).length;
      return (
        <div className="flex flex-col gap-4">
          {/* Header card */}
          <div className="rounded-2xl border border-slate-100 dark:border-[#2D3D4F] shadow-sm p-4 md:p-7">
            <div className="flex flex-col md:flex-row md:items-center gap-4">
              <div className="flex items-center gap-4 flex-1 min-w-0">
                <div className="relative flex-shrink-0">
                  <div className="w-12 h-12 rounded-2xl bg-[#229ED9] flex items-center justify-center text-white text-xl font-bold">
                    T
                  </div>
                  <div className="absolute -bottom-1 -right-1 w-5 h-5 rounded-full bg-[#2D8A4E] border-2 border-white dark:border-[#162032] flex items-center justify-center">
                    <Check className="w-2.5 h-2.5 text-white" strokeWidth={3} />
                  </div>
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-semibold text-[#0F172A] dark:text-white text-base">
                      Telegram підключено
                    </span>
                    <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-[#DCFCE7] text-[#2D8A4E]">
                      Підключено
                    </span>
                  </div>
                  {status.telegram_username && (
                    <div className="text-xs text-slate-500 dark:text-slate-400 mt-1 font-mono">
                      @{status.telegram_username}
                    </div>
                  )}
                  {status.created_at && (
                    <div className="text-xs text-slate-400 dark:text-slate-500 mt-1 font-mono">
                      Підключено{" "}
                      {new Date(status.created_at).toLocaleDateString("uk-UA", {
                        day: "numeric",
                        month: "long",
                        year: "numeric",
                      })}
                    </div>
                  )}
                </div>
              </div>
              <button
                onClick={handleDisconnect}
                disabled={isDisconnecting}
                className="w-full md:w-auto md:flex-shrink-0 flex items-center justify-center gap-1.5 px-3 py-2 md:py-1.5 rounded-lg text-sm font-medium bg-[#FEE2E2] dark:bg-red-900/20 text-[#C0392B] border border-[#C0392B]/30 hover:bg-[#FEE2E2]/80 transition-colors disabled:opacity-50"
              >
                {isDisconnecting ? "…" : "Відʼєднати"}
              </button>
            </div>
          </div>

          {/* Notification toggles */}
          <div className="rounded-2xl border border-slate-100 dark:border-[#2D3D4F] shadow-sm p-4 md:p-7">
            <div className="flex items-center justify-between mb-1">
              <div>
                <h4 className="font-semibold text-[#0F172A] dark:text-white text-sm">
                  Типи сповіщень
                </h4>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                  Вмикайте лише те, що вам цікаво
                </p>
              </div>
              <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-[#CADCFC] text-[#1E2761]">
                {enabledCount} із {NOTIF_TYPES.length}
              </span>
            </div>

            <div className="mt-2">
              {NOTIF_TYPES.map(({ key, label, desc, iconBg, iconColor, Icon }) => (
                <div
                  key={key}
                  className="flex items-center gap-4 py-4 border-b border-slate-50 dark:border-[#1C2B3A] last:border-0"
                >
                  <div
                    className="w-9 h-9 md:w-11 md:h-11 rounded-xl flex-shrink-0 flex items-center justify-center"
                    style={{ background: iconBg, color: iconColor }}
                  >
                    <Icon className="w-5 h-5" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-semibold text-[#0F172A] dark:text-white">
                      {label}
                    </div>
                    <div className="text-xs text-slate-500 dark:text-slate-400 mt-0.5 leading-snug">
                      {desc}
                    </div>
                  </div>
                  <Toggle
                    checked={status[key] ?? false}
                    onChange={(val) => handleToggle(key, val)}
                  />
                </div>
              ))}
            </div>
          </div>

          {/* Quiet hours (UI-only, future feature) */}
          <div
            className="rounded-2xl p-4"
            style={{ background: '#F8FAFC', border: '1px dashed #CBD5E1' }}
          >
            <div className="flex items-start gap-3">
              <span className="text-slate-400 mt-0.5">
                <svg
                  width="18"
                  height="18"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <path d="M18 8A6 6 0 006 8c0 7-3 9-3 9h18s-3-2-3-9" />
                  <path d="M13.73 21a2 2 0 01-3.46 0" />
                </svg>
              </span>
              <div className="flex-1">
                <div className="text-sm font-semibold text-[#0F172A] dark:text-white">
                  Тихі години
                </div>
                <div className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                  Не турбувати з 22:00 до 08:00 (крім аварійних)
                </div>
              </div>
              <Toggle checked={false} onChange={() => {}} />
            </div>
          </div>
        </div>
      );
    }

    // Default panel (not connected, no deepLink)
    return (
      <div className="flex flex-col gap-4">
        {/* Main connection card */}
        <div className="rounded-2xl border border-slate-100 dark:border-[#2D3D4F] shadow-sm p-4 md:p-7">
          {/* Header */}
          <div className="flex items-center gap-3 mb-5 sm:mb-6">
            <TelegramLogo size={44} />
            <div className="flex-1">
              <h3 className="text-lg sm:text-xl font-bold text-[#0F172A] dark:text-white">
                Сповіщення в Telegram
              </h3>
              <p className="text-xs sm:text-sm text-slate-500 dark:text-slate-400 mt-0.5">
                Підключіть бота, щоб отримувати миттєві сповіщення
              </p>
            </div>
            <span className="hidden sm:inline text-xs font-semibold px-2.5 py-1 rounded-full bg-[#F1F5F9] text-[#64748B]">
              Не підключено
            </span>
          </div>

          {/* QR + steps — two-column on desktop (≥md), stacked on mobile */}
          <div className="flex flex-col md:grid md:grid-cols-[200px_1fr] gap-5 md:gap-7 items-start">
            {/* Decorative QR code — hidden on mobile, shown on md+ */}
            <div className="hidden md:flex flex-col items-center gap-3">
              <div className="p-3 border border-slate-200 dark:border-[#2D3D4F] rounded-xl bg-white">
                <QRCode size={160} seed="apartmentos-tg-1" />
              </div>
              <span className="text-xs text-slate-400 font-mono">Дійсний 10 хвилин</span>
            </div>

            {/* Steps */}
            <div className="flex flex-col gap-4 sm:gap-5">
              {/* Step 1 */}
              <div className="flex gap-3">
                <div className="w-6 h-6 rounded-full bg-[#1E2761] text-white flex items-center justify-center text-xs font-bold flex-shrink-0 mt-0.5">
                  1
                </div>
                <div>
                  <div className="text-sm font-semibold text-[#0F172A] dark:text-white">
                    Відскануйте QR-код
                  </div>
                  <div className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                    Або натисніть кнопку нижче, якщо ви на телефоні
                  </div>
                </div>
              </div>

              {/* Step 2 */}
              <div className="flex gap-3">
                <div className="w-6 h-6 rounded-full bg-[#1E2761] text-white flex items-center justify-center text-xs font-bold flex-shrink-0 mt-0.5">
                  2
                </div>
                <div className="flex-1">
                  <div className="text-sm font-semibold text-[#0F172A] dark:text-white">
                    Натисніть Start у боті
                  </div>
                  <div className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                    Бот надішле вам код підтвердження автоматично
                  </div>
                </div>
              </div>

              {/* CTA button — full-width on mobile, auto-width on desktop */}
              <button
                onClick={handleConnect}
                disabled={isGenerating}
                className="flex items-center justify-center gap-2 w-full md:w-auto rounded-xl bg-[#1E2761] hover:bg-[#16204f] disabled:opacity-60 text-white px-4 py-3 text-sm font-semibold transition-colors"
              >
                {isGenerating ? (
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                ) : (
                  <TelegramLogo size={18} mono />
                )}
                Відкрити Telegram
              </button>
            </div>
          </div>
        </div>

        {/* Preview notification list */}
        <div className="rounded-2xl border border-slate-100 dark:border-[#2D3D4F] shadow-sm p-4 md:p-7">
          <h4 className="text-sm font-semibold text-[#0F172A] dark:text-white mb-0.5">
            Що ви будете отримувати
          </h4>
          <p className="text-xs text-slate-500 dark:text-slate-400 mb-3">
            Налаштуйте типи сповіщень після підключення
          </p>
          <div>
            {PREVIEW_NOTIF.map(({ label, desc, iconBg, iconColor, Icon, on }, idx) => (
              <div
                key={idx}
                className="flex items-center gap-4 py-3.5 border-b border-slate-50 dark:border-[#1C2B3A] last:border-0"
              >
                <div
                  className="w-9 h-9 md:w-11 md:h-11 rounded-xl flex-shrink-0 flex items-center justify-center"
                  style={{ background: iconBg, color: iconColor }}
                >
                  <Icon className="w-5 h-5" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-semibold text-[#0F172A] dark:text-white">{label}</div>
                  <div className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">{desc}</div>
                </div>
                <Toggle checked={on} onChange={() => {}} disabled />
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  };

  return (
    <TabsContent value="notifications">
      {renderContent()}
    </TabsContent>
  );
}
