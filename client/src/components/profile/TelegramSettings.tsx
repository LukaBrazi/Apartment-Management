"use client";

import { useEffect, useState } from "react";
import { Send, CheckCircle, AlertCircle } from "lucide-react";
import { toast } from "react-toastify";
import Spinner from "@/components/shared/Spinner";
import { TabsContent } from "@/components/ui/tabs";
import {
  useGetTelegramStatusQuery,
  useGenerateTelegramTokenMutation,
  useDisconnectTelegramMutation,
  useUpdateTelegramSettingsMutation,
} from "@/lib/redux/features/telegram/telegramProfileApiSlice";

export default function TelegramSettings() {
  const [isConnecting, setIsConnecting] = useState(false);
  const [deepLink, setDeepLink] = useState<string | null>(null);
  const [isPolling, setIsPolling] = useState(false);

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
      setIsConnecting(false);
      setDeepLink(null);
      toast.success("Telegram успішно підключено!");
    }
  }, [status?.connected, isPolling]);

  // State D: feature disabled for this org — component completely hidden
  if (!isLoading && !status?.feature_enabled) {
    return null;
  }

  const handleConnect = async () => {
    try {
      setIsConnecting(true);
      const result = await generateToken().unwrap();
      setDeepLink(result.deep_link);
      setIsPolling(true);
    } catch {
      toast.error("Не вдалось згенерувати посилання. Спробуйте ще раз.");
      setIsConnecting(false);
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
    field: "notify_issues" | "notify_passes" | "notify_announcements",
    value: boolean,
  ) => {
    try {
      await updateSettings({ [field]: value }).unwrap();
    } catch {
      toast.error("Не вдалося оновити налаштування.");
    }
  };

  const renderContent = () => {
    if (isLoading) {
      return (
        <div className="flex justify-center py-8">
          <Spinner size="sm" />
        </div>
      );
    }

    // State C: feature enabled but bot not configured
    if (!status?.bot_configured) {
      return (
        <div className="rounded-2xl border border-slate-100 dark:border-[#2D3D4F] shadow-sm p-6">
          <div className="flex items-center gap-3 mb-3">
            <Send className="size-5 text-slate-400" />
            <h3 className="font-semibold text-slate-700 dark:text-slate-300">
              Telegram сповіщення
            </h3>
          </div>
          <div className="flex items-start gap-2 text-sm text-amber-700 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/20 rounded-lg p-3">
            <AlertCircle className="size-4 mt-0.5 shrink-0" />
            <p>
              Telegram бот ще не налаштований для вашої організації. Зверніться до адміністратора.
            </p>
          </div>
        </div>
      );
    }

    // State A: not connected
    if (!status?.connected) {
      return (
        <div className="rounded-2xl border border-slate-100 dark:border-[#2D3D4F] shadow-sm p-6">
          <div className="flex items-center gap-3 mb-4">
            <div className="flex items-center justify-center size-10 rounded-xl bg-[#CADCFC] dark:bg-[#1E2761]/40">
              <Send className="size-5 text-[#4A90D9]" />
            </div>
            <div>
              <h3 className="font-semibold text-slate-800 dark:text-babyPowder">
                Telegram сповіщення
              </h3>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Отримуйте сповіщення про заявки та оголошення
              </p>
            </div>
          </div>

          {!deepLink ? (
            <button
              onClick={handleConnect}
              disabled={isGenerating || isConnecting}
              className="flex items-center gap-2 rounded-lg bg-[#4A90D9] hover:bg-[#3A7BC8] disabled:opacity-60 text-white px-4 py-2.5 text-sm font-medium transition-colors"
            >
              {isGenerating ? <Spinner size="sm" /> : <Send className="size-4" />}
              Підключити Telegram
            </button>
          ) : (
            <div className="space-y-3">
              <p className="text-sm text-slate-600 dark:text-slate-400">
                Натисніть кнопку нижче, щоб відкрити бота і підтвердити підключення:
              </p>
              <a
                href={deepLink}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 rounded-lg bg-[#4A90D9] hover:bg-[#3A7BC8] text-white px-4 py-2.5 text-sm font-medium transition-colors"
              >
                <Send className="size-4" />
                Відкрити Telegram бота
              </a>
              <div className="flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400">
                <Spinner size="sm" />
                <span>Очікуємо підтвердження...</span>
              </div>
            </div>
          )}
        </div>
      );
    }

    // State B: connected — show settings
    return (
      <div className="rounded-2xl border border-slate-100 dark:border-[#2D3D4F] shadow-sm p-6">
        <div className="flex items-center justify-between mb-5">
          <div className="flex items-center gap-3">
            <div className="flex items-center justify-center size-10 rounded-xl bg-[#CADCFC] dark:bg-[#1E2761]/40">
              <Send className="size-5 text-[#4A90D9]" />
            </div>
            <div>
              <h3 className="font-semibold text-slate-800 dark:text-babyPowder">
                Telegram сповіщення
              </h3>
              <div className="flex items-center gap-1.5 mt-0.5">
                <CheckCircle className="size-3.5 text-green-500" />
                <span className="text-xs text-green-600 dark:text-green-400 font-medium">
                  Підключено
                </span>
              </div>
            </div>
          </div>
        </div>

        <div className="space-y-4 mb-5">
          <p className="text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wide">
            Сповіщати про:
          </p>
          {(
            [
              { key: "notify_issues", label: "Нові заявки" },
              { key: "notify_passes", label: "Заявки на в'їзд" },
              { key: "notify_announcements", label: "Оголошення" },
            ] as const
          ).map(({ key, label }) => (
            <label key={key} className="flex items-center justify-between cursor-pointer">
              <span className="text-sm text-slate-700 dark:text-slate-300">{label}</span>
              <input
                type="checkbox"
                checked={status[key] ?? false}
                onChange={(e) => handleToggle(key, e.target.checked)}
                className="size-4 rounded accent-[#4A90D9] cursor-pointer"
              />
            </label>
          ))}
        </div>

        <button
          onClick={handleDisconnect}
          disabled={isDisconnecting}
          className="text-sm text-red-500 hover:text-red-600 dark:text-red-400 dark:hover:text-red-300 underline disabled:opacity-50 transition-colors"
        >
          {isDisconnecting ? "Відключення..." : "Відключити Telegram"}
        </button>
      </div>
    );
  };

  return (
    <TabsContent value="notifications">
      {renderContent()}
    </TabsContent>
  );
}
