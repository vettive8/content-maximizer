import { isSupportedModel } from '../data/models.js';
import { apiUrl } from './api.js';

const STORAGE_KEYS = {
    API_KEY: 'meos_gemini_api_key',
    SELECTED_MODEL: 'meos_selected_model'
};

const DEFAULT_MODEL = 'gemini-3-flash-preview';

export function getApiKey() {
    return localStorage.getItem(STORAGE_KEYS.API_KEY) || '';
}

export function setApiKey(key) {
    localStorage.setItem(STORAGE_KEYS.API_KEY, key);
}

export function getSelectedModel() {
    const selected = localStorage.getItem(STORAGE_KEYS.SELECTED_MODEL) || DEFAULT_MODEL;
    return isSupportedModel(selected) ? selected : DEFAULT_MODEL;
}

export function setSelectedModel(modelId) {
    localStorage.setItem(STORAGE_KEYS.SELECTED_MODEL, modelId);
}

export function getAIConfig() {
    return {
        api_key: getApiKey(),
        model: getSelectedModel()
    };
}

export function withAIConfig(payload = {}) {
    return {
        ...payload,
        ai_config: getAIConfig()
    };
}

export async function syncAIConfigToBackend() {
    const response = await fetch(apiUrl('/api/ai/config'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(getAIConfig())
    });

    if (!response.ok) {
        throw new Error(`AI config sync failed with status ${response.status}`);
    }

    return response.json();
}
