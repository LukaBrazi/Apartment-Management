"use client";

import { useGetUserProfileQuery } from "@/lib/redux/features/users/usersApiSlice";
import Spinner from "@/components/shared/Spinner";
import { TabsContent } from "@/components/ui/tabs";
import { ProfileItem } from "./ProfileItem";
import {
	BadgeCheck,
	Briefcase,
	CalendarDays,
	Contact,
	Home,
	Hotel,
	Map,
	MapPinnedIcon,
	Star,
	UserRoundCheck,
} from "lucide-react";
import { formatDate } from "@/utils";
import ProtectedRoute from "../shared/ProtectedRoutes";
import Link from "next/link";
import { Button } from "@/components/ui/button";

const genderLabels: Record<string, string> = {
	male: "Чоловік",
	female: "Жінка",
	other: "Інше",
};

const countryLabels: Record<string, string> = {
	Ukraine: "Україна",
};

const occupationLabels: Record<string, string> = {
	mason: "Муляр",
	carpenter: "Тесляр",
	plumber: "Сантехнік",
	roofer: "Покрівельник",
	painter: "Маляр",
	electrician: "Електрик",
	hvac: "Вентиляція/Кліматизація",
	tenant: "Мешканець",
	guard: "Охоронець",
};

function AboutContent() {
	const { data, isLoading } = useGetUserProfileQuery();
	const profile = data?.profile;

	// Репутація видима тільки для персоналу (охорона, сантехніки тощо)
	// Мешканці (tenant) не бачать своєї репутації
	const isWorker = profile?.is_staff || (profile?.occupation && profile.occupation !== "tenant");

	if (isLoading) {
		return (
			<div className="flex-center pt-32">
				<Spinner size="xl" />
			</div>
		);
	}

	return (
		<TabsContent value="about">
			<div className="grid grid-cols-1 gap-4 p-4 md:grid-cols-2">
				{/* column 1 */}
				<div className="space-y-3">
					<ProfileItem
						icon={<Contact className="tab-icon" />}
						label="Ім'я"
						value={profile?.full_name || ""}
					/>
					<ProfileItem
						icon={<UserRoundCheck className="tab-icon" />}
						label="Стать"
						value={genderLabels[profile?.gender || ""] || profile?.gender || ""}
					/>
					<ProfileItem
						icon={<CalendarDays className="tab-icon" />}
						label="Дата реєстрації"
						value={formatDate(profile?.date_joined).toString() || ""}
					/>
					{isWorker && (
						<ProfileItem
							icon={<BadgeCheck className="tab-icon" />}
							label="Репутація"
							value={`${profile?.reputation} з 100` || ""}
						/>
					)}
					<ProfileItem
						icon={<Map className="tab-icon" />}
						label="Країна"
						value={countryLabels[profile?.country_of_origin || ""] || profile?.country_of_origin || ""}
					/>
					<ProfileItem
						icon={<MapPinnedIcon className="tab-icon" />}
						label="Місто"
						value={profile?.city_of_origin || ""}
					/>
				</div>
				{/* column 2 */}
				<div className="space-y-3">
					<ProfileItem
						icon={<Briefcase className="tab-icon" />}
						label="Рід занять"
						value={occupationLabels[profile?.occupation || ""] || profile?.occupation || ""}
					/>
					<ProfileItem
						icon={<Home className="tab-icon" />}
						label="Квартира"
						value={profile?.apartment?.unit_number || "Немає"}
					/>
					<ProfileItem
						icon={<Hotel className="tab-icon" />}
						label="Будинок"
						value={`${profile?.apartment?.building || "Немає"}, Поверх: ${profile?.apartment?.floor || "Немає"}`}
					/>
					<ProfileItem
						icon={<Star className="tab-icon" />}
						label="Середня оцінка"
						value={profile?.average_rating?.toString() || ""}
					/>

					<div className="prose max-w-none">
						<p>
							<span className="tab-font">Про себе:</span>
							<span className="dark:text-babyPowder">
								{profile?.bio || "Ви ще не додали інформацію про себе!"}
							</span>
						</p>
					</div>
				</div>
			</div>
			<div className="flex cursor-pointer flex-row justify-between p-4">
				<Link href="/profile/edit">
					<Button className="h3-semibold electricIndigo-gradient text-babyPowder w-64 rounded-lg">
						Оновити профіль
					</Button>
				</Link>
				<Link href="/apartment">
					<Button className="h3-semibold electricIndigo-gradient text-babyPowder w-64 rounded-lg">
						Додати квартиру
					</Button>
				</Link>
			</div>
		</TabsContent>
	);
}

export default function About() {
	return (
		<ProtectedRoute>
			<AboutContent />
		</ProtectedRoute>
	);
}
