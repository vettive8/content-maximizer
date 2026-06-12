import './AIEngine.css';
import { geminiModels, getCostClass, getCostDisplay, getStatusBadge } from '../data/models.js';
import {
  getApiKey,
  setApiKey,
  getSelectedModel,
  setSelectedModel,
  syncAIConfigToBackend
} from '../utils/storage.js';
import { getAppLanguage } from '../utils/settings.js';

function getAiEngineUiText() {
  const isPolish = getAppLanguage() === 'pl';
  if (isPolish) {
    return {
      engineName: 'Silnik AI',
      title: 'Konfiguracja',
      subtitle: 'Zarzadzaj kluczem Gemini API i modelem uzywanym przez backend.',
      keyTitle: 'Klucz Gemini API',
      keySubtitle: 'Przechowywany w przegladarce i synchronizowany z konfiguracja backendu.',
      keyPlaceholder: 'Wprowadz klucz Gemini API...',
      show: 'POKAZ',
      hide: 'UKRYJ',
      saveKey: 'Zapisz Klucz',
      modelSelection: 'Wybor Modelu',
      modelSelectionSubtitle: 'Wybierz model uzywany przez endpointy generowania.',
      updated: 'Aktualizacja',
      knowledgeCutoff: 'Zakres wiedzy',
      cost: 'Koszt',
      syncing: 'Synchronizacja...',
      saved: 'Zapisano',
      syncFailed: 'Blad synchronizacji'
    };
  }
  return {
    engineName: 'AI Engine',
    title: 'Configuration',
    subtitle: 'Manage your Gemini API key and model used by backend processing.',
    keyTitle: 'Gemini API Key',
    keySubtitle: 'Stored in browser and synced to backend runtime config.',
    keyPlaceholder: 'Enter your Gemini API key...',
    show: 'SHOW',
    hide: 'HIDE',
    saveKey: 'Save Key',
    modelSelection: 'Model Selection',
    modelSelectionSubtitle: 'Choose the model used by backend generation endpoints.',
    updated: 'Updated',
    knowledgeCutoff: 'Knowledge Cutoff',
    cost: 'Cost',
    syncing: 'Syncing...',
    saved: 'Saved',
    syncFailed: 'Sync Failed'
  };
}

export function renderAIEnginePage() {
  const ui = getAiEngineUiText();
  const currentKey = getApiKey();
  const selectedModel = getSelectedModel();

  return `
    <div class="ai-engine-page">
      <header class="page-header">
        <h1>${ui.engineName} <span class="text-gradient">${ui.title}</span></h1>
        <p>${ui.subtitle}</p>
      </header>

      <section class="api-key-section">
        <div class="section-card api-key-card">
          <div class="card-header">
            <div class="card-icon gemini-icon">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                <path d="M12 2L2 7L12 12L22 7L12 2Z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                <path d="M2 17L12 22L22 17" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                <path d="M2 12L12 17L22 12" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
            </div>
            <div class="card-title-group">
              <h3>${ui.keyTitle}</h3>
              <p>${ui.keySubtitle}</p>
            </div>
          </div>

          <div class="api-key-input-wrapper">
            <input
              type="password"
              id="api-key-input"
              class="api-key-input"
              placeholder="${ui.keyPlaceholder}"
              value="${currentKey || ''}"
            />
            <button id="toggle-key-btn" class="btn btn-ghost toggle-key-btn">${ui.show}</button>
            <button id="save-key-btn" class="btn btn-primary save-key-btn">${ui.saveKey}</button>
          </div>
        </div>
      </section>

      <section class="model-selection-section">
        <div class="section-header">
          <div class="section-icon">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
              <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2"/>
              <path d="M12 6V12L16 14" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
            </svg>
          </div>
          <div>
            <h3>${ui.modelSelection}</h3>
            <p>${ui.modelSelectionSubtitle}</p>
          </div>
        </div>

        <div class="models-grid">
          ${geminiModels.map((model) => `
            <div class="model-card ${model.id === selectedModel ? 'selected' : ''}" data-model-id="${model.id}">
              ${model.id === selectedModel ? '<div class="selected-check">OK</div>' : ''}
              <h4 class="model-name">${model.name}</h4>
              <p class="model-description">${model.description}</p>
              <div class="model-meta">
                <div class="meta-item">
                  <span class="meta-label">${ui.updated}</span>
                  <span class="meta-value">${model.updated}</span>
                </div>
                <div class="meta-item">
                  <span class="meta-label">${ui.knowledgeCutoff}</span>
                  <span class="meta-value">${model.knowledgeCutoff}</span>
                </div>
              </div>
              <div class="model-footer">
                <span class="cost ${getCostClass(model.cost)}">${ui.cost}: ${getCostDisplay(model.cost)}</span>
                ${getStatusBadge(model.status, getAppLanguage())}
              </div>
            </div>
          `).join('')}
        </div>
      </section>
    </div>
  `;
}

function showSaveState(button, text, isError = false) {
  if (!button) return;
  button.textContent = text;
  if (isError) {
    button.classList.remove('saved');
  } else {
    button.classList.add('saved');
  }
  setTimeout(() => {
    button.textContent = getAiEngineUiText().saveKey;
    button.classList.remove('saved');
    button.disabled = false;
  }, 2000);
}

export function initAIEngineEvents() {
  const apiKeyInput = document.getElementById('api-key-input');
  const toggleKeyBtn = document.getElementById('toggle-key-btn');
  const saveKeyBtn = document.getElementById('save-key-btn');
  const modelCards = document.querySelectorAll('.model-card');

  toggleKeyBtn?.addEventListener('click', () => {
    if (apiKeyInput.type === 'password') {
      apiKeyInput.type = 'text';
      toggleKeyBtn.textContent = getAiEngineUiText().hide;
    } else {
      apiKeyInput.type = 'password';
      toggleKeyBtn.textContent = getAiEngineUiText().show;
    }
  });

  saveKeyBtn?.addEventListener('click', async () => {
    const key = apiKeyInput.value.trim();
    if (!key) return;

    setApiKey(key);
    saveKeyBtn.disabled = true;
    saveKeyBtn.textContent = getAiEngineUiText().syncing;

    try {
      await syncAIConfigToBackend();
      showSaveState(saveKeyBtn, getAiEngineUiText().saved);
    } catch (error) {
      console.error('Failed to sync API key:', error);
      showSaveState(saveKeyBtn, getAiEngineUiText().syncFailed, true);
    }
  });

  modelCards.forEach((card) => {
    card.addEventListener('click', async () => {
      const modelId = card.dataset.modelId;
      if (!modelId) return;

      setSelectedModel(modelId);
      document.querySelectorAll('.model-card').forEach((item) => {
        item.classList.remove('selected');
        const check = item.querySelector('.selected-check');
        if (check) check.remove();
      });
      card.classList.add('selected');
      const check = document.createElement('div');
      check.className = 'selected-check';
      check.textContent = 'OK';
      card.prepend(check);

      try {
        await syncAIConfigToBackend();
      } catch (error) {
        console.error('Failed to sync selected model:', error);
      }
    });
  });
}
