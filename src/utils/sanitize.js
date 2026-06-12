const HTML_ESCAPE_MAP = {
  '&': '&amp;',
  '<': '&lt;',
  '>': '&gt;',
  '"': '&quot;',
  "'": '&#39;',
  '`': '&#96;',
};

const HTML_ENTITY_MAP = {
  amp: '&',
  lt: '<',
  gt: '>',
  quot: '"',
  apos: "'",
  nbsp: ' ',
};

export function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>"'`]/g, (char) => HTML_ESCAPE_MAP[char]);
}

export function decodeHtmlEntities(value) {
  return String(value ?? '').replace(/&(#x?[0-9a-fA-F]+|[a-zA-Z]+);/g, (match, token) => {
    if (!token) return match;

    if (token[0] === '#') {
      const isHex = token[1]?.toLowerCase() === 'x';
      const raw = isHex ? token.slice(2) : token.slice(1);
      const parsed = Number.parseInt(raw, isHex ? 16 : 10);
      if (!Number.isFinite(parsed) || parsed <= 0 || parsed > 0x10ffff) {
        return match;
      }
      try {
        return String.fromCodePoint(parsed);
      } catch {
        return match;
      }
    }

    const key = token.toLowerCase();
    return Object.prototype.hasOwnProperty.call(HTML_ENTITY_MAP, key)
      ? HTML_ENTITY_MAP[key]
      : match;
  });
}

export function escapeAttribute(value) {
  return escapeHtml(value);
}

export function encodeInlineArg(value) {
  return encodeURIComponent(String(value ?? ''));
}

export function sanitizeDeep(input) {
  if (Array.isArray(input)) {
    return input.map((item) => sanitizeDeep(item));
  }

  if (input && typeof input === 'object') {
    const out = {};
    Object.entries(input).forEach(([key, value]) => {
      out[key] = sanitizeDeep(value);
    });
    return out;
  }

  if (typeof input === 'string') {
    return escapeHtml(decodeHtmlEntities(input));
  }

  return input;
}
