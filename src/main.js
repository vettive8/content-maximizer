import './styles/global.css';
import './pages/Placeholder.css';
import { renderSidebar, initSidebarEvents } from './components/Sidebar.js';
import { renderAIEnginePage, initAIEngineEvents } from './pages/AIEngine.js';
import { renderContentMaximizerPage, initContentMaximizerEvents } from './pages/ContentMaximizer.js';
import { renderBusinessGrowthStrategyPage, initBusinessGrowthStrategyEvents } from './pages/BusinessGrowthStrategy.js';
import { renderScriptManagementPage, initScriptManagement } from './pages/ScriptManagement.js';
import { renderSettingsPage, initSettingsEvents } from './pages/Settings.js';
import { renderPlaceholderPage } from './pages/Placeholder.js';
import { syncAIConfigToBackend } from './utils/storage.js';
import { initializeAppSettings } from './utils/settings.js';
import { apiUrl, installBackendFetchRewrite } from './utils/api.js';

const GROWTH_STRATEGY_PAGE = 'business-growth-strategy';
const LEGACY_GROWTH_STRATEGY_TYPE = ['game', 'plan'].join('-');

installBackendFetchRewrite();

// App State
let currentPage = 'content-maximizer';
let recentProjects = [];

// Global Job Manager
import { jobManager } from './utils/JobManager.js';
window.jobManager = jobManager;

// Router
function navigate(page) {
  currentPage = page;
  render();
}
window.setPage = navigate;

// Project Management
async function loadProjects() {
  try {
    const res = await fetch(apiUrl('/api/list_projects'));
    const data = await res.json();
    if (data.success) {
      recentProjects = data.projects;

      // OPTIMIZED: Only re-render sidebar if it exists, to avoid killing active main process
      const sidebarContainer = document.querySelector('.sidebar');
      if (sidebarContainer && document.querySelector('.main-content')) {
        // We are in a state where we just want to update the sidebar
        // Re-render the sidebar HTML string
        const newSidebarHTML = renderSidebar(currentPage, navigate, recentProjects);
        // Create a temp container to extract the new sidebar element
        const temp = document.createElement('div');
        temp.innerHTML = newSidebarHTML;
        const newSidebar = temp.firstElementChild;

        // Replace the old sidebar with the new one
        sidebarContainer.replaceWith(newSidebar);

        // Re-attach sidebar events
        initSidebarEvents(navigate, handleProjectSelect);
      } else {
        // First load or full render needed
        render();
      }
    }
  } catch (e) {
    console.error('Failed to load projects', e);
  }
}

async function handleProjectSelect(projectId) {
  const normalizedProjectId = String(projectId || '').trim();
  if (!normalizedProjectId) {
    return false;
  }

  try {
    const res = await fetch(apiUrl(`/api/get_project/${encodeURIComponent(normalizedProjectId)}`));
    if (!res.ok) {
      return false;
    }

    const data = await res.json();

    if (data.success && data.data) {
      const projectData = data.data;

      // Check project type to navigate to correct page
      if (projectData.type === GROWTH_STRATEGY_PAGE || projectData.type === LEGACY_GROWTH_STRATEGY_TYPE) {
        // Business Growth Strategy project - navigate to Business Growth Strategy page
        currentPage = GROWTH_STRATEGY_PAGE;
        render();
        if (window.loadBusinessGrowthStrategyData) {
          window.loadBusinessGrowthStrategyData(projectData);
        }
      } else {
        // Default: Content Maximizer project
        currentPage = 'content-maximizer';
        render();
        if (window.loadProjectData) {
          window.loadProjectData(projectData);
        }
      }
      return true;
    }

    return false;
  } catch (e) {
    console.error('Failed to load project', e);
    return false;
  }
}
window.handleProjectSelect = handleProjectSelect;

// Expose refresh function for ContentMaximizer to call after save
window.refreshProjects = loadProjects;

// Render App
function render() {
  const app = document.getElementById('app');

  let pageContent;
  switch (currentPage) {
    case 'content-maximizer':
      pageContent = renderContentMaximizerPage();
      break;
    case 'ai-engine':
      pageContent = renderAIEnginePage();
      break;
    case GROWTH_STRATEGY_PAGE:
      pageContent = renderBusinessGrowthStrategyPage();
      break;
    case 'script-management':
    case 'script-pipeline': // Legacy alias
      pageContent = renderScriptManagementPage();
      break;
    case 'settings':
      pageContent = renderSettingsPage();
      break;
    default:
      pageContent = renderPlaceholderPage(currentPage);
  }

  app.innerHTML = `
    ${renderSidebar(currentPage, navigate, recentProjects)}
    <main class="main-content">
      ${pageContent}
    </main>
  `;

  // Initialize event listeners
  initSidebarEvents(navigate, handleProjectSelect);

  switch (currentPage) {
    case 'content-maximizer':
      initContentMaximizerEvents();
      break;
    case 'ai-engine':
      initAIEngineEvents();
      break;
    case GROWTH_STRATEGY_PAGE:
      initBusinessGrowthStrategyEvents();
      break;
    case 'script-management':
    case 'script-pipeline': // Legacy alias
      initScriptManagement();
      break;
    case 'settings':
      initSettingsEvents();
      break;
  }
}

if (!window.__settingsRerenderBound) {
  window.addEventListener('app-settings-changed', () => {
    render();
  });
  window.__settingsRerenderBound = true;
}

function bootstrapApp() {
  if (window.__appBootstrapped) {
    return;
  }
  window.__appBootstrapped = true;

  initializeAppSettings();
  syncAIConfigToBackend().catch((error) => {
    console.warn('Failed to sync AI config on startup:', error);
  });
  loadProjects(); // Fetch projects first
  render();
}

// Initialize app exactly once.
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', bootstrapApp, { once: true });
} else {
  bootstrapApp();
}


