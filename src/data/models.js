export const geminiModels = [
  {
    id: 'gemini-3-flash-preview',
    name: 'Gemini 3 Flash (Preview)',
    description: 'Fast, balanced model with strong reasoning for production workflows.',
    updated: 'April 2026',
    knowledgeCutoff: 'January 2025',
    cost: 2,
    status: 'recommended'
  },
  {
    id: 'gemini-3.1-flash-lite-preview',
    name: 'Gemini 3.1 Flash-Lite (Preview)',
    description: 'High-volume, cost-efficient model for everyday generation tasks.',
    updated: 'April 2026',
    knowledgeCutoff: 'January 2025',
    cost: 1,
    status: 'efficient'
  },
  {
    id: 'gemini-3.1-pro-preview',
    name: 'Gemini 3.1 Pro (Preview)',
    description: 'Top-tier reasoning and broad multimodal capability for complex tasks.',
    updated: 'April 2026',
    knowledgeCutoff: 'January 2025',
    cost: 4,
    status: 'advanced'
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
    advanced: isPolish ? 'Zaawansowany' : 'Advanced'
  };

  switch (status) {
    case 'recommended':
      return `<span class="badge badge-recommended">${labels.recommended}</span>`;
    case 'efficient':
      return `<span class="badge badge-efficient">${labels.efficient}</span>`;
    case 'advanced':
      return `<span class="badge badge-advanced">${labels.advanced}</span>`;
    default:
      return '';
  }
}
