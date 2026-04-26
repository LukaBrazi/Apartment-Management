import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
	title: "Політика приватності | ApartmentOS",
	description:
		"Політика приватності ApartmentOS — як ми збираємо, обробляємо та захищаємо ваші персональні дані відповідно до GDPR та законодавства України.",
};

const PRIVACY_VERSION = "1.0";
const PRIVACY_EFFECTIVE_DATE = "26 квітня 2026";

export default function PrivacyPage() {
	return (
		<main className="mx-auto min-h-screen max-w-3xl bg-white px-6 py-12 text-[#0F172A]">
			<header className="mb-10 border-b border-[#E2E8F0] pb-6">
				<Link
					href="/"
					className="mb-4 inline-block text-sm text-[#1E2761] hover:underline"
				>
					← На головну
				</Link>
				<h1 className="text-3xl font-bold sm:text-4xl">
					Політика приватності
				</h1>
				<p className="mt-2 text-sm text-[#64748B]">
					Версія {PRIVACY_VERSION} · діє з {PRIVACY_EFFECTIVE_DATE}
				</p>
			</header>

			<article className="prose prose-slate max-w-none space-y-6 text-[15px] leading-relaxed">
				<section>
					<h2 className="text-xl font-semibold">1. Хто ми</h2>
					<p>
						ApartmentOS (далі — «Сервіс», «ми») — SaaS-платформа для
						управління багатоквартирними будинками. Ми діємо як
						процесор персональних даних на замовлення організацій
						(управляючих компаній, ОСББ), які виступають
						контролерами даних щодо своїх мешканців.
					</p>
				</section>

				<section>
					<h2 className="text-xl font-semibold">2. Які дані ми збираємо</h2>
					<ul className="list-disc pl-6">
						<li>
							<strong>Облікові:</strong> ім’я, прізвище, email,
							номер телефону, посада/роль (мешканець, диспетчер,
							охорона, працівник), приналежність до квартири.
						</li>
						<li>
							<strong>Контентні:</strong> заявки на ремонт,
							повідомлення, оголошення, фотографії, які Ви
							завантажуєте.
						</li>
						<li>
							<strong>Технічні:</strong> IP-адреса, User-Agent,
							час входу/виходу — для безпеки та аудиту.
						</li>
						<li>
							<strong>Згоди:</strong> історія прийняття Умов
							користування та цієї Політики (версія, дата, IP) —
							для виконання вимог GDPR Art. 7.
						</li>
					</ul>
					<p>
						Ми <strong>не збираємо</strong> чутливі категорії даних
						(стан здоров’я, релігійні переконання, орієнтацію тощо)
						у рамках основного функціоналу.
					</p>
				</section>

				<section>
					<h2 className="text-xl font-semibold">3. Цілі обробки</h2>
					<ul className="list-disc pl-6">
						<li>надання основних функцій Сервісу;</li>
						<li>
							комунікація між мешканцями та керуючою компанією;
						</li>
						<li>
							безпека (виявлення зловживань, протидія несанкціонованим
							діям);
						</li>
						<li>аналітика для покращення Сервісу (агрегована, без ідентифікації);</li>
						<li>виконання правових зобов’язань.</li>
					</ul>
				</section>

				<section>
					<h2 className="text-xl font-semibold">
						4. Правові підстави (GDPR Art. 6)
					</h2>
					<ul className="list-disc pl-6">
						<li>
							<strong>Виконання договору</strong> — обробка облікових
							даних для надання Сервісу;
						</li>
						<li>
							<strong>Згода</strong> — для маркетингових
							комунікацій та необов’язкових функцій;
						</li>
						<li>
							<strong>Законні інтереси</strong> — безпека Сервісу,
							запобігання шахрайству;
						</li>
						<li>
							<strong>Виконання правових зобов’язань</strong> —
							зокрема, ведення журналу згод відповідно до GDPR.
						</li>
					</ul>
				</section>

				<section>
					<h2 className="text-xl font-semibold">5. Передача третім сторонам</h2>
					<p>
						Ми не продаємо персональні дані. Передача можлива лише:
					</p>
					<ul className="list-disc pl-6">
						<li>
							організації-контролеру (вашій управляючій компанії
							або ОСББ);
						</li>
						<li>
							інфраструктурним підрядникам (хмарний хостинг,
							доставка email, аналітика помилок) — на умовах
							договорів про обробку даних (DPA);
						</li>
						<li>
							державним органам — у випадках, прямо передбачених
							законом.
						</li>
					</ul>
				</section>

				<section>
					<h2 className="text-xl font-semibold">6. Терміни зберігання</h2>
					<ul className="list-disc pl-6">
						<li>
							облікові дані — поки активний обліковий запис плюс
							12 місяців після деактивації;
						</li>
						<li>
							журнал згод (ConsentLog) — необмежено, як юридичний
							доказ виконання GDPR;
						</li>
						<li>
							логи безпеки — 90 днів;
						</li>
						<li>
							резервні копії БД — 30 днів.
						</li>
					</ul>
				</section>

				<section>
					<h2 className="text-xl font-semibold">7. Ваші права (GDPR Art. 12–22)</h2>
					<p>Ви маєте право:</p>
					<ul className="list-disc pl-6">
						<li>отримати копію своїх даних (доступ);</li>
						<li>виправити неточні дані;</li>
						<li>видалити дані («право бути забутим»);</li>
						<li>обмежити обробку;</li>
						<li>заперечити проти обробки;</li>
						<li>перенести дані до іншого сервісу;</li>
						<li>відкликати згоду в будь-який момент.</li>
					</ul>
					<p>
						Для реалізації цих прав звертайтесь до адміністратора
						Вашої організації або напряму до нас на{" "}
						<a
							href="mailto:privacy@apartmentos.org"
							className="text-[#1E2761] underline"
						>
							privacy@apartmentos.org
						</a>
						. Ми відповімо протягом 30 днів.
					</p>
				</section>

				<section>
					<h2 className="text-xl font-semibold">8. Cookies</h2>
					<p>
						Ми використовуємо лише технічно необхідні cookies для
						підтримки сесії користувача (наприклад, <code>logged_in</code>).
						Маркетингові або аналітичні cookies без Вашої окремої
						згоди не встановлюються.
					</p>
				</section>

				<section>
					<h2 className="text-xl font-semibold">9. Безпека</h2>
					<p>
						Ми використовуємо HTTPS, шифрування паролів (Argon2),
						JWT-токени з обмеженим терміном дії, role-based access
						control та регулярні security-аудити для захисту Ваших
						даних.
					</p>
				</section>

				<section>
					<h2 className="text-xl font-semibold">10. Зміни Політики</h2>
					<p>
						Ми можемо оновлювати цю Політику. Про суттєві зміни Вам
						буде повідомлено через інтерфейс Сервісу і запропоновано
						повторно прийняти оновлену редакцію.
					</p>
				</section>

				<section>
					<h2 className="text-xl font-semibold">11. Контакти</h2>
					<p>
						Data Protection Officer (DPO):{" "}
						<a
							href="mailto:privacy@apartmentos.org"
							className="text-[#1E2761] underline"
						>
							privacy@apartmentos.org
						</a>
					</p>
					<p>
						Скарги можна також подати до Уповноваженого Верховної
						Ради України з прав людини або до національного органу з
						захисту даних у Вашій юрисдикції.
					</p>
				</section>
			</article>

			<footer className="mt-12 border-t border-[#E2E8F0] pt-6 text-sm text-[#64748B]">
				<p>
					Дивіться також:{" "}
					<Link
						href="/terms"
						className="text-[#1E2761] underline"
					>
						Умови користування
					</Link>
					.
				</p>
			</footer>
		</main>
	);
}
