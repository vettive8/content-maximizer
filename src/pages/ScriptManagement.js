import './ScriptManagement.css';
import { encodeInlineArg, escapeAttribute, sanitizeDeep } from '../utils/sanitize.js';
import { getAppLanguage } from '../utils/settings.js';
import { apiUrl } from '../utils/api.js';

// State
let scripts = [];
let selectedScript = null;
let isLoading = false;

function getScriptManagementUiText() {
  const isPolish = getAppLanguage() === 'pl';
  if (isPolish) {
    return {
      title: 'Zarządzanie skryptami',
      subtitle: 'Zarządzaj skryptami wideo od wersji roboczej do publikacji',
      written: 'Napisane',
      scheduled: 'Zaplanowane',
      published: 'Opublikowane',
      loading: 'Ładowanie...',
      noScripts: 'Brak skryptów',
      untitledScript: 'Skrypt bez tytułu',
      chaptersSuffix: 'rozdziałów',
      createdLabel: 'Utworzono',
      openProject: 'Otwórz projekt',
      openProjectTitle: 'Otwórz powiązany projekt',
      openProjectMissing: 'Brak powiązanego projektu dla tego skryptu',
      deleteScript: 'Usuń skrypt',
      close: 'Zamknij',
      status: 'Status',
      scheduledFor: 'Zaplanowano na',
      chapterPrefix: 'Rozdział',
      noChapters: 'Brak rozdziałów',
      saveChanges: 'Zapisz zmiany',
      savedSuccess: 'Skrypt zapisany pomyślnie.',
      savedError: 'Nie udało się zapisać skryptu.',
      deleteConfirm: 'Czy na pewno chcesz usunąć ten skrypt?',
      noLinkedProject: 'Nie znaleziono powiązanego projektu dla tego skryptu.',
      handlerMissing: 'Handler projektu jest niedostępny.',
      projectNotFound: 'Nie udało się znaleźć powiązanego projektu w historii projektów.',
      projectLoadFailed: 'Nie udało się wczytać powiązanego projektu.'
    };
  }

  return {
    title: 'Script Management',
    subtitle: 'Manage your video scripts from draft to publication',
    written: 'Written',
    scheduled: 'Scheduled',
    published: 'Published',
    loading: 'Loading...',
    noScripts: 'No scripts yet',
    untitledScript: 'Untitled Script',
    chaptersSuffix: 'chapters',
    createdLabel: 'Created',
    openProject: 'Open Project',
    openProjectTitle: 'Open linked project',
    openProjectMissing: 'No linked project found for this script',
    deleteScript: 'Delete Script',
    close: 'Close',
    status: 'Status',
    scheduledFor: 'Scheduled for',
    chapterPrefix: 'Chapter',
    noChapters: 'No chapters found',
    saveChanges: 'Save Changes',
    savedSuccess: 'Script saved successfully.',
    savedError: 'Failed to save script.',
    deleteConfirm: 'Are you sure you want to delete this script?',
    noLinkedProject: 'No linked project was found for this script.',
    handlerMissing: 'Project handler is not available.',
    projectNotFound: 'Could not find the associated project in Project History.',
    projectLoadFailed: 'Failed to load the associated project.'
  };
}
function decodeInlineArg(value) {
  try {
    return decodeURIComponent(value || '');
  } catch {
    return '';
  }
}

export function renderScriptManagementPage() {
  const ui = getScriptManagementUiText();
  const writtenCount = scripts.filter((s) => s.status === 'written').length;
  const scheduledCount = scripts.filter((s) => s.status === 'scheduled').length;
  const publishedCount = scripts.filter((s) => s.status === 'published').length;

  return `
    <div class="script-pipeline-page">
      <header class="pipeline-header">
        <div class="header-content">
          <h1>
            <span class="pipeline-title-icon" aria-hidden="true">&#x1F4DD;</span>
            ${ui.title}
          </h1>
          <p>${ui.subtitle}</p>
        </div>
      </header>

      <div class="pipeline-board">
        <div class="pipeline-column" data-status="written" ondragover="window.onDragOverColumn(event)" ondrop="window.onDropOnColumn(event, 'written')">
          <div class="column-header">
            <span class="column-icon" aria-hidden="true">&#x270F;&#xFE0F;</span>
            <h3 class="column-title">${ui.written}</h3>
            <span class="count">${writtenCount}</span>
          </div>
          <div class="column-cards">
            ${renderScriptCards('written')}
          </div>
        </div>

        <div class="pipeline-column" data-status="scheduled" ondragover="window.onDragOverColumn(event)" ondrop="window.onDropOnColumn(event, 'scheduled')">
          <div class="column-header">
            <span class="column-icon" aria-hidden="true">&#x1F4C5;</span>
            <h3 class="column-title">${ui.scheduled}</h3>
            <span class="count">${scheduledCount}</span>
          </div>
          <div class="column-cards">
            ${renderScriptCards('scheduled')}
          </div>
        </div>

        <div class="pipeline-column" data-status="published" ondragover="window.onDragOverColumn(event)" ondrop="window.onDropOnColumn(event, 'published')">
          <div class="column-header">
            <span class="column-icon" aria-hidden="true">&#x1F3AC;</span>
            <h3 class="column-title">${ui.published}</h3>
            <span class="count">${publishedCount}</span>
          </div>
          <div class="column-cards">
            ${renderScriptCards('published')}
          </div>
        </div>
      </div>

      ${selectedScript ? renderScriptModal() : ''}
      ${isLoading ? `<div class="pipeline-loading">${ui.loading}</div>` : ''}
    </div>
  `;
}

function renderScriptCards(status) {
  const ui = getScriptManagementUiText();
  const filteredScripts = scripts.filter((s) => s.status === status);

  if (filteredScripts.length === 0) {
    return `<div class="empty-column">${ui.noScripts}</div>`;
  }

  return filteredScripts.map((script) => {
    const safeScript = sanitizeDeep(script);
    const encodedId = encodeInlineArg(script?.id || '');
    const encodedProjectId = encodeInlineArg(script?.project_id || '');
    const hasLinkedProject = Boolean(script?.project_id);
    const createdAt = script?.created_at ? new Date(script.created_at).toLocaleDateString() : '-';
    const scheduledDate = script?.scheduled_date ? new Date(script.scheduled_date).toLocaleDateString() : '';

    return `
      <div class="script-card"
           draggable="true"
           ondragstart="window.onDragScript(event, decodeURIComponent('${encodedId}'))"
           onclick="window.openScriptModal(decodeURIComponent('${encodedId}'))">
        <div class="card-header">
          <h4>${safeScript.title || ui.untitledScript}</h4>
          <span class="chapter-count">${script.chapters?.length || 0} ${ui.chaptersSuffix}</span>
        </div>
        <p class="card-date">${ui.createdLabel}: ${createdAt}</p>
        ${scheduledDate ? `<p class="card-scheduled">&#x1F4C5; ${scheduledDate}</p>` : ''}
        <div class="card-actions">
          <button
            class="btn btn-primary btn-sm btn-open-project"
            ${hasLinkedProject ? '' : 'disabled'}
            title="${hasLinkedProject ? ui.openProjectTitle : ui.openProjectMissing}"
            onclick="event.stopPropagation(); window.openProjectFromScript(decodeURIComponent('${encodedProjectId}'))"
          >
            <span aria-hidden="true">&#x1F4C1;</span>
            ${ui.openProject}
          </button>
          <button class="btn-delete-card" onclick="event.stopPropagation(); window.deleteScript(decodeURIComponent('${encodedId}'))" title="${ui.deleteScript}" aria-label="${ui.deleteScript}">
            &#x1F5D1;&#xFE0F;
          </button>
        </div>
      </div>
    `;
  }).join('');
}

function renderScriptModal() {
  const ui = getScriptManagementUiText();
  const safeSelected = sanitizeDeep(selectedScript || {});
  const encodedId = encodeInlineArg(selectedScript?.id || '');

  return `
    <div class="modal-overlay" onclick="window.closeScriptModal()">
      <div class="script-modal" onclick="event.stopPropagation()">
        <header class="modal-header">
          <h2>${safeSelected.title || ui.untitledScript}</h2>
          <button class="btn-close" onclick="window.closeScriptModal()">${ui.close}</button>
        </header>

        <div class="modal-body">
          <div class="status-controls">
            <label>${ui.status}:</label>
            <select onchange="window.updateScriptStatus(decodeURIComponent('${encodedId}'), this.value)">
              <option value="written" ${selectedScript.status === 'written' ? 'selected' : ''}>${ui.written}</option>
              <option value="scheduled" ${selectedScript.status === 'scheduled' ? 'selected' : ''}>${ui.scheduled}</option>
              <option value="published" ${selectedScript.status === 'published' ? 'selected' : ''}>${ui.published}</option>
            </select>

            ${selectedScript.status === 'scheduled' ? `
              <label>${ui.scheduledFor}:</label>
              <input
                type="date"
                value="${escapeAttribute(selectedScript.scheduled_date || '')}"
                onchange="window.updateScheduledDate(decodeURIComponent('${encodedId}'), this.value)">
            ` : ''}
          </div>

          <div class="script-content">
            ${safeSelected.chapters?.map((chapter, index) => `
              <div class="chapter-block">
                <h4>${ui.chapterPrefix} ${index + 1}: ${chapter.title || ui.untitledScript}</h4>
                <textarea
                  class="chapter-editor"
                  onchange="window.updateChapterScript(decodeURIComponent('${encodedId}'), ${index}, this.value)"
                >${chapter.script || ''}</textarea>
              </div>
            `).join('') || `<p>${ui.noChapters}</p>`}
          </div>
        </div>

        <footer class="modal-footer">
          <button class="btn btn-subtle" onclick="window.closeScriptModal()">${ui.close}</button>
          <button class="btn btn-primary" onclick="window.saveScriptChanges()">${ui.saveChanges}</button>
        </footer>
      </div>
    </div>
  `;
}

// --- WINDOW FUNCTIONS ---

window.loadScripts = async function () {
  isLoading = true;
  render();
  try {
    const response = await fetch(apiUrl('/api/scripts/list'));
    const result = await response.json();
    if (result.success) {
      scripts = result.data || [];
    }
  } catch (e) {
    console.error('Failed to load scripts:', e);
  } finally {
    isLoading = false;
    render();
  }
};

window.saveScriptToPipeline = async function (scriptData) {
  try {
    const response = await fetch(apiUrl('/api/scripts/save'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(scriptData)
    });
    const result = await response.json();
    if (result.success) {
      scripts.push(result.data);
      render();
      return true;
    }
  } catch (e) {
    console.error('Failed to save script:', e);
  }
  return false;
};

window.openScriptModal = function (scriptId) {
  const normalizedId = decodeInlineArg(scriptId);
  selectedScript = scripts.find((script) => script.id === normalizedId);
  render();
};

window.closeScriptModal = function () {
  selectedScript = null;
  render();
};

window.updateScriptStatus = async function (scriptId, newStatus) {
  const normalizedId = decodeInlineArg(scriptId);
  try {
    const response = await fetch(apiUrl(`/api/scripts/${normalizedId}`), {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status: newStatus })
    });
    const result = await response.json();
    if (result.success) {
      const index = scripts.findIndex((script) => script.id === normalizedId);
      if (index >= 0) scripts[index].status = newStatus;
      if (selectedScript?.id === normalizedId) selectedScript.status = newStatus;
      render();
    }
  } catch (e) {
    console.error('Failed to update status:', e);
  }
};

window.updateScheduledDate = async function (scriptId, date) {
  const normalizedId = decodeInlineArg(scriptId);
  try {
    const response = await fetch(apiUrl(`/api/scripts/${normalizedId}`), {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ scheduled_date: date })
    });
    const result = await response.json();
    if (result.success) {
      const index = scripts.findIndex((script) => script.id === normalizedId);
      if (index >= 0) scripts[index].scheduled_date = date;
      if (selectedScript?.id === normalizedId) selectedScript.scheduled_date = date;
      render();
    }
  } catch (e) {
    console.error('Failed to update scheduled date:', e);
  }
};

window.updateChapterScript = function (scriptId, chapterIndex, text) {
  const normalizedId = decodeInlineArg(scriptId);
  if (selectedScript?.id === normalizedId && selectedScript.chapters?.[chapterIndex]) {
    selectedScript.chapters[chapterIndex].script = text;
  }
};

window.saveScriptChanges = async function () {
  if (!selectedScript) return;

  try {
    const response = await fetch(apiUrl(`/api/scripts/${selectedScript.id}`), {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ chapters: selectedScript.chapters })
    });
    const result = await response.json();
    if (result.success) {
      const index = scripts.findIndex((script) => script.id === selectedScript.id);
      if (index >= 0) scripts[index].chapters = selectedScript.chapters;
      alert(getScriptManagementUiText().savedSuccess);
    }
  } catch (e) {
    console.error('Failed to save script:', e);
    alert(getScriptManagementUiText().savedError);
  }
};

window.deleteScript = async function (scriptId) {
  const normalizedId = decodeInlineArg(scriptId);
  if (!confirm(getScriptManagementUiText().deleteConfirm)) return;

  try {
    const response = await fetch(apiUrl(`/api/scripts/${normalizedId}`), {
      method: 'DELETE'
    });
    const result = await response.json();
    if (result.success) {
      scripts = scripts.filter((script) => script.id !== normalizedId);
      render();
    }
  } catch (e) {
    console.error('Failed to delete script:', e);
  }
};

window.openProjectFromScript = async function (projectId) {
  const normalizedProjectId = decodeInlineArg(projectId).trim();
  if (!normalizedProjectId) {
    alert(getScriptManagementUiText().noLinkedProject);
    return;
  }
  if (typeof window.handleProjectSelect !== 'function') {
    console.error('Project loading failed: handler missing', normalizedProjectId);
    alert(getScriptManagementUiText().handlerMissing);
    return;
  }

  try {
    const didOpen = await window.handleProjectSelect(normalizedProjectId);
    if (!didOpen) {
      alert(getScriptManagementUiText().projectNotFound);
    }
  } catch (error) {
    console.error('Failed to open linked project:', error);
    alert(getScriptManagementUiText().projectLoadFailed);
  }
};

// --- DRAG AND DROP HANDLERS ---
window.onDragScript = function (event, scriptId) {
  const normalizedId = decodeInlineArg(scriptId);
  event.dataTransfer.setData('scriptId', normalizedId);
  event.target.classList.add('dragging');
};

window.onDragOverColumn = function (event) {
  event.preventDefault();
  event.currentTarget.classList.add('drag-over');
};

window.onDropOnColumn = function (event, newStatus) {
  event.preventDefault();
  const column = event.currentTarget;
  column.classList.remove('drag-over');

  const scriptId = event.dataTransfer.getData('scriptId');
  if (scriptId) {
    window.updateScriptStatus(scriptId, newStatus);
  }

  document.querySelectorAll('.script-card.dragging').forEach((el) => el.classList.remove('dragging'));
};

// Helper to re-render (called from main.js)
function render() {
  const container = document.querySelector('.main-content');
  if (container && document.querySelector('.script-pipeline-page')) {
    container.innerHTML = renderScriptManagementPage();
  }
}

// Load scripts on initial render
export function initScriptManagement() {
  window.loadScripts();
}

