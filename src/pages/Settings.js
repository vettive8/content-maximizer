import './Settings.css';
import { getAppLanguage, getAppTheme, setAppLanguage, setAppTheme, t } from '../utils/settings.js';

export function renderSettingsPage() {
    const language = getAppLanguage();
    const theme = getAppTheme();

    return `
    <div class="settings-page">
      <header class="settings-header">
        <h1>${t('settings_title', 'Settings')}</h1>
        <p>${t('settings_subtitle', 'Control application language and visual theme.')}</p>
      </header>

      <section class="settings-grid">
        <article class="settings-card">
          <h2>${t('settings_language_title', 'Language')}</h2>
          <p>${t('settings_language_desc', 'Choose the language used by AI generation defaults and interface labels.')}</p>
          <div class="settings-options" role="radiogroup" aria-label="${t('settings_language_title', 'Language')}">
            <button
              class="settings-option ${language === 'pl' ? 'active' : ''}"
              data-setting="language"
              data-value="pl"
              aria-pressed="${language === 'pl'}"
            >
              ${t('settings_language_polish', 'Polish')}
            </button>
            <button
              class="settings-option ${language === 'en' ? 'active' : ''}"
              data-setting="language"
              data-value="en"
              aria-pressed="${language === 'en'}"
            >
              ${t('settings_language_english', 'English')}
            </button>
          </div>
        </article>

        <article class="settings-card">
          <h2>${t('settings_theme_title', 'Theme')}</h2>
          <p>${t('settings_theme_desc', 'Switch between dark and light mode.')}</p>
          <div class="settings-options" role="radiogroup" aria-label="${t('settings_theme_title', 'Theme')}">
            <button
              class="settings-option ${theme === 'dark' ? 'active' : ''}"
              data-setting="theme"
              data-value="dark"
              aria-pressed="${theme === 'dark'}"
            >
              ${t('settings_theme_dark', 'Dark')}
            </button>
            <button
              class="settings-option ${theme === 'light' ? 'active' : ''}"
              data-setting="theme"
              data-value="light"
              aria-pressed="${theme === 'light'}"
            >
              ${t('settings_theme_light', 'Light')}
            </button>
          </div>
        </article>
      </section>

      <footer class="settings-footer">
        <span>${t('settings_saved', 'Saved automatically')}</span>
      </footer>
    </div>
  `;
}

export function initSettingsEvents() {
    document.querySelectorAll('.settings-option').forEach((button) => {
        button.addEventListener('click', () => {
            const settingName = button.getAttribute('data-setting');
            const settingValue = button.getAttribute('data-value');

            if (settingName === 'language') {
                setAppLanguage(settingValue);
                return;
            }

            if (settingName === 'theme') {
                setAppTheme(settingValue);
            }
        });
    });
}
