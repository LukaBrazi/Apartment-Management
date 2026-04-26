"use client";

import type { Metadata } from "next";
import { useGetSiteSettingsQuery } from "@/lib/redux/features/siteSettings/siteSettingsApiSlice";
import { useAppSelector } from "@/lib/redux/hooks/typedHooks";
import FeedbackForm from "@/components/feedback/FeedbackForm";
import Image from "next/image";

/**
 * Note: Metadata exports are not supported in 'use client' components.
 * SEO metadata is handled via the root layout or a separate metadata route.
 */

/**
 * Contact persons page showing all active staff and emergency contacts.
 * Data is loaded from /api/v1/site-settings/ via RTK Query.
 */
export default function ContactsPage() {
  const { data: siteSettingsData, isLoading, error } = useGetSiteSettingsQuery();
  const { isAuthenticated } = useAppSelector((state) => state.auth);

  const contacts = siteSettingsData?.contacts || [];
  const settings = siteSettingsData?.settings;

  // Group contacts by emergency status
  const regularContacts = contacts.filter((c) => !c.is_emergency);
  const emergencyContacts = contacts.filter((c) => c.is_emergency);

  return (
    <div className="flex flex-col gap-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-[#111827] dark:text-white">
          Контакти
        </h1>
        <p className="text-sm text-[#6B7280] dark:text-[#9CA3AF] mt-1">
          Контакти служб та управителя {settings?.display_complex_name || "будинку"}
        </p>
      </div>

      {/* Loading state */}
      {isLoading && (
        <div className="flex justify-center items-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[#3D7A8A]" />
        </div>
      )}

      {/* Error state */}
      {error && (
        <div className="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
          <p className="text-red-600 dark:text-red-400">
            Помилка завантаження контактів. Спробуйте пізніше.
          </p>
        </div>
      )}

      {/* Empty state */}
      {!isLoading && !error && contacts.length === 0 && (
        <div className="p-8 bg-gray-50 dark:bg-gray-800 rounded-lg text-center">
          <p className="text-[#6B7280] dark:text-[#9CA3AF]">
            Контакти ще не додані. Спробуйте пізніше.
          </p>
        </div>
      )}

      {/* Regular Contacts Section */}
      {!isLoading && regularContacts.length > 0 && (
        <div>
          <h2 className="text-xl font-semibold text-[#111827] dark:text-white mb-4">
            Управління та послуги
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {regularContacts.map((contact) => (
              <ContactCard key={contact.id} contact={contact} />
            ))}
          </div>
        </div>
      )}

      {/* Emergency Contacts Section */}
      {!isLoading && emergencyContacts.length > 0 && (
        <div>
          <h2 className="text-xl font-semibold text-[#111827] dark:text-white mb-4">
            Аварійні служби
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {emergencyContacts.map((contact) => (
              <ContactCard key={contact.id} contact={contact} isEmergency />
            ))}
          </div>
        </div>
      )}

      {/* Support Information */}
      {!isLoading && settings && (
        <div className="mt-8 p-6 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
          <h3 className="text-lg font-semibold text-[#111827] dark:text-white mb-3">
            Загальна інформація про підтримку
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {settings.support_email && (
              <div>
                <p className="text-sm text-[#6B7280] dark:text-[#9CA3AF]">Email</p>
                <a
                  href={`mailto:${settings.support_email}`}
                  className="text-[#3D7A8A] dark:text-[#5BA3B8] hover:underline font-medium"
                >
                  {settings.support_email}
                </a>
              </div>
            )}
            {settings.support_phone && (
              <div>
                <p className="text-sm text-[#6B7280] dark:text-[#9CA3AF]">Телефон</p>
                <a
                  href={`tel:${settings.support_phone}`}
                  className="text-[#3D7A8A] dark:text-[#5BA3B8] hover:underline font-medium"
                >
                  {settings.support_phone}
                </a>
              </div>
            )}
            {settings.support_hours && (
              <div>
                <p className="text-sm text-[#6B7280] dark:text-[#9CA3AF]">Години роботи</p>
                <p className="font-medium text-[#111827] dark:text-white">
                  {settings.support_hours}
                </p>
              </div>
            )}
            <div>
              <p className="text-sm text-[#6B7280] dark:text-[#9CA3AF]">Мессенджери</p>
              <div className="flex gap-3 mt-1">
                {settings.telegram_url && (
                  <a
                    href={settings.telegram_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-[#3D7A8A] dark:text-[#5BA3B8] hover:underline text-sm font-medium"
                  >
                    Telegram
                  </a>
                )}
                {settings.viber_url && (
                  <a
                    href={settings.viber_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-[#3D7A8A] dark:text-[#5BA3B8] hover:underline text-sm font-medium"
                  >
                    Viber
                  </a>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Feedback Form — visible only to authenticated users */}
      {isAuthenticated && (
        <section className="mt-10 rounded-2xl border border-[#F1F5F9] bg-white p-6 shadow-sm dark:border-[#2D3D4F] dark:bg-[#1C2B3A]">
          <h2 className="mb-1 text-lg font-semibold text-[#0F172A] dark:text-white">
            Відгук про застосунок
          </h2>
          <p className="mb-4 text-sm text-[#6B7280]">
            Ця форма — для відгуків про роботу застосунку ApartmentOS: зручність інтерфейсу,
            помилки, побажання щодо функціоналу. Для звернень до керуючої компанії або з питань
            обслуговування будинку — скористайтесь контактами вище або розділом «Заявки».
          </p>
          <FeedbackForm />
        </section>
      )}
    </div>
  );
}

/**
 * Individual contact card component.
 */
interface ContactCardProps {
  contact: any;
  isEmergency?: boolean;
}

function ContactCard({ contact, isEmergency = false }: ContactCardProps) {
  return (
    <div
      className={`p-4 rounded-lg border transition-all ${
        isEmergency
          ? "border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-900/10"
          : "border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800"
      } hover:shadow-md`}
    >
      {/* Photo */}
      {contact.photo_url && (
        <div className="mb-4">
          <img
            src={contact.photo_url}
            alt={contact.name}
            className="w-full h-32 object-cover rounded-md"
          />
        </div>
      )}

      {/* Name & Role */}
      <h3 className="text-lg font-semibold text-[#111827] dark:text-white">
        {contact.name}
      </h3>
      <p className="text-sm text-[#6B7280] dark:text-[#9CA3AF]">
        {contact.role_display}
      </p>

      {/* Position */}
      {contact.position && (
        <p className="text-sm text-[#6B7280] dark:text-[#9CA3AF] italic mt-1">
          {contact.position}
        </p>
      )}

      {/* Contact Details */}
      <div className="mt-3 space-y-1 text-sm">
        {contact.phone && (
          <div>
            <a
              href={`tel:${contact.phone}`}
              className="text-[#3D7A8A] dark:text-[#5BA3B8] hover:underline"
            >
              📞 {contact.phone}
            </a>
          </div>
        )}
        {contact.email && (
          <div>
            <a
              href={`mailto:${contact.email}`}
              className="text-[#3D7A8A] dark:text-[#5BA3B8] hover:underline"
            >
              ✉️ {contact.email}
            </a>
          </div>
        )}
        {contact.telegram && (
          <div>
            <a
              href={`https://t.me/${contact.telegram}`}
              target="_blank"
              rel="noopener noreferrer"
              className="text-[#3D7A8A] dark:text-[#5BA3B8] hover:underline"
            >
              💬 Telegram: @{contact.telegram}
            </a>
          </div>
        )}
      </div>

      {/* Working Hours */}
      {contact.working_hours && (
        <div className="mt-3 pt-3 border-t border-gray-200 dark:border-gray-700">
          <p className="text-xs text-[#6B7280] dark:text-[#9CA3AF]">
            <span className="font-semibold">Час роботи:</span> {contact.working_hours}
          </p>
        </div>
      )}
    </div>
  );
}
