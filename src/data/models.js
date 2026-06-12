export const geminiModels = [
  {
    id: 'gemini-3.5-flash',
    name: 'Gemini 3.5 Flash',
    description: 'Stable, fast frontier model for production content workflows and long-running agentic tasks.',
    updated: 'May 2026',
    knowledgeCutoff: 'January 2025',
    cost: 2,
    status: 'recommended'
  },
  {
    id: 'gemini-3.1-flash-lite',
    name: 'Gemini 3.1 Flash-Lite',
    description: 'Stable low-latency, cost-efficient model for high-volume lightweight generation tasks.',
    updated: 'May 2026',
    knowledgeCutoff: 'January 2025',
    cost: 1,
    status: 'efficient'
  },
  {
    id: 'gemini-3.1-pro-preview',
    name: 'Gemini 3.1 Pro Preview',
    description: 'Advanced reasoning and multimodal capability for complex strategy and architecture tasks.',
    updated: 'February 2026',
    knowledgeCutoff: 'January 2025',
    cost: 4,
    status: 'advanced'
  },
  {
    id: 'gemini-3-flash-preview',
    name: 'Gemini 3 Flash Preview',
    description: 'Preview model kept as an optional compatibility choice for existing local configs.',
    updated: 'Preview',
    knowledgeCutoff: 'January 2025',
    cost: 2,
    status: 'preview'
  }
];

export const supportedModelIds = geminiModels.map((model) => model.id);

export function isSupportedModel(modelId) {
  return supportedModelIds.includes(modelId);
}

export function getCostDisplay(cost) {
  return '$'.repeat(cost);
}

export function getCostClass(cost) {
  if (cost >= 4) return 'cost-high';
  if (cost >= 2) return 'cost-medium';
  return 'cost-low';
}

export function getStatusBadge(status, language = 'en') {
  const isPolish = language === 'pl';
  const labels = {
    recommended: isPolish ? 'Polecany' : 'Recommended',
    efficient: isPolish ? 'Oszczedny' : 'Efficient',
    advanced: isPolish ? 'Zaawansowany' : 'Advanced',
    preview: isPolish ? 'Preview' : 'Preview'
  };

  switch (status) {
    case 'recommended':
      return `<span class="badge badge-recommended">${labels.recommended}</span>`;
    case 'efficient':
      return `<span class="badge badge-efficient">${labels.efficient}</span>`;
    case 'advanced':
      return `<span class="badge badge-advanced">${labels.advanced}</span>`;
    case 'preview':
      return `<span class="badge badge-preview">${labels.preview}</span>`;
    default:
      return '';
  }
}
