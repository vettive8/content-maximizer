export function renderPlaceholderPage(pageName) {
    const formattedName = pageName
        .split('-')
        .map(word => word.charAt(0).toUpperCase() + word.slice(1))
        .join(' ');

    return `
    <div class="placeholder-page">
      <div class="placeholder-content">
        <div class="placeholder-icon">
          <svg width="64" height="64" viewBox="0 0 24 24" fill="none">
            <rect x="3" y="3" width="18" height="18" rx="2" stroke="currentColor" stroke-width="2"/>
            <path d="M3 9H21" stroke="currentColor" stroke-width="2"/>
            <path d="M9 21V9" stroke="currentColor" stroke-width="2"/>
          </svg>
        </div>
        <h2>${formattedName}</h2>
        <p>This feature is coming soon. Stay tuned for updates!</p>
        <div class="placeholder-badge">In Development</div>
      </div>
    </div>
  `;
}
