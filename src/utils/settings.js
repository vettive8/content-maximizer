const STORAGE_KEYS = {
    LANGUAGE: 'meos_app_language',
    THEME: 'meos_app_theme'
};

const SUPPORTED_LANGUAGES = ['pl', 'en'];
const SUPPORTED_THEMES = ['dark', 'light'];

const TRANSLATIONS = {
    en: {
        sidebar_content_maximizer: 'Content Maximizer',
        sidebar_growth_strategy: 'Business Growth Strategy',
        sidebar_script_pipeline: 'Script Management',
        sidebar_project_history: 'Project History',
        sidebar_clear_all: 'Clear All',
        sidebar_no_history: 'No history yet',
        sidebar_delete_project: 'Delete Project',
        sidebar_delete_confirm: 'Are you sure you want to delete this project?',
        sidebar_clear_confirm: 'Are you sure you want to delete ALL project history? This cannot be undone.',
        sidebar_ai_engine: 'AI Engine',
        sidebar_model_key: 'Model & Key',
        sidebar_user: 'User',
        sidebar_free_plan: 'Free Plan',
        sidebar_settings: 'Settings',
        settings_title: 'Settings',
        settings_subtitle: 'Control application language and visual theme.',
        settings_language_title: 'Language',
        settings_language_desc: 'Choose the language used by AI generation defaults and interface labels.',
        settings_theme_title: 'Theme',
        settings_theme_desc: 'Switch between dark and light mode.',
        settings_language_polish: 'Polish',
        settings_language_english: 'English',
        settings_theme_dark: 'Dark',
        settings_theme_light: 'Light',
        settings_saved: 'Saved automatically'
    },
    pl: {
        sidebar_content_maximizer: 'Maksymalizator Treści',
        sidebar_growth_strategy: 'Strategia Wzrostu Biznesu',
        sidebar_script_pipeline: 'Zarządzanie skryptami',
        sidebar_project_history: 'Historia Projektów',
        sidebar_clear_all: 'Wyczyść',
        sidebar_no_history: 'Brak historii',
        sidebar_delete_project: 'Usuń projekt',
        sidebar_delete_confirm: 'Czy na pewno chcesz usunąć ten projekt?',
        sidebar_clear_confirm: 'Czy na pewno chcesz usunąć CAŁĄ historię projektów? Tej operacji nie można cofnąć.',
        sidebar_ai_engine: 'Silnik AI',
        sidebar_model_key: 'Model i Klucz',
        sidebar_user: 'Użytkownik',
        sidebar_free_plan: 'Plan Darmowy',
        sidebar_settings: 'Ustawienia',
        settings_title: 'Ustawienia',
        settings_subtitle: 'Zarządzaj językiem aplikacji i motywem wizualnym.',
        settings_language_title: 'Język',
        settings_language_desc: 'Wybierz język domyślny dla generowania AI i etykiet interfejsu.',
        settings_theme_title: 'Motyw',
        settings_theme_desc: 'Przełączaj między trybem ciemnym i jasnym.',
        settings_language_polish: 'Polski',
        settings_language_english: 'Angielski',
        settings_theme_dark: 'Ciemny',
        settings_theme_light: 'Jasny',
        settings_saved: 'Zapisano automatycznie'
    }
};

function normalizeLanguage(language) {
    return SUPPORTED_LANGUAGES.includes(language) ? language : null;
}

function normalizeTheme(theme) {
    return SUPPORTED_THEMES.includes(theme) ? theme : null;
}

function resolveDefaultLanguage() {
    const navLanguage = (navigator.language || '').toLowerCase();
    return navLanguage.startsWith('pl') ? 'pl' : 'en';
}

function resolveDefaultTheme() {
    return window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark';
}

function emitSettingsChange() {
    window.dispatchEvent(new CustomEvent('app-settings-changed', {
        detail: {
            language: getAppLanguage(),
            theme: getAppTheme()
        }
    }));
}

export function getAppLanguage() {
    const stored = normalizeLanguage(localStorage.getItem(STORAGE_KEYS.LANGUAGE));
    return stored || resolveDefaultLanguage();
}

export function setAppLanguage(language) {
    const normalized = normalizeLanguage(language);
    if (!normalized) return;
    if (normalized === getAppLanguage()) return;
    localStorage.setItem(STORAGE_KEYS.LANGUAGE, normalized);
    emitSettingsChange();
}

export function getAppTheme() {
    const stored = normalizeTheme(localStorage.getItem(STORAGE_KEYS.THEME));
    return stored || resolveDefaultTheme();
}

export function applyTheme(theme = getAppTheme()) {
    const normalized = normalizeTheme(theme) || 'dark';
    document.documentElement.setAttribute('data-theme', normalized);
    document.documentElement.style.colorScheme = normalized;
}

export function setAppTheme(theme) {
    const normalized = normalizeTheme(theme);
    if (!normalized) return;
    if (normalized === getAppTheme()) return;
    localStorage.setItem(STORAGE_KEYS.THEME, normalized);
    applyTheme(normalized);
    emitSettingsChange();
}

export function initializeAppSettings() {
    applyTheme(getAppTheme());
}

export function t(key, fallback = '') {
    const language = getAppLanguage();
    const translated = TRANSLATIONS[language]?.[key];
    if (translated) return translated;
    const english = TRANSLATIONS.en[key];
    if (english) return english;
    return fallback || key;
}
