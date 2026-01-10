import dayjs from 'dayjs';

// Import all locales using a DRY approach
const locales = [
	'af', 'am', 'ar', 'az', 'be', 'bg', 'bi', 'bm', 'bn', 'bo', 'br', 'bs',
	'ca', 'cs', 'cv', 'cy', 'da', 'de', 'dv', 'el', 'en', 'eo', 'es', 'et',
	'eu', 'fa', 'fi', 'fo', 'fr', 'fy', 'ga', 'gd', 'gl', 'gu', 'he', 'hi',
	'hr', 'ht', 'hu', 'id', 'is', 'it', 'ja', 'jv', 'ka', 'kk', 'km', 'kn',
	'ko', 'ku', 'ky', 'lb', 'lo', 'lt', 'lv', 'me', 'mi', 'mk', 'ml', 'mn',
	'mr', 'ms', 'mt', 'my', 'nb', 'ne', 'nl', 'nn', 'pl', 'pt', 'ro', 'ru',
	'rw', 'sd', 'se', 'si', 'sk', 'sl', 'sq', 'sr', 'ss', 'sv', 'sw', 'ta',
	'te', 'tet', 'tg', 'th', 'tk', 'tlh', 'tr', 'tzl', 'tzm', 'uk', 'ur',
	'uz', 'vi', 'yo', 'zh', 'zh-tw'
];

// Dynamically import all locales
locales.forEach(locale => {
	import(`dayjs/locale/${locale}.js`)
		.then(() => dayjs.locale(locale))
		.catch(e => console.error(`Failed to load locale ${locale}`, e));
});

export async function loadLocale(locales) {
	for (const locale of locales) {
		try {
			dayjs.locale(locale);
			break; // Stop after successfully loading the first available locale
		} catch (error) {
			console.error(`Could not load locale '${locale}':`, error);
		}
	}
}

export default dayjs;
