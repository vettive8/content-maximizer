import './Sidebar.css';
import { escapeAttribute, escapeHtml } from '../utils/sanitize.js';
import { getAppLanguage, t } from '../utils/settings.js';
import { apiUrl } from '../utils/api.js';

const navItems = [
  { id: 'content-maximizer', icon: '&#x1F3AC;', labelKey: 'sidebar_content_maximizer' },
  { id: 'business-growth-strategy', icon: '&#x1F3AF;', labelKey: 'sidebar_growth_strategy' },
  { id: 'script-management', icon: '&#x1F4DD;', labelKey: 'sidebar_script_pipeline' }
];

function normalizeProjectTitle(rawTitle, projectType) {
  let title = String(rawTitle || '').trim();

  if (!title) {
    return title;
  }

  title = title
    .replace(/^MT\s*-\s*/i, 'CM - ')
    .replace(/^SWB\s*-\s*/i, 'BGS - ')
    .replace(/^GM\s*-\s*/i, 'BGS - ')
    .replace(/^Game Plan\s*-\s*/i, 'BGS - ')
    .replace(/^Strategia Wzrostu Biznesu\s*-\s*/i, 'BGS - ')
    .replace(/^Content Maximizer\s*-\s*/i, 'CM - ')
    .replace(/^Content Maximizer\s*-\s*/i, 'Maksymalizator Treści - ');

  title = title
    .replace(/^Maksymalizator Tresci\s*-\s*/i, 'CM - ')
    .replace(/^Maksymalizator Tre\u0139\u203Aci\s*-\s*/i, 'CM - ')
    .replace(/^Maksymalizator Tre\u015Bci\s*-\s*/i, 'CM - ');

  title = title
    .replace(/\bGame Plan\b/gi, 'Business Growth Strategy')
    .replace(/\bStrategia Wzrostu Biznesu\b/gi, 'Business Growth Strategy')
    .replace(/\bContent Maximizer\b/gi, 'Maksymalizator Treści');

  title = title
    .replace(/\bMaksymalizator Tresci\b/gi, 'Content Maximizer')
    .replace(/\bMaksymalizator Tre\u0139\u203Aci\b/gi, 'Content Maximizer')
    .replace(/\bMaksymalizator Tre\u015Bci\b/gi, 'Content Maximizer');

  if (/^(business-growth-strategy|game-plan)$/i.test(String(projectType || '')) && !/^BGS\s*-/i.test(title)) {
    title = `BGS - ${title}`;
  }
  if (/^content-maximizer$/i.test(String(projectType || '')) && !/^CM\s*-/i.test(title)) {
    title = `CM - ${title}`;
  }

  return title;
}

function formatProjectTimestamp(createdAt) {
  const date = new Date(createdAt || '');
  if (Number.isNaN(date.getTime())) {
    return '-';
  }
  const locale = getAppLanguage() === 'pl' ? 'pl-PL' : 'en-US';
  const day = date.toLocaleDateString(locale);
  const time = date.toLocaleTimeString(locale, { hour: '2-digit', minute: '2-digit' });
  return `${day} ${time}`;
}

export function renderSidebar(activePage, onNavigate, recentProjects = []) {
  const safeProjects = (recentProjects || []).map((project) => ({
    ...project,
    id: escapeAttribute(project?.id || ''),
    title: escapeHtml(normalizeProjectTitle(project?.title, project?.type) || 'Untitled Project')
  }));

  return `
    <aside class="sidebar">
      <div class="sidebar-header">
        <span class="sidebar-logo">Marketing Engine OS</span>
      </div>

      <nav class="sidebar-nav">
        ${navItems.map(item => `
          <button
            class="nav-item ${(activePage === item.id || (item.id === 'script-management' && activePage === 'script-pipeline')) ? 'active' : ''}"
            data-page="${item.id}"
          >
            <span class="nav-icon">${item.icon}</span>
            <span class="nav-label">${t(item.labelKey, item.id)}</span>
          </button>
        `).join('')}
      </nav>

      <div class="recent-projects-section" style="padding: 20px; flex: 1; overflow-y: auto;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
          <h4 style="font-size: 0.75rem; text-transform: uppercase; color: var(--text-muted); letter-spacing: 0.05em; margin: 0;">${t('sidebar_project_history', 'Project History')}</h4>
          ${recentProjects && recentProjects.length > 0
      ? `<button id="btn-clear-history" style="background: none; border: none; color: var(--text-muted); font-size: 0.7rem; cursor: pointer; padding: 2px 6px; border-radius: 4px;">${t('sidebar_clear_all', 'Clear All')}</button>`
      : ''}
        </div>

        <div class="projects-list">
          ${safeProjects && safeProjects.length > 0 ? safeProjects.map(p => `
            <div class="project-item" data-id="${p.id}" style="padding: 8px 0; cursor: pointer; border-bottom: 1px solid var(--border-color); display: flex; justify-content: space-between; align-items: center; group;">
              <div style="flex: 1; min-width: 0; margin-right: 8px;">
                <div style="font-size: 0.85rem; font-weight: 500; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" title="${p.title}">${p.title}</div>
                <div style="font-size: 0.75rem; color: var(--text-muted);">${formatProjectTimestamp(p.created_at)}</div>
              </div>
              <button class="btn-delete-project" data-id="${p.id}" style="background: none; border: none; color: var(--text-muted); cursor: pointer; opacity: 0.5; padding: 4px; transition: opacity 0.2s;" title="${t('sidebar_delete_project', 'Delete Project')}">
                &#x1F5D1;&#xFE0F;
              </button>
            </div>
          `).join('') : `<div style="font-size: 0.8rem; color: var(--text-muted);">${t('sidebar_no_history', 'No history yet')}</div>`}
        </div>
      </div>

      <div class="sidebar-footer">
        <button class="nav-item ai-engine ${activePage === 'ai-engine' ? 'active' : ''}" data-page="ai-engine">
          <span class="nav-icon ai-icon">&#9881;</span>
          <div class="nav-content">
            <span class="nav-label">${t('sidebar_ai_engine', 'AI Engine')}</span>
            <span class="nav-sublabel">${t('sidebar_model_key', 'Model & Key')}</span>
          </div>
        </button>

        <div class="user-section">
          <div class="user-avatar"></div>
          <div class="user-info">
            <span class="user-name">${t('sidebar_user', 'User')}</span>
            <span class="user-plan">${t('sidebar_free_plan', 'Free Plan')}</span>
          </div>
          <button class="settings-btn ${activePage === 'settings' ? 'active' : ''}" title="${t('sidebar_settings', 'Settings')}" aria-label="${t('sidebar_settings', 'Settings')}">&#9881;</button>
        </div>
      </div>
    </aside>
  `;
}

export function initSidebarEvents(onNavigate, onProjectSelect) {
  document.querySelectorAll('.nav-item').forEach(item => {
    item.addEventListener('click', () => {
      const page = item.dataset.page;
      onNavigate(page);
    });
  });

  const settingsBtn = document.querySelector('.settings-btn');
  if (settingsBtn) {
    settingsBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      onNavigate('settings');
    });
  }

  document.querySelectorAll('.project-item').forEach(item => {
    item.addEventListener('click', (e) => {
      // Don't trigger if delete button was clicked
      if (e.target.closest('.btn-delete-project')) return;

      const projectId = item.dataset.id;
      if (onProjectSelect) onProjectSelect(projectId);
    });
  });

  // Delete Project Handlers
  document.querySelectorAll('.btn-delete-project').forEach(btn => {
    btn.addEventListener('click', async (e) => {
      e.stopPropagation(); // Prevent loading the project
      if (!confirm(t('sidebar_delete_confirm', 'Are you sure you want to delete this project?'))) return;

      const projectId = btn.dataset.id;
      try {
        const res = await fetch(apiUrl('/api/delete_project'), {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ project_id: projectId })
        });
        if (res.ok) {
          window.refreshProjects && window.refreshProjects();
        }
      } catch (err) {
        console.error('Failed to delete project', err);
      }
    });
  });

  // Clear History Handler
  const clearBtn = document.getElementById('btn-clear-history');
  if (clearBtn) {
    clearBtn.addEventListener('click', async (e) => {
      e.stopPropagation();
      if (!confirm(t('sidebar_clear_confirm', 'Are you sure you want to delete ALL project history? This cannot be undone.'))) return;

      try {
        const res = await fetch(apiUrl('/api/delete_all_projects'), {
          method: 'POST'
        });
        if (res.ok) {
          window.refreshProjects && window.refreshProjects();
        }
      } catch (err) {
        console.error('Failed to clear history', err);
      }
    });
  }
}


