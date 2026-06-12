import './ContentMaximizer.css';
import { notifyContentMaximizerComplete, requestNotificationPermission } from '../utils/notifications.js';
import { decodeHtmlEntities, encodeInlineArg, escapeAttribute, escapeHtml, sanitizeDeep } from '../utils/sanitize.js';
import { syncAIConfigToBackend, withAIConfig } from '../utils/storage.js';
import { getAppLanguage, setAppLanguage } from '../utils/settings.js';
import { apiUrl } from '../utils/api.js';

// Segment categories with duration ranges
const segmentInfo = {
  'Micro Hooks': { type: 'shorts', range: '15-30s', minSec: 15, maxSec: 30 },
  'Viral Shorts': { type: 'shorts', range: '1:00-1:15', minSec: 60, maxSec: 75 },
  'Extended Shorts': { type: 'shorts', range: '1:50-2:00', minSec: 110, maxSec: 120 },
  'Golden Nuggets': { type: 'medium', range: '3:00-4:00', minSec: 180, maxSec: 240 },
  'Deep Dives': { type: 'long', range: '5:00-5:59', minSec: 300, maxSec: 359 },
  'Full Segments': { type: 'long', range: '10:00-10:59', minSec: 600, maxSec: 659 }
};

// Demo data for placeholders - one per category with proper durations
const demoClips = [
  {
    id: 1,
    title: 'Polska gospodarka 2026 - szybka prognoza',
    category: 'Micro Hooks',
    start_time: 0,
    end_time: 18,
    duration: 18,
    viral_score: 8,
    best_platform: 'Instagram',
    content: {
      yt_shorts: { title: 'Polska gospodarka 2026 - szybki skrót', description: 'Krótka prognoza dla właścicieli firm B2B.' },
      instagram: { caption: 'Co czeka polskie firmy w 2026? #biznes #ekonomia', hashtags: ['#biznes', '#ekonomia'] },
      tiktok: { caption: 'Prognoza 2026 w 20 sekund.', hashtags: ['#biznes', '#b2b'] },
      linkedin: { post: 'Skrócona analiza trendów gospodarczych na 2026 dla firm B2B.' },
      twitter: { tweet: 'Polska gospodarka 2026: najważniejsze sygnały dla firm B2B.' },
      facebook: { post: 'Jak przygotować firmę B2B na 2026? Oto szybkie podsumowanie.' },
      cta: 'Obserwuj po więcej analiz.'
    }
  },
  {
    id: 2,
    title: 'Inwestorzy B2B są ostrożniejsi - co to znaczy',
    category: 'Viral Shorts',
    start_time: 124,
    end_time: 189,
    duration: 65,
    viral_score: 9,
    best_platform: 'Tiktok',
    content: {
      yt_shorts: { title: 'Dlaczego rynek B2B zwalnia', description: 'Najważniejsze przyczyny ostrożności inwestorów.' },
      linkedin: { post: 'Firmy B2B opóźniają decyzje zakupowe. Jak skrócić cykl sprzedaży?' },
      instagram: { caption: 'B2B: ryzyko czy szansa w 2026?', hashtags: ['#b2b', '#sprzedaz'] },
      tiktok: { caption: 'Dlaczego leady odkładają decyzję?', hashtags: ['#b2b', '#marketing'] },
      cta: 'Zobacz pełny materiał.'
    }
  },
  {
    id: 3,
    title: 'Prognozy 2026: wzrost i wyzwania firm B2B',
    category: 'Extended Shorts',
    start_time: 310,
    end_time: 425,
    duration: 115,
    viral_score: 7,
    best_platform: 'YT Shorts',
    content: {
      yt_shorts: { title: 'Strategia wzrostu B2B na 2026', description: 'Co działa, a co traci skuteczność.' },
      linkedin: { post: 'Jak planować wzrost B2B przy rosnącej presji kosztów i konkurencji?' },
      cta: 'Obejrzyj pełne wideo.'
    }
  },
  {
    id: 4,
    title: '3-4 min: kluczowy insight dla zespołu B2B',
    category: 'Golden Nuggets',
    start_time: 420,
    end_time: 630,
    duration: 210,
    viral_score: 8,
    best_platform: 'LinkedIn',
    content: {
      yt_shorts: { title: 'Jedna rzecz, która odblokowuje sprzedaż B2B', description: 'Konkretna lekcja z pełnego odcinka.' },
      linkedin: { post: 'Największy przełom w sprzedaży B2B zwykle zaczyna się od jednego poprawionego nawyku operacyjnego.' },
      cta: 'Zapisz i wdroż w tym tygodniu.'
    }
  },
  {
    id: 5,
    title: 'Największe ryzyka gospodarcze dla B2B w 2026',
    category: 'Deep Dives',
    start_time: 480,
    end_time: 810,
    duration: 330,
    viral_score: 8,
    best_platform: 'LinkedIn',
    content: {
      yt_shorts: { title: 'Ryzyka gospodarcze 2026', description: 'Na co uważać, planując sprzedaż B2B.' },
      linkedin: { post: 'Jak zarządzać ryzykiem przy długich procesach zakupowych i wysokiej niepewności rynku?' },
      cta: 'Zapisz się na webinar.'
    }
  },
  {
    id: 6,
    title: 'Mapa tarcia firmy: jak odblokować wzrost',
    category: 'Full Segments',
    start_time: 300,
    end_time: 920,
    duration: 620,
    viral_score: 6,
    best_platform: 'X/Twitter',
    content: {
      yt_shorts: { title: 'Mapa tarcia procesów B2B', description: 'Jak szybciej domykać sprzedaż.' },
      linkedin: { post: 'Największe opóźnienia zwykle są między marketingiem, sprzedażą i delivery.' },
      twitter: { tweet: 'Mapa tarcia procesów B2B: 3 miejsca, gdzie najczęściej tracisz marżę.' },
      cta: 'Pobierz checklistę do audytu procesów.'
    }
  }
];

const categories = ['All', 'Micro Hooks', 'Viral Shorts', 'Extended Shorts', 'Golden Nuggets', 'Deep Dives', 'Full Segments'];

const demoTranscript = `[00:00] W ostatnich latach firmy B2B zaczęły prowadzić bardziej świadomy marketing.
[00:05] Konkurencja rośnie, a decyzje zakupowe trwają coraz dłużej.
[00:10] W tym materiale pokazuję trendy, które warto wdrożyć w 2026 roku.
[00:15] Zaczynamy od skrócenia cyklu sprzedaży i poprawy jakości leadów.`;

const demoBlogPost = {
  title: 'Trendy marketingu B2B na 2026: praktyczny przewodnik',
  intro: 'Rynek B2B przyspiesza, ale rosną też oczekiwania klientów i koszty pozyskania leadów. Ten przewodnik pokazuje, co wdrożyć najpierw.',
  sections: [
    { title: '1. Wideo jako główny nośnik zaufania', content: 'Autentyczny ekspert i konkretne przykłady zwiększają konwersję bardziej niż ogólne deklaracje.' }
  ]
};

let currentTab = 'video-clips';
let currentCategory = 'All';
let isProcessed = false;
let isProcessing = false;
let currentUrl = '';
const clipDownloadStates = {};
const clipDownloadPollers = {};

function getCmUiText() {
  const isPolish = getAppLanguage() === 'pl';
  if (isPolish) {
    return {
      heroLine1: 'Zamień podcasty YouTube w',
      heroLine2: 'Wysokowartościowe Pakiety Treści',
      heroSubtitle: 'Profesjonalna transkrypcja po polsku i angielsku. Generuj blogi, posty LinkedIn i wątki na X w kilka sekund.',
      heroBrand: 'Maksymalizator Treści',
      cardTitle: 'Maksymalizator Treści',
      cardDescription: 'Przekształć jedno wideo w shorty, klipy i wpisy blogowe automatycznie.',
      tabVideoClips: 'Klipy wideo',
      tabWrittenContent: 'Treści pisane (Blog, Social)',
      inputPlaceholder: 'Wklej URL YouTube...',
      inputUploadLabel: 'Lub wybierz plik MP4',
      inputOrLabel: 'lub',
      maximizeButton: 'Maksymalizuj treść',
      toastProjectLoaded: 'Projekt wczytany z historii',
      toastInvalidUrl: 'Wprowadź poprawny URL YouTube',
      toastInvalidInput: 'Wklej URL YouTube lub wybierz plik MP4',
      toastConnectFailed: 'Nie udało się połączyć',
      toastContentGenerated: 'Treść wygenerowana pomyślnie!',
      toastNothingToSave: 'Brak danych do zapisania.',
      toastSaveSuccess: 'Projekt zapisany.',
      toastSaveFailed: 'Nie udało się zapisać projektu.',
      toastSaveError: 'Wystąpił błąd podczas zapisu projektu.',
      toastGenerationErrorPrefix: 'Błąd generowania: ',
      toastErrorPrefix: 'Błąd: ',
      toastAnotherJobRunning: 'Inny workflow jest teraz uruchomiony. Poczekaj na jego zakończenie.',
      downloadPreparing: 'Przygotowanie pobierania...',
      downloadSourceVideo: 'Pobieranie źródła z YouTube...',
      downloadSlicing: 'Wycinanie klipu...',
      downloadFinalizing: 'Finalizowanie pliku...',
      downloadReady: 'Klip gotowy',
      downloadEtaLabel: 'Pozostało',
      downloadUnknownEta: 'Obliczanie...',
      bubbleFirstClipHint: 'Pierwszy klip dla tego filmu może trwać dłużej: pobieramy całe źródło.',
      bubbleNextClipsHint: 'Kolejne klipy z tego samego filmu zwykle pobierają się szybciej.',
      bubbleClipReady: 'Klip gotowy. Pobieranie zostało uruchomione.',
      bubbleClipFailedPrefix: 'Nie udało się pobrać klipu: ',
      bubbleClipCached: 'Ten klip jest już w cache, pobieranie będzie szybkie.',
      unknownError: 'Nieznany błąd',
      progressFetching: 'Pobieranie transkryptu z YouTube...',
      progressUploading: 'Transkrypcja przesłanego MP4...',
      progressAnalyzing: 'Analiza pod viralowe klipy...',
      progressInitializing: 'Inicjalizacja...',
      progressWritingBlog: 'Pisanie wpisu blogowego SEO...',
      progressDraftingSocial: 'Tworzenie postów social media...',
      progressProcessing: 'Przetwarzanie...',
      progressFetchingEta: '~70s',
      noClipsFound: 'Brak klipów dla tej kategorii',
      categoryAll: 'Wszystkie',
      categoryMicroHooks: 'Mikro Hooki',
      categoryViralShorts: 'Viral Shorty',
      categoryExtendedShorts: 'Rozszerzone Shorty',
      categoryGoldenNuggets: 'Złote Nuggety',
      categoryDeepDives: 'Deep Dive',
      categoryFullSegments: 'Pełne Segmenty',
      saveButtonSaving: 'Zapisywanie...',
      saveButtonSaved: 'Zapisano!',
      processedVideo: 'Przetworzone wideo',
      fullTranscript: 'Pełna transkrypcja',
      copy: 'Kopiuj',
      download: 'Pobierz',
      sourceLabel: 'Źródło',
      sourceYoutube: 'YouTube',
      sourceUpload: 'Plik MP4',
      sourceFileLabel: 'Plik',
      videoIdLabel: 'ID wideo',
      languageLabel: 'Język',
      autoLabel: '(auto)',
      linesLabel: 'Liczba linii',
      seoBlogPost: 'Wpis blogowy SEO',
      targetKeywords: 'Słowa kluczowe',
      socialMediaPosts: 'Posty social media',
      readyToPublish: 'Treści gotowe do publikacji z przypisanymi klipami',
      linkedInPost: 'Post LinkedIn',
      twitterThread: 'Wątek X/Twitter',
      facebookPost: 'Post Facebook',
      copyPost: 'Kopiuj post',
      copyTweet: 'Kopiuj tweet',
      tweetPrefix: 'WPIS',
      recommendedAttachment: 'Rekomendowany załącznik',
      bestClip: 'Najlepszy klip',
      downloadAttachment: 'Pobierz załącznik',
      titleLabel: 'Tytuł',
      descLabel: 'Opis',
      copyYtShortsPost: 'Kopiuj post YT Shorts',
      bestBadge: 'Najlepszy',
      untitledClip: 'Klip bez tytułu',
      downloadClip: 'Pobierz klip',
      omnichannelContent: 'TREŚĆ OMNICHANNEL',
      blogCopied: 'Wpis blogowy skopiowany do schowka',
      transcriptCopied: 'Transkrypcja skopiowana do schowka',
      copyFailed: 'Nie udało się skopiować',
      copiedButton: 'Skopiowano!',
      processingButton: 'Przetwarzanie...',
      downloadStarted: 'Pobieranie rozpoczęte',
      errorButton: 'Błąd',
      ytPlayerTitle: 'Odtwarzacz YouTube',
      uploadPlayerTitle: 'Odtwarzacz MP4'
    };
  }

  return {
    heroLine1: 'Turn YouTube Podcasts into',
    heroLine2: 'High-Value Content Packs',
    heroSubtitle: 'Professional transcription for English and Polish. Generate blogs, LinkedIn posts, and Twitter threads in seconds.',
    heroBrand: 'Content Maximizer',
    cardTitle: 'Content Maximizer',
    cardDescription: 'Turn one video into shorts, clips, and blog posts automatically.',
    tabVideoClips: 'Video Clips',
    tabWrittenContent: 'Written Content (Blog, Social)',
    inputPlaceholder: 'Paste YouTube URL...',
    inputUploadLabel: 'Or choose an MP4 file',
    inputOrLabel: 'or',
    maximizeButton: 'Maximize Content',
    toastProjectLoaded: 'Project loaded from history',
    toastInvalidUrl: 'Please enter a valid YouTube URL',
    toastInvalidInput: 'Paste a YouTube URL or choose an MP4 file',
    toastConnectFailed: 'Failed to connect',
    toastContentGenerated: 'Content generated successfully!',
    toastNothingToSave: 'Nothing to save yet.',
    toastSaveSuccess: 'Project saved.',
    toastSaveFailed: 'Failed to save project.',
    toastSaveError: 'Error saving project.',
    toastGenerationErrorPrefix: 'Generation Error: ',
    toastErrorPrefix: 'Error: ',
    toastAnotherJobRunning: 'Another workflow is already running. Please wait until it finishes.',
    downloadPreparing: 'Preparing download...',
    downloadSourceVideo: 'Downloading source video...',
    downloadSlicing: 'Slicing clip...',
    downloadFinalizing: 'Finalizing file...',
    downloadReady: 'Clip ready',
    downloadEtaLabel: 'Left',
    downloadUnknownEta: 'Calculating...',
    bubbleFirstClipHint: 'First clip for this video may take longer because we download the full source.',
    bubbleNextClipsHint: 'Next clips from the same video are usually faster.',
    bubbleClipReady: 'Clip is ready. Download started.',
    bubbleClipFailedPrefix: 'Failed to download clip: ',
    bubbleClipCached: 'This clip is already cached, download should be fast.',
    unknownError: 'Unknown error',
    progressFetching: 'Fetching transcript from YouTube...',
    progressUploading: 'Transcribing uploaded MP4...',
    progressAnalyzing: 'Analyzing for Viral Clips...',
    progressInitializing: 'Initializing...',
    progressWritingBlog: 'Writing SEO Blog Post...',
    progressDraftingSocial: 'Drafting Social Posts...',
    progressProcessing: 'Processing...',
    progressFetchingEta: '~70s',
    noClipsFound: 'No clips found for this category',
    categoryAll: 'All',
    categoryMicroHooks: 'Micro Hooks',
    categoryViralShorts: 'Viral Shorts',
    categoryExtendedShorts: 'Extended Shorts',
    categoryGoldenNuggets: 'Golden Nuggets',
    categoryDeepDives: 'Deep Dives',
    categoryFullSegments: 'Full Segments',
    saveButtonSaving: 'Saving...',
    saveButtonSaved: 'Saved!',
    processedVideo: 'Processed Video',
    fullTranscript: 'Full Transcript',
    copy: 'Copy',
    download: 'Download',
    sourceLabel: 'Source',
    sourceYoutube: 'YouTube',
    sourceUpload: 'MP4 File',
    sourceFileLabel: 'File',
    videoIdLabel: 'Video ID',
    languageLabel: 'Language',
    autoLabel: '(auto)',
    linesLabel: 'Lines',
    seoBlogPost: 'SEO Blog Post',
    targetKeywords: 'Target Keywords',
    socialMediaPosts: 'Social Media Posts',
    readyToPublish: 'Ready-to-publish content with attached viral clips',
    linkedInPost: 'LinkedIn Post',
    twitterThread: 'Twitter/X Thread',
    facebookPost: 'Facebook Post',
    copyPost: 'Copy Post',
    copyTweet: 'Copy Tweet',
    tweetPrefix: 'TWEET',
    recommendedAttachment: 'Recommended Attachment',
    bestClip: 'Best Clip',
    downloadAttachment: 'Download Attachment',
    titleLabel: 'Title',
    descLabel: 'Desc',
    copyYtShortsPost: 'Copy YT Shorts Post',
    bestBadge: 'Best',
    untitledClip: 'Untitled Clip',
    downloadClip: 'Download Clip',
    omnichannelContent: 'OMNICHANNEL CONTENT',
    blogCopied: 'Blog post copied to clipboard',
    transcriptCopied: 'Transcript copied to clipboard',
    copyFailed: 'Failed to copy',
    copiedButton: 'Copied!',
    processingButton: 'Processing...',
    downloadStarted: 'Download Started',
    errorButton: 'Error',
    ytPlayerTitle: 'YouTube video player',
    uploadPlayerTitle: 'MP4 video player'
  };
}

function localizeCmProgressMessage(stage, fallbackMessage) {
  const ui = getCmUiText();
  if (stage === 'init') return ui.progressInitializing;
  if (stage === 'clips') return ui.progressAnalyzing;
  if (stage === 'blog') return ui.progressWritingBlog;
  if (stage === 'social') return ui.progressDraftingSocial;
  return fallbackMessage || ui.progressProcessing;
}

function getContentMaximizerJobState() {
  const state = window.jobManager?.getState?.() || {};
  if (state.jobType && state.jobType !== 'content-maximizer') {
    return {
      isGenerating: false,
      progress: 0,
      stage: '',
      message: '',
      timeRemaining: '',
      result: null,
      error: null,
      jobType: state.jobType
    };
  }
  return state;
}

function localizeCmTimeRemaining(timeRemaining = '') {
  const raw = String(timeRemaining || '').trim();
  if (!raw) return '';
  if (getAppLanguage() !== 'pl') return raw;

  if (/calculating/i.test(raw)) return 'Obliczanie...';
  if (/almost done/i.test(raw)) return 'Prawie gotowe...';

  const minsMatch = raw.match(/~?\s*([\d.,]+)\s*mins?\s*left/i);
  if (minsMatch) {
    const value = minsMatch[1].replace('.', ',');
    return `~${value} min pozostalo`;
  }

  const secsMatch = raw.match(/~?\s*([\d.,]+)\s*secs?\s*left/i);
  if (secsMatch) {
    const value = secsMatch[1].replace('.', ',');
    return `~${value} s pozostalo`;
  }

  return raw
    .replace(/\bleft\b/gi, 'pozostalo')
    .replace(/\bmins?\b/gi, 'min')
    .replace(/\bsecs?\b/gi, 's');
}

function getCurrentSourceMeta() {
  const transcriptData = window.transcriptData || {};
  const sourceType = transcriptData.source_type === 'upload' ? 'upload' : 'youtube';
  const sourceId = String(
    transcriptData.source_id
    || transcriptData.video_id
    || 'lsuOUJQ-0iQ'
  );
  const encodedSourceId = encodeURIComponent(sourceId);
  const thumbnail = sourceType === 'youtube'
    ? `https://img.youtube.com/vi/${encodedSourceId}/hqdefault.jpg`
    : '';
  const mediaUrl = sourceType === 'upload'
    ? apiUrl(`/api/media/${encodedSourceId}`)
    : '';
  return { sourceType, sourceId, encodedSourceId, thumbnail, mediaUrl };
}

function getSourceTypeLabel(sourceType) {
  const ui = getCmUiText();
  return sourceType === 'upload' ? ui.sourceUpload : ui.sourceYoutube;
}

function buildClipDownloadKey(sourceType, sourceId, start, end) {
  const safeType = String(sourceType || 'youtube').replace(/[^a-zA-Z0-9_-]/g, '');
  const safeSourceId = String(sourceId || '').replace(/[^a-zA-Z0-9_-]/g, '');
  const startMs = Math.round(Number(start || 0) * 100);
  const endMs = Math.round(Number(end || 0) * 100);
  return `dl_${safeType}_${safeSourceId}_${startMs}_${endMs}`;
}

function formatEtaSeconds(seconds) {
  const ui = getCmUiText();
  if (!Number.isFinite(Number(seconds)) || Number(seconds) <= 0) {
    return ui.downloadUnknownEta;
  }
  const s = Math.max(0, Math.round(Number(seconds)));
  if (s < 60) {
    return getAppLanguage() === 'pl' ? `~${s}s` : `~${s}s`;
  }
  const mins = Math.floor(s / 60);
  const rem = s % 60;
  if (getAppLanguage() === 'pl') {
    return rem > 0 ? `~${mins}m ${rem}s` : `~${mins}m`;
  }
  return rem > 0 ? `~${mins}m ${rem}s` : `~${mins}m`;
}

function localizeDownloadStage(stage) {
  const ui = getCmUiText();
  if (stage === 'queued' || stage === 'preparing') return ui.downloadPreparing;
  if (stage === 'downloading_source') return ui.downloadSourceVideo;
  if (stage === 'slicing_clip') return ui.downloadSlicing;
  if (stage === 'finalizing') return ui.downloadFinalizing;
  if (stage === 'completed') return ui.downloadReady;
  return ui.downloadPreparing;
}

function showDownloadBubble(message, type = 'info') {
  const stackId = 'cm-download-bubble-stack';
  let stack = document.getElementById(stackId);
  if (!stack) {
    stack = document.createElement('div');
    stack.id = stackId;
    stack.className = 'download-bubble-stack';
    document.body.appendChild(stack);
  }

  const bubble = document.createElement('div');
  bubble.className = `download-bubble download-bubble-${type}`;
  bubble.textContent = message;
  stack.appendChild(bubble);

  requestAnimationFrame(() => bubble.classList.add('show'));
  setTimeout(() => {
    bubble.classList.remove('show');
    setTimeout(() => bubble.remove(), 250);
  }, 4800);
}

function getClipDownloadState(clipKey) {
  return clipDownloadStates[clipKey] || null;
}

function setClipDownloadState(clipKey, nextState) {
  clipDownloadStates[clipKey] = {
    ...(clipDownloadStates[clipKey] || {}),
    ...nextState
  };
}

function clearClipDownloadPoller(clipKey) {
  if (clipDownloadPollers[clipKey]) {
    clearInterval(clipDownloadPollers[clipKey]);
    delete clipDownloadPollers[clipKey];
  }
}

function triggerClipFileDownload(jobId) {
  const link = document.createElement('a');
  link.href = apiUrl(`/api/download_clip/file/${encodeURIComponent(jobId)}`);
  link.style.display = 'none';
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}

function renderDownloadControl(sourceType, sourceId, startTime, endTime, title, clipKey) {
  const ui = getCmUiText();
  const state = getClipDownloadState(clipKey);
  if (!state || state.status === 'idle') {
    return `
      <button class="btn btn-download"
        onclick="window.downloadClip('${sourceType}', decodeURIComponent('${encodeInlineArg(sourceId)}'), ${startTime}, ${endTime}, decodeURIComponent('${encodeInlineArg(title)}'), this)"
      >
        ${ui.downloadClip}
      </button>
    `;
  }

  if (state.status === 'error') {
    return `
      <button class="btn btn-download"
        onclick="window.downloadClip('${sourceType}', decodeURIComponent('${encodeInlineArg(sourceId)}'), ${startTime}, ${endTime}, decodeURIComponent('${encodeInlineArg(title)}'), this)"
      >
        ${ui.downloadClip}
      </button>
    `;
  }

  const progress = Math.max(2, Math.min(100, Math.round(Number(state.progressPercent || 0))));
  const stageLabel = escapeHtml(localizeDownloadStage(state.stage));
  const eta = escapeHtml(formatEtaSeconds(state.remainingSeconds));
  return `
    <div class="download-progress-inline" aria-live="polite">
      <div class="download-progress-row">
        <span class="download-progress-label">${stageLabel}</span>
        <span class="download-progress-eta">${ui.downloadEtaLabel}: ${eta}</span>
      </div>
      <div class="download-progress-track">
        <div class="download-progress-fill" style="width:${progress}%"></div>
      </div>
    </div>
  `;
}

function refreshDownloadControl(clipKey) {
  const selector = `.clip-download-container[data-download-key="${clipKey}"]`;
  document.querySelectorAll(selector).forEach((container) => {
    const sourceType = container.getAttribute('data-source-type') || 'youtube';
    const sourceId = container.getAttribute('data-source-id') || '';
    const start = Number(container.getAttribute('data-start') || 0);
    const end = Number(container.getAttribute('data-end') || start + 1);
    const title = decodeURIComponent(container.getAttribute('data-title') || '');
    container.innerHTML = renderDownloadControl(sourceType, sourceId, start, end, title, clipKey);
  });
}

async function pollClipDownloadStatus(clipKey, jobId) {
  clearClipDownloadPoller(clipKey);

  clipDownloadPollers[clipKey] = setInterval(async () => {
    try {
      const response = await fetch(apiUrl(`/api/download_clip/status/${encodeURIComponent(jobId)}`));
      const payload = await response.json();
      if (!response.ok || !payload.success) {
        throw new Error(payload.error || 'Failed to fetch download status');
      }

      setClipDownloadState(clipKey, {
        status: payload.status,
        stage: payload.stage,
        progressPercent: payload.progress_percent,
        remainingSeconds: payload.remaining_seconds,
        estimatedSeconds: payload.estimated_seconds,
      });
      refreshDownloadControl(clipKey);

      if (payload.status === 'completed') {
        clearClipDownloadPoller(clipKey);
        triggerClipFileDownload(jobId);
        showDownloadBubble(getCmUiText().bubbleClipReady, 'success');
        setTimeout(() => {
          setClipDownloadState(clipKey, { status: 'idle', progressPercent: 0, stage: '' });
          refreshDownloadControl(clipKey);
        }, 2600);
      } else if (payload.status === 'error') {
        clearClipDownloadPoller(clipKey);
        setClipDownloadState(clipKey, {
          status: 'error',
          stage: 'error',
          progressPercent: 0,
          remainingSeconds: 0,
        });
        refreshDownloadControl(clipKey);
        showDownloadBubble(`${getCmUiText().bubbleClipFailedPrefix}${payload.error || getCmUiText().unknownError}`, 'error');
      }
    } catch (error) {
      clearClipDownloadPoller(clipKey);
      setClipDownloadState(clipKey, {
        status: 'error',
        stage: 'error',
        progressPercent: 0,
        remainingSeconds: 0,
      });
      refreshDownloadControl(clipKey);
      showDownloadBubble(`${getCmUiText().bubbleClipFailedPrefix}${error.message}`, 'error');
    }
  }, 900);
}
export function renderContentMaximizerPage() {
  const ui = getCmUiText();
  const brandName = ui.heroBrand || ui.cardTitle || 'Content Maximizer';
  const progressState = getContentMaximizerJobState();
  return `
    <div class="content-maximizer-page">
      <header class="page-brand">
        <div class="brand-icon">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
            <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2"/>
            <circle cx="12" cy="12" r="4" fill="currentColor"/>
          </svg>
        </div>
        <span class="brand-name">${brandName}</span>
      </header>
      
      <section class="hero-section">
        <h1>${ui.heroLine1}<br><span class="text-gradient">${ui.heroLine2}</span></h1>
        <p class="hero-subtitle">${ui.heroSubtitle}</p>
      </section>
      
      <section class="maximizer-card">
        <div class="card-header-row">
          <div>
            <h2>${ui.cardTitle}</h2>
            <p>${ui.cardDescription}</p>
          </div>
        </div>
        
        <div class="maximizer-content-wrapper">
            <div id="cm-input-container" class="input-row" style="margin-bottom: 20px;">
                ${renderInputForm()}
            </div>
            <div id="cm-progress-container" style="display: ${progressState.isGenerating ? 'block' : 'none'}">
                ${renderProgressBar()}
            </div>
        </div>
      </section>
      
      ${isProcessed ? renderResultsTabs() : ''}
    </div>
  `;
}

function renderResultsTabs() {
  const ui = getCmUiText();
  return `
    <section class="results-section">
      <div class="tabs-header">
        <div class="tabs">
          <button class="tab ${currentTab === 'video-clips' ? 'active' : ''}" data-tab="video-clips">
            ${ui.tabVideoClips}
          </button>
          <button class="tab ${currentTab === 'written-content' ? 'active' : ''}" data-tab="written-content">
            ${ui.tabWrittenContent}
          </button>
        </div>
      </div>
      
      ${currentTab === 'video-clips' ? renderVideoClipsTab() : renderWrittenContentTab()}
    </section>
  `;
}

// Global function to load project data (called from main.js)
window.loadProjectData = function (data) {
  if (!data) return;
  window.transcriptData = data.transcriptData;
  window.contentData = data.contentData;
  isProcessed = true;

  // Re-render
  const page = document.querySelector('.content-maximizer-page');
  if (page) {
    page.outerHTML = renderContentMaximizerPage();
    initContentMaximizerEvents();
    initResultsEvents();
  }
  showToast(getCmUiText().toastProjectLoaded, 'success');
};

// Modified save to support silent mode
async function saveCurrentProject(silent = false) {
  const ui = getCmUiText();
  if (!window.transcriptData || !window.contentData) {
    if (!silent) showToast(ui.toastNothingToSave, 'warning');
    return;
  }

  const btn = document.getElementById('btn-save-project');
  const originalText = btn ? btn.innerHTML : '';

  if (!silent && btn) {
    btn.innerHTML = ui.saveButtonSaving;
    btn.disabled = true;
  }

  try {
    const dateStr = new Date().toLocaleDateString('pl-PL').replace(/\./g, '-');
    const videoTitle = window.transcriptData.title || (window.contentData.blog?.title || window.contentData.clips?.[0]?.title || 'Untitled_Video').substring(0, 30);
    const projectTitle = `CM - ${videoTitle} - ${dateStr}`;

    const payload = {
      type: 'content-maximizer', // Differentiates from business-growth-strategy
      video_id: window.transcriptData.video_id,
      title: projectTitle,
      transcriptData: window.transcriptData,
      contentData: window.contentData,
      updated_at: new Date().toISOString()
    };

    // Add project_id if it exists in window
    if (window.currentProjectId) {
      payload.id = window.currentProjectId;
    }

    const res = await fetch(apiUrl('/api/save_project'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    const result = await res.json();

    if (result.success) {
      // Refresh sidebar project list
      if (window.refreshProjects) window.refreshProjects();

      if (!silent) {
        showToast(ui.toastSaveSuccess, 'success');
      }
      // Store ID to update same project next time
      window.currentProjectId = result.project_id;
    } else {
      if (!silent) showToast(ui.toastSaveFailed, 'error');
    }
  } catch (e) {
    console.error(e);
    if (!silent) showToast(ui.toastSaveError, 'error');
  } finally {
    if (!silent && btn) {
      btn.innerHTML = ui.saveButtonSaved;
      setTimeout(() => {
        btn.innerHTML = originalText;
        btn.disabled = false;
      }, 2000);
    }
  }
}

function renderVideoClipsTab() {
  // Use AI-generated clips if available, otherwise fall back to demo
  const aiClips = window.contentData?.clips || [];
  const allClips = sanitizeDeep(aiClips.length > 0 ? aiClips : demoClips);

  const filteredClips = currentCategory === 'All'
    ? allClips
    : allClips.filter(c => c.category === currentCategory);

  return `
    <div class="video-clips-tab">
      <div class="category-filters">
        ${categories.map(cat => `
          <button class="filter-btn ${currentCategory === cat ? 'active' : ''}" data-category="${cat}">
            ${cat}
          </button>
        `).join('')}
      </div>
      
      <div class="clips-grid">
        ${filteredClips.length > 0
      ? filteredClips.map(clip => renderClipCard(clip)).join('')
      : `<p class="no-clips">${getCmUiText().noClipsFound}</p>`
    }
      </div>
    </div>
  `;
}

function getTranscriptMaxDuration() {
  const segments = window.transcriptData?.segments;
  if (!Array.isArray(segments) || segments.length === 0) {
    return null;
  }

  let maxEnd = 0;
  segments.forEach((segment) => {
    if (!segment || typeof segment !== 'object') return;
    const start = Number(segment.start);
    const duration = Number(segment.duration);
    const end = Number.isFinite(Number(segment.end))
      ? Number(segment.end)
      : (Number.isFinite(start) && Number.isFinite(duration) ? start + duration : NaN);
    if (Number.isFinite(end) && end > maxEnd) {
      maxEnd = end;
    }
  });

  return maxEnd > 0 ? maxEnd : null;
}

function normalizeClipWindow(startRaw, endRaw, maxDuration) {
  const startCandidate = Number(startRaw);
  const endCandidate = Number(endRaw);
  const startBase = Number.isFinite(startCandidate) ? startCandidate : 0;
  const endBase = Number.isFinite(endCandidate) ? endCandidate : startBase + 1;

  if (!Number.isFinite(maxDuration) || maxDuration === null || maxDuration <= 0) {
    const safeStart = Math.max(0, startBase);
    const safeEnd = Math.max(safeStart + 1, endBase);
    return { start: safeStart, end: safeEnd };
  }

  const total = maxDuration;
  const desiredDuration = Math.max(1, endBase - startBase);
  let start = Math.max(0, startBase);
  let end = start + desiredDuration;

  if (end > total) {
    end = total;
    start = Math.max(0, end - desiredDuration);
  }

  if (end - start < 1) {
    start = Math.max(0, total - 1);
    end = total;
  }

  if (start >= total) {
    start = Math.max(0, total - 1);
    end = total;
  }

  return { start, end };
}

function renderClipCard(clip) {
  const ui = getCmUiText();
  const sourceMeta = getCurrentSourceMeta();
  const thumbnailStyle = sourceMeta.sourceType === 'youtube'
    ? `background-image: url('${sourceMeta.thumbnail}');`
    : '';

  // Format times
  const rawStart = clip.start_time ?? clip.start ?? 0;
  const rawEnd = clip.end_time ?? (Number(rawStart) + (clip.duration || 60));
  const transcriptDuration = getTranscriptMaxDuration();
  const normalizedWindow = normalizeClipWindow(rawStart, rawEnd, transcriptDuration);
  const startTime = normalizedWindow.start;
  const endTime = normalizedWindow.end;
  const duration = endTime - startTime;
  const timeRange = `${formatTime(startTime)} - ${formatTime(endTime)}`;
  const clipTitle = clip.title || ui.untitledClip;
  const clipKey = buildClipDownloadKey(sourceMeta.sourceType, sourceMeta.sourceId, startTime, endTime);

  // Omnichannel Content logic
  const platformOrder = ['yt_shorts', 'instagram', 'tiktok', 'linkedin', 'twitter', 'facebook', 'cta'];

  const platformHtml = platformOrder.map(p => {
    const key = p.toLowerCase();
    const data = clip.content?.[key];

    const bestPlatform = clip.best_platform?.toLowerCase();
    const isBest = bestPlatform === key ||
      (key === 'yt_shorts' && bestPlatform === 'yt shorts') ||
      (key === 'twitter' && bestPlatform === 'x/twitter');

    // Labeling
    let label = p.charAt(0).toUpperCase() + p.slice(1);
    if (key === 'yt_shorts') label = 'YT Shorts';
    if (key === 'twitter') label = 'X/Twitter';
    if (key === 'cta') label = 'CTA';

    if (!data && !isBest) return '';

    let contentHtml = '';

    if (key === 'yt_shorts') {
      const ytCopyText = `${data?.title || ''} ${data?.description || ''}`.trim();
      contentHtml = `
        <div class="field-group">
          <span class="field-label">${ui.titleLabel}:</span> <span class="field-value">${data?.title || ''}</span>
        </div>
        <div class="field-group">
          <span class="field-label">${ui.descLabel}:</span> <div class="field-value">${data?.description || ''}</div>
        </div>
        <button class="btn-copy-post" onclick="window.copyToClipboard(this, decodeURIComponent('${encodeInlineArg(ytCopyText)}'))">${ui.copyYtShortsPost}</button>
      `;
    } else if (key === 'cta') {
      contentHtml = `<div class="field-value">${typeof data === 'string' ? data : (data?.text || '')}</div>`;
    } else {
      // Generic for social posts
      const text = data?.post || data?.caption || data?.tweet || (typeof data === 'string' ? data : '');
      const encodedText = encodeInlineArg(text);

      contentHtml = `<div class="field-value">${text}</div>`;
      if (data?.hashtags && Array.isArray(data.hashtags)) {
        contentHtml += `<div class="hashtags">${data.hashtags.join(' ')}</div>`;
      }
      contentHtml += `<button class="btn-copy-post" onclick="window.copyToClipboard(this, decodeURIComponent('${encodedText}'))">${ui.copy} ${label}</button>`;
    }

    return `
      <div class="platform-row" data-platform="${key}">
        <div class="row-header">
          <span class="platform-name">${label}</span>
          ${isBest ? `<span class="best-badge">${ui.bestBadge}</span>` : ''}
          <span class="expand-icon">&#9662;</span>
        </div>
        <div class="row-content" style="display:none">
          <div class="platform-content-body">
            ${contentHtml}
          </div>
        </div>
      </div>
    `;
  }).join('');

  return `
    <div class="clip-card" id="clip-${clip.id}">
      <div class="clip-header">
        <h3 class="clip-title">${clipTitle}</h3>
        <div class="clip-badges">
          <span class="clip-category">${clip.category}</span>
        </div>
      </div>
      
      <div class="clip-thumbnail" style="${thumbnailStyle}" onclick="window.playClip(this, '${sourceMeta.sourceType}', decodeURIComponent('${encodeInlineArg(sourceMeta.sourceId)}'), ${startTime}, ${endTime})">
        <div class="video-overlay"></div>
        <div class="video-controls">
          <span class="play-icon">&#9654;</span>
          <span class="time-display">${formatTime(0)} / ${formatTime(duration)}</span>
          <span class="control-icons">VOL | CC | ...</span>
        </div>
      </div>
      
      <div class="clip-time-range">${timeRange}</div>

      <div
        class="clip-download-container"
        data-download-key="${clipKey}"
        data-source-type="${sourceMeta.sourceType}"
        data-source-id="${escapeAttribute(sourceMeta.sourceId)}"
        data-start="${startTime}"
        data-end="${endTime}"
        data-title="${encodeInlineArg(clipTitle)}"
      >
        ${renderDownloadControl(sourceMeta.sourceType, sourceMeta.sourceId, startTime, endTime, clipTitle, clipKey)}
      </div>
      
      <div class="omnichannel-section">
        <div class="omnichannel-header">${ui.omnichannelContent}</div>
        <div class="platforms-accordion">
          ${platformHtml}
        </div>
      </div>
    </div>
  `;
}

// Helper function to format seconds to MM:SS or HH:MM:SS
function formatTime(seconds) {
  const secs = Math.floor(seconds);
  const h = Math.floor(secs / 3600);
  const m = Math.floor((secs % 3600) / 60);
  const s = secs % 60;
  if (h > 0) {
    return `${h}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  }
  return `${m}:${s.toString().padStart(2, '0')}`;
}


function renderWrittenContentTab() {
  const ui = getCmUiText();
  // Get AI-generated content or fall back to demo
  const aiClips = sanitizeDeep(window.contentData?.clips || []);
  const aiBlog = sanitizeDeep(window.contentData?.blog);
  const aiSocial = sanitizeDeep(window.contentData?.social);
  const sourceMeta = getCurrentSourceMeta();
  const clipThumbnailStyle = sourceMeta.sourceType === 'youtube'
    ? `background-image: url('${sourceMeta.thumbnail}'); height: 180px;`
    : 'height: 180px;';

  // Helper to find best clip for a platform
  const getClipForPlatform = (platform) => {
    if (aiClips.length > 0) {
      return aiClips.find(c => c.best_platform?.toLowerCase() === platform.toLowerCase()) || aiClips[0];
    }
    return demoClips[0];
  };

  const linkedinClip = getClipForPlatform('linkedin');
  const twitterClip = getClipForPlatform('twitter');
  const facebookClip = getClipForPlatform('facebook');
  const transcriptDuration = getTranscriptMaxDuration();
  const linkedinWindow = normalizeClipWindow(
    linkedinClip.start_time ?? linkedinClip.start ?? 0,
    linkedinClip.end_time ?? linkedinClip.end ?? ((linkedinClip.start_time ?? linkedinClip.start ?? 0) + 60),
    transcriptDuration
  );
  const twitterWindow = normalizeClipWindow(
    twitterClip.start_time ?? twitterClip.start ?? 0,
    twitterClip.end_time ?? twitterClip.end ?? ((twitterClip.start_time ?? twitterClip.start ?? 0) + 60),
    transcriptDuration
  );
  const facebookWindow = normalizeClipWindow(
    facebookClip.start_time ?? facebookClip.start ?? 0,
    facebookClip.end_time ?? facebookClip.end ?? ((facebookClip.start_time ?? facebookClip.start ?? 0) + 60),
    transcriptDuration
  );
  const linkedinTitle = linkedinClip.title || 'linkedin_clip';
  const twitterTitle = twitterClip.title || 'twitter_clip';
  const facebookTitle = facebookClip.title || 'facebook_clip';
  const linkedinKey = buildClipDownloadKey(sourceMeta.sourceType, sourceMeta.sourceId, linkedinWindow.start, linkedinWindow.end);
  const twitterKey = buildClipDownloadKey(sourceMeta.sourceType, sourceMeta.sourceId, twitterWindow.start, twitterWindow.end);
  const facebookKey = buildClipDownloadKey(sourceMeta.sourceType, sourceMeta.sourceId, facebookWindow.start, facebookWindow.end);

  // Use AI blog or demo
  const blog = aiBlog || demoBlogPost;

  // Use AI social posts or demo
  const linkedinContent = aiSocial?.linkedin?.content || '';
  const twitterThread = aiSocial?.twitter?.tweets || [];
  const facebookContent = aiSocial?.facebook?.content || '';

  // Render Blog Sections
  const renderBlogSections = () => {
    if (!blog.sections || !Array.isArray(blog.sections)) return '';
    return blog.sections.map(section => `
      <div class="blog-section-content">
        <h2>${section.title}</h2>
        <div>${window.marked && window.marked.parse ? window.marked.parse(escapeHtml(section.content || '')) : escapeHtml(section.content || '')}</div>
      </div>
    `).join('');
  };

  // Note: We need marked.js for markdown rendering. If not available, we'll just dump text.
  // Assuming marked is available or we use simple text replacement for now.
  // Actually, let's use a simple formatter if marked isn't loaded.
  const formatContent = (text) => {
    const safeText = escapeHtml(decodeHtmlEntities(text || ''));
    if (window.marked && window.marked.parse) return window.marked.parse(safeText);
    return safeText.replace(/\n/g, '<br>').replace(/## (.*)/g, '<h3>$1</h3>').replace(/\*\*(.*)\*\*/g, '<b>$1</b>');
  };

  return `
    <div class="written-content-tab">
      <!-- Row 1: Transcript + Blog -->
      <div class="content-columns">
        <div class="transcript-section">
          <div class="section-header">
            <div>
              <h3>${ui.processedVideo}</h3>
              <span class="section-subtitle">${ui.fullTranscript}</span>
            </div>
            <div class="export-buttons">
              <button class="btn btn-export" onclick="window.exportTranscript('copy', this)">${ui.copy}</button>
              <button class="btn btn-export" onclick="window.exportTranscript('txt', this)">TXT</button>
              <button class="btn btn-export" onclick="window.exportTranscript('srt', this)">SRT</button>
              <button class="btn btn-export" onclick="window.exportTranscript('vtt', this)">VTT</button>
              <button class="btn btn-export" onclick="window.exportTranscript('json', this)">JSON</button>
            </div>
          </div>
          <div class="transcript-content">
            <pre>${escapeHtml(window.transcriptData?.transcript || demoTranscript)}</pre>
          </div>
          <div class="transcript-meta">
            ${window.transcriptData ? `
              <span class="meta-item">${ui.sourceLabel}: ${escapeHtml(getSourceTypeLabel(window.transcriptData.source_type))}</span>
              ${window.transcriptData.source_type === 'upload'
      ? `<span class="meta-item">${ui.sourceFileLabel}: ${escapeHtml(window.transcriptData.source_filename || window.transcriptData.title || '')}</span>`
      : `<span class="meta-item">${ui.videoIdLabel}: ${escapeHtml(window.transcriptData.video_id)}</span>`
    }
              <span class="meta-item">${ui.languageLabel}: ${escapeHtml(window.transcriptData.language)} ${window.transcriptData.is_generated ? ui.autoLabel : ''}</span>
              <span class="meta-item">${ui.linesLabel}: ${window.transcriptData.line_count}</span>
            ` : ''}
          </div>
        </div>
        
        <div class="blog-section">
          <div class="section-header">
            <div>
              <h3>${ui.seoBlogPost}</h3>
            </div>
            <div class="export-buttons">
              <button class="btn btn-export" onclick="window.copyBlogContent(this)">${ui.copy}</button>
              <button class="btn btn-export" onclick="window.downloadBlogContent(this)">${ui.download}</button>
            </div>
          </div>
          
          <div class="blog-card">
            
            <div class="blog-scroll-container">
              <h1 class="blog-title" style="font-size: 1.5rem; margin-bottom: 1rem;">${blog.title}</h1>
              <p class="blog-intro" style="font-style: italic; margin-bottom: 1.5rem; color: var(--text-muted);">${blog.meta_description || blog.intro}</p>
              
              ${blog.intro ? `<div class="blog-section-content"><p>${formatContent(blog.intro)}</p></div>` : ''}
              
              ${blog.sections ? blog.sections.map(section => `
                <div class="blog-section-content">
                  <h2>${section.title}</h2>
                  <div>${formatContent(section.content)}</div>
                </div>
              `).join('') : ''}
              
              ${blog.keywords ? `
                <div class="blog-keywords" style="margin-top: 2rem;">
                  <h4>${ui.targetKeywords}:</h4>
                  ${blog.keywords.map(k => `<span class="keyword-tag">${k}</span>`).join('')}
                </div>
              ` : ''}
            </div>
          </div>
        </div>
      </div>
      
      <!-- Row 2: Social Posts -->
      <div class="social-posts-section">
        <h3 class="section-title">${ui.socialMediaPosts}</h3>
        <p class="section-subtitle">${ui.readyToPublish}</p>
        
        <div class="social-posts-grid">
          <!-- LinkedIn Post -->
          <div class="social-post-card linkedin">
            <div class="post-header">
              <div class="platform-label">
                <span class="platform-icon">in</span>
                <span>${ui.linkedInPost}</span>
              </div>
              <button class="btn btn-post linkedin-btn" onclick="window.copyToClipboard(this, decodeURIComponent('${encodeInlineArg(linkedinContent)}'))">${ui.copyPost}</button>
            </div>
            
            <div class="post-content">
              <p>${formatContent(linkedinContent)}</p>
              ${aiSocial?.linkedin?.hashtags ? `
                <div class="hashtags">${aiSocial.linkedin.hashtags.join(' ')}</div>
              ` : ''}
            </div>
            
            <div class="attached-clip">
              <div class="clip-mini-header" style="margin-bottom: 8px; font-size: 0.8rem; color: var(--text-muted);">
                ${ui.recommendedAttachment}: <strong>${linkedinClip.title || ui.bestClip}</strong>
              </div>
              <div class="clip-thumbnail" style="${clipThumbnailStyle}" 
                   onclick="window.playClip(this, '${sourceMeta.sourceType}', decodeURIComponent('${encodeInlineArg(sourceMeta.sourceId)}'), ${linkedinWindow.start}, ${linkedinWindow.end})">
                <div class="video-overlay"></div>
                <div class="video-controls">
                  <span class="play-icon">&#9654;</span>
                  <span class="time-display">${formatTime(linkedinWindow.start)} - ${formatTime(linkedinWindow.end)}</span>
                </div>
              </div>
              <div
                class="clip-download-container"
                style="margin-top: 8px;"
                data-download-key="${linkedinKey}"
                data-source-type="${sourceMeta.sourceType}"
                data-source-id="${escapeAttribute(sourceMeta.sourceId)}"
                data-start="${linkedinWindow.start}"
                data-end="${linkedinWindow.end}"
                data-title="${encodeInlineArg(linkedinTitle)}"
              >
                ${renderDownloadControl(sourceMeta.sourceType, sourceMeta.sourceId, linkedinWindow.start, linkedinWindow.end, linkedinTitle, linkedinKey)}
              </div>
            </div>
          </div>
          
          <!-- Twitter/X Thread -->
          <div class="social-post-card twitter">
            <div class="post-header">
              <div class="platform-label">
                <span class="platform-icon">X</span>
                <span>${ui.twitterThread}</span>
              </div>
            </div>
            
            <div class="thread-tweets">
              ${twitterThread.map((tweet, index) => `
                <div class="tweet-item">
                  <div class="tweet-header" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                    <span class="tweet-number" style="font-weight: bold; color: var(--text-muted); font-size: 0.8rem;">${ui.tweetPrefix} ${index + 1}/${twitterThread.length}</span>
                    <button class="btn-copy-post" onclick="window.copyToClipboard(this, decodeURIComponent('${encodeInlineArg(tweet.content)}'))">${ui.copyTweet}</button>
                  </div>
                  <p>${tweet.content}</p>
                </div>
              `).join('')}
            </div>
            
            <div class="attached-clip" style="margin-top: 1rem;">
               <div class="clip-mini-header" style="margin-bottom: 8px; font-size: 0.8rem; color: var(--text-muted);">
                ${ui.recommendedAttachment}: <strong>${twitterClip.title || ui.bestClip}</strong>
              </div>
              <div class="clip-thumbnail" style="${clipThumbnailStyle}" 
                   onclick="window.playClip(this, '${sourceMeta.sourceType}', decodeURIComponent('${encodeInlineArg(sourceMeta.sourceId)}'), ${twitterWindow.start}, ${twitterWindow.end})">
                <div class="video-overlay"></div>
                <div class="video-controls">
                  <span class="play-icon">&#9654;</span>
                  <span class="time-display">${formatTime(twitterWindow.start)} - ${formatTime(twitterWindow.end)}</span>
                </div>
              </div>
              <div
                class="clip-download-container"
                style="margin-top: 8px;"
                data-download-key="${twitterKey}"
                data-source-type="${sourceMeta.sourceType}"
                data-source-id="${escapeAttribute(sourceMeta.sourceId)}"
                data-start="${twitterWindow.start}"
                data-end="${twitterWindow.end}"
                data-title="${encodeInlineArg(twitterTitle)}"
              >
                ${renderDownloadControl(sourceMeta.sourceType, sourceMeta.sourceId, twitterWindow.start, twitterWindow.end, twitterTitle, twitterKey)}
              </div>
            </div>
          </div>
          
          <!-- Facebook Post -->
          <div class="social-post-card facebook">
            <div class="post-header">
              <div class="platform-label">
                <span class="platform-icon">f</span>
                <span>${ui.facebookPost}</span>
              </div>
              <button class="btn btn-post facebook-btn" onclick="window.copyToClipboard(this, decodeURIComponent('${encodeInlineArg(facebookContent)}'))">${ui.copyPost}</button>
            </div>
            
            <div class="post-content">
              <p>${formatContent(facebookContent)}</p>
            </div>
            
            <div class="attached-clip">
              <div class="clip-mini-header" style="margin-bottom: 8px; font-size: 0.8rem; color: var(--text-muted);">
                ${ui.recommendedAttachment}: <strong>${facebookClip.title || ui.bestClip}</strong>
              </div>
              <div class="clip-thumbnail" style="${clipThumbnailStyle}" 
                   onclick="window.playClip(this, '${sourceMeta.sourceType}', decodeURIComponent('${encodeInlineArg(sourceMeta.sourceId)}'), ${facebookWindow.start}, ${facebookWindow.end})">
                <div class="video-overlay"></div>
                <div class="video-controls">
                  <span class="play-icon">&#9654;</span>
                  <span class="time-display">${formatTime(facebookWindow.start)} - ${formatTime(facebookWindow.end)}</span>
                </div>
              </div>
              <div
                class="clip-download-container"
                style="margin-top: 8px;"
                data-download-key="${facebookKey}"
                data-source-type="${sourceMeta.sourceType}"
                data-source-id="${escapeAttribute(sourceMeta.sourceId)}"
                data-start="${facebookWindow.start}"
                data-end="${facebookWindow.end}"
                data-title="${encodeInlineArg(facebookTitle)}"
              >
                ${renderDownloadControl(sourceMeta.sourceType, sourceMeta.sourceId, facebookWindow.start, facebookWindow.end, facebookTitle, facebookKey)}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  `;
}


function renderInputForm() {
  const appLanguage = getAppLanguage();
  const ui = getCmUiText();
  return `
    <div class="url-input-wrapper">
      <input 
        type="text" 
        id="youtube-url" 
        class="url-input" 
        placeholder="${ui.inputPlaceholder}"
        value="${escapeAttribute(currentUrl)}"
      />
    </div>

    <div class="input-separator">${ui.inputOrLabel}</div>

    <label for="video-file" class="file-input-wrapper">
      <input
        type="file"
        id="video-file"
        class="file-input"
        accept="video/mp4"
      />
      <span id="video-file-label" class="file-input-label">${ui.inputUploadLabel}</span>
    </label>
    
    <div class="language-select-wrapper">
      <select id="language-select" class="language-select">
        <option value="pl" ${appLanguage === 'pl' ? 'selected' : ''}>Polski</option>
        <option value="en" ${appLanguage === 'en' ? 'selected' : ''}>English</option>
      </select>
    </div>
    
    <button id="maximize-btn" class="btn btn-maximize">
      ${ui.maximizeButton}
    </button>
  `;
}

function renderProgressBar() {
  const ui = getCmUiText();
  const state = getContentMaximizerJobState();
  const progress = state.progress || 0;
  const message = escapeHtml(localizeCmProgressMessage(state.stage, state.message || ui.progressInitializing));
  const timeRemaining = escapeHtml(localizeCmTimeRemaining(state.timeRemaining || ''));

  return `
    <div class="progress-container" style="width: 100%; padding: 20px; text-align: center; border-top: 1px solid var(--border-subtle);">
      <div style="display: flex; justify-content: space-between; margin-bottom: 5px; font-size: 0.9rem; color: var(--text-muted);">
          <span class="progress-message">${message}</span>
          <div style="text-align: right;">
              <span class="progress-percent">${Math.round(progress)}%</span>
              <span class="progress-time" style="display: block; font-size: 0.8em; color: var(--accent-secondary);">${timeRemaining}</span>
          </div>
      </div>
      <div class="progress-bar-wrapper" style="width: 100%; height: 8px; background: rgba(255,255,255,0.05); border-radius: 4px; overflow: hidden;">
        <div class="progress-bar-fill" style="width: ${progress}%; height: 100%; background: linear-gradient(90deg, #6366f1 0%, #a855f7 100%); transition: width 0.3s ease;">
            <div class="progress-bar-pulse"></div>
        </div>
      </div>
    </div>
  `;
}

export function initContentMaximizerEvents() {
  // Bind JobManager update to re-render
  if (window.jobManager) {
    // Unsubscribe previous listener if exists
    if (window.cmJobUnsubscribe) {
      window.cmJobUnsubscribe();
    }

    window.cmJobUnsubscribe = window.jobManager.subscribe((state) => {
      const onContentMaximizerPage = Boolean(document.querySelector('.content-maximizer-page'));
      if (!onContentMaximizerPage) {
        return;
      }

      const inputContainer = document.getElementById('cm-input-container');
      const progressContainer = document.getElementById('cm-progress-container');
      const maximizeBtn = document.getElementById('maximize-btn');
      const inputs = document.querySelectorAll('.url-input, .language-select, .file-input');
      const isCmJob = state.jobType === 'content-maximizer';
      const isOtherJobRunning = state.isGenerating && state.jobType && state.jobType !== 'content-maximizer';

      if (!isCmJob) {
        if (progressContainer) progressContainer.style.display = 'none';
        if (maximizeBtn) maximizeBtn.disabled = isOtherJobRunning;
        inputs.forEach(el => {
          el.disabled = Boolean(isOtherJobRunning);
        });
      }

      // 1. Handle Error
      if (isCmJob && state.error) {
        showToast(`${getCmUiText().toastGenerationErrorPrefix}${state.error}`, 'error');
        if (progressContainer) progressContainer.style.display = 'none';
        if (maximizeBtn) maximizeBtn.disabled = false;
        inputs.forEach(el => el.disabled = false);
        return;
      }

      // 2. Handle Generation (Progress)
      if (isCmJob && state.isGenerating) {
        if (progressContainer) progressContainer.style.display = 'block';
        if (maximizeBtn) maximizeBtn.disabled = true;
        inputs.forEach(el => el.disabled = true);

        // Update progress bar
        const progress = state.progress || 0;
        const message = localizeCmProgressMessage(state.stage, state.message || getCmUiText().progressProcessing);
        const timeRemaining = localizeCmTimeRemaining(state.timeRemaining || '');

        const pBar = progressContainer?.querySelector('.progress-bar-fill');
        const pMsg = progressContainer?.querySelector('.progress-message');
        const pPct = progressContainer?.querySelector('.progress-percent');
        const pTime = progressContainer?.querySelector('.progress-time');

        if (pBar) pBar.style.width = `${Math.max(5, progress)}%`; // Min 5% width
        if (pMsg) pMsg.textContent = message;
        if (pPct) pPct.textContent = `${Math.round(progress)}%`;
        if (pTime) pTime.textContent = timeRemaining;

      } else if (isCmJob && !state.result && !isProcessed) {
        // 3. Handle Idle/Reset (only if NOT manually fetching)
        // We need to be careful not to hide the manual "Fetching..." state if JobManager is just idle before start.
        // But since startJob resets immediately, checking state.error is crucial.

        // If we are here, JobManager is idle, no result, no error.
        // This is the default state.
        // We typically don't want to force-reset UI here if we are manually waiting for fetch.
        // But `maximizeBtn` click handler manages the manual state.

        // Let's only re-enable inputs if we are truly done/cancelled.
        // But relying on "not generating" is tricky if we haven't started yet.
        // However, startJob sets isGenerating=true synchronously.

        // So this block is for "Cancelled" or "Reset".
        // We won't auto-hide progress here to avoid flickering, but we re-enable inputs.
        if (maximizeBtn) maximizeBtn.disabled = false;
        inputs.forEach(el => el.disabled = false);
      }

      // 4. Handle Completion
      if (isCmJob && state.result && !isProcessed) {
        handleJobCompletion(state.result);
      } else if (isCmJob && !state.isGenerating && !state.result && !state.error && !isProcessed) {
        // Reset UI only if we are truly idle and not just starting
        // But we need to distinguish "Initial Idle" from "Finished".
        // For now, let's just re-enable inputs for safety if not maximizing
      }
    });
  }

  const maximizeBtn = document.getElementById('maximize-btn');
  const youtubeUrl = document.getElementById('youtube-url');
  const languageSelect = document.getElementById('language-select');
  const videoFileInput = document.getElementById('video-file');
  const videoFileLabel = document.getElementById('video-file-label');

  languageSelect?.addEventListener('change', () => {
    setAppLanguage(languageSelect.value);
  });

  videoFileInput?.addEventListener('change', () => {
    const file = videoFileInput.files?.[0];
    if (!videoFileLabel) return;
    videoFileLabel.textContent = file?.name || getCmUiText().inputUploadLabel;
  });

  maximizeBtn?.addEventListener('click', async () => {
    const url = youtubeUrl?.value?.trim() || '';
    const selectedFile = videoFileInput?.files?.[0] || null;
    const useUpload = Boolean(selectedFile);
    currentUrl = url;
    const language = document.getElementById('language-select')?.value || getAppLanguage();
    const managerState = window.jobManager?.getState?.();
    if (managerState?.isGenerating && managerState.jobType && managerState.jobType !== 'content-maximizer') {
      showToast(getCmUiText().toastAnotherJobRunning, 'warning');
      return;
    }

    if (!useUpload && !url) {
      showToast(getCmUiText().toastInvalidInput, 'error');
      return;
    }

    if (useUpload && !isValidMp4File(selectedFile)) {
      showToast(getCmUiText().toastInvalidInput, 'error');
      return;
    }

    if (!useUpload && !isValidYouTubeUrl(url)) {
      showToast(getCmUiText().toastInvalidUrl, 'error');
      return;
    }

    // Manual UI Toggle: Show Progress Bar immediately for "Fetching" state
    const progressContainer = document.getElementById('cm-progress-container');
    const maximizeBtn = document.getElementById('maximize-btn');
    const inputs = document.querySelectorAll('.url-input, .language-select, .file-input');

    if (maximizeBtn) maximizeBtn.disabled = true;
    inputs.forEach(el => el.disabled = true);

  if (progressContainer) {
      progressContainer.style.display = 'block';
      // Set initial state
      const pMsg = progressContainer.querySelector('.progress-message');
      const pPct = progressContainer.querySelector('.progress-percent');
      const pBar = progressContainer.querySelector('.progress-bar-fill');
      const pTime = progressContainer.querySelector('.progress-time');

      if (pMsg) pMsg.textContent = useUpload ? getCmUiText().progressUploading : getCmUiText().progressFetching;
      if (pPct) pPct.textContent = '0%';
      if (pBar) pBar.style.width = '5%';
      if (pTime) pTime.textContent = getCmUiText().progressFetchingEta;
    }

    // Start Job
    isProcessed = false;
    window.contentData = null;
    window.transcriptData = null;

    try {
      try {
        await syncAIConfigToBackend();
      } catch (syncError) {
        console.warn('AI config sync failed before generation:', syncError);
      }
      requestNotificationPermission();

      let transcriptResponse;
      if (useUpload) {
        const formData = new FormData();
        formData.append('video', selectedFile);
        formData.append('language', language);
        transcriptResponse = await fetch(apiUrl('/api/transcript/upload'), {
          method: 'POST',
          body: formData
        });
      } else {
        transcriptResponse = await fetch(apiUrl('/api/transcript'), {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ url, language })
        });
      }

      const transcriptData = await transcriptResponse.json();

      if (!transcriptData.success) {
        showToast(`${getCmUiText().toastErrorPrefix}${transcriptData.error}`, 'error');
        // Revert UI
        if (maximizeBtn) maximizeBtn.disabled = false;
        inputs.forEach(el => el.disabled = false);
        if (progressContainer) progressContainer.style.display = 'none';
        return;
      }

      window.transcriptData = transcriptData;
      // showToast(`Transcript fetched!`, 'success'); // Removed alert/toast per user preference for smooth flow

      // Step 2: Start Streaming Job
      const payload = {
        transcript: transcriptData.transcript,
        segments: transcriptData.segments,
        language: language,
        generate: ['clips', 'blog', 'social']
      };

      window.jobManager.startJob(
        apiUrl('/api/process_stream'),
        withAIConfig(payload),
        {
          initialProgress: 10,
          initialMessage: getCmUiText().progressAnalyzing,
          initialTimeRemaining: '~60s',
          jobType: 'content-maximizer'
        }
      );

    } catch (error) {
      console.error('Error:', error);
      showToast(getCmUiText().toastConnectFailed, 'error');
      // Revert UI
      if (maximizeBtn) maximizeBtn.disabled = false;
      inputs.forEach(el => el.disabled = false);
      if (progressContainer) progressContainer.style.display = 'none';
    }
  });

}

function handleJobCompletion(result) {
  if (result.success) {
    window.contentData = result; // The result structure matches what we expect (clips, blog, social)
    isProcessed = true;

    // Re-render
    const page = document.querySelector('.content-maximizer-page');
    if (page) {
      page.outerHTML = renderContentMaximizerPage();
      initContentMaximizerEvents();
      initResultsEvents();
    }

    showToast(getCmUiText().toastContentGenerated, 'success');
    saveCurrentProject(true);
    const title = window.transcriptData?.title || 'Video';
    notifyContentMaximizerComplete(title);

    // Clear job result so we don't re-trigger
    window.jobManager.result = null;
  } else {
    const errors = result.errors?.join(', ') || getCmUiText().unknownError;
    showToast(`${getCmUiText().toastGenerationErrorPrefix}${errors}`, 'error');
  }
}

function initResultsEvents() {
  // Save Project Button - REMOVED for Auto-Save

  // Tab switching
  document.querySelectorAll('.tab').forEach(tab => {
    tab.addEventListener('click', () => {
      currentTab = tab.dataset.tab;
      const resultsSection = document.querySelector('.results-section');
      if (resultsSection) {
        resultsSection.outerHTML = renderResultsTabs();
        initResultsEvents();
      }
    });
  });

  // Category filtering
  document.querySelectorAll('.filter-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      currentCategory = btn.dataset.category;
      const videoTab = document.querySelector('.video-clips-tab');
      if (videoTab) {
        videoTab.outerHTML = renderVideoClipsTab();
        initResultsEvents();
      }
    });
  });

  // Platform expand/collapse - Event delegation style
  const platformsAccordion = document.querySelector('.platforms-accordion');
  if (platformsAccordion) { // Use delegation if possible, or bind to elements
    // Handled inline via onclick="togglePlatform(this)" as safe approach for dynamic content
  }

  // Re-bind click event listeners just in case inline onclicks are frowned upon, 
  // but strictly speaking inline is fine for this prototype. 
  // We added togglePlatform to window so inline works.

  // Also make sure we attach specific listeners where needed
  document.querySelectorAll('.platform-row').forEach(row => {
    row.addEventListener('click', function (e) {
      // Prevent triggering if clicking a button inside
      if (e.target.tagName === 'BUTTON') return;
      window.togglePlatform(this);
    });
  });
}

function isValidYouTubeUrl(url) {
  const pattern = /^(https?:\/\/)?(www\.)?(youtube\.com|youtu\.be)\/.+/;
  return pattern.test(url);
}

function isValidMp4File(file) {
  if (!file) return false;
  const name = String(file.name || '').toLowerCase();
  const type = String(file.type || '').toLowerCase();
  return name.endsWith('.mp4') || type === 'video/mp4';
}

function showToast(message, type = 'info') {
  // Remove existing toasts
  document.querySelectorAll('.toast').forEach(t => t.remove());

  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.textContent = message;
  document.body.appendChild(toast);

  setTimeout(() => toast.classList.add('show'), 10);
  setTimeout(() => {
    toast.classList.remove('show');
    setTimeout(() => toast.remove(), 300);
  }, 3000);
}

// Helper functions for UI interactions (exposed to window for inline calls)
window.copyBlogContent = async function (btn) {
  if (!window.contentData?.blog) return;
  const ui = getCmUiText();
  const blog = window.contentData.blog;

  let text = `# ${blog.title}\n\n`;
  if (blog.intro) text += `*${blog.intro}*\n\n`;

  if (blog.sections) {
    blog.sections.forEach(section => {
      text += `## ${section.title}\n\n${section.content}\n\n`;
    });
  }

  if (blog.keywords) {
    text += `\n**Keywords:** ${blog.keywords.join(', ')}`;
  }

  try {
    await navigator.clipboard.writeText(text);
    const originalText = btn.innerText;
    btn.innerText = ui.copiedButton;
    setTimeout(() => btn.innerText = originalText, 2000);
    showToast(ui.blogCopied, 'success');
  } catch (err) {
    showToast(ui.copyFailed, 'error');
  }
};

window.downloadBlogContent = function (btn) {
  if (!window.contentData?.blog) return;
  const blog = window.contentData.blog;

  let text = `# ${blog.title}\n\n`;
  if (blog.intro) text += `*${blog.intro}*\n\n`;

  if (blog.sections) {
    blog.sections.forEach(section => {
      text += `## ${section.title}\n\n${section.content}\n\n`;
    });
  }

  if (blog.keywords) {
    text += `\n**Keywords:** ${blog.keywords.join(', ')}`;
  }

  const blob = new Blob([text], { type: 'text/markdown' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `${blog.title.replace(/[^a-z0-9]/gi, '_').toLowerCase()}.md`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
};

window.exportTranscript = async function (format, btn) {
  if (!window.transcriptData) return;
  const ui = getCmUiText();
  const data = window.transcriptData;
  const videoId = data.video_id;
  const filename = `transcript_${videoId}`;

  let content = '';
  let type = 'text/plain';
  let ext = 'txt';

  if (format === 'copy') {
    try {
      await navigator.clipboard.writeText(data.transcript);
      const originalText = btn.innerText;
      btn.innerText = ui.copiedButton;
      setTimeout(() => btn.innerText = originalText, 2000);
      showToast(ui.transcriptCopied, 'success');
    } catch (err) {
      showToast(ui.copyFailed, 'error');
    }
    return;
  }

  if (format === 'txt') {
    content = data.transcript;
    type = 'text/plain';
    ext = 'txt';
  } else if (format === 'json') {
    content = JSON.stringify(data, null, 2);
    type = 'application/json';
    ext = 'json';
  } else if (format === 'srt') {
    content = convertToSRT(data.segments);
    type = 'text/plain';
    ext = 'srt';
  } else if (format === 'vtt') {
    content = convertToVTT(data.segments);
    type = 'text/vtt'; // Correct mime type for VTT
    ext = 'vtt';
  }

  const blob = new Blob([content], { type: type });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `${filename}.${ext}`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
};

function convertToSRT(segments) {
  if (!segments || !Array.isArray(segments)) return '';
  return segments.map((seg, index) => {
    const start = formatTimestamp(seg.start, true);
    const end = formatTimestamp(seg.start + seg.duration, true);
    return `${index + 1}\n${start} --> ${end}\n${seg.text}\n`;
  }).join('\n');
}

function convertToVTT(segments) {
  if (!segments || !Array.isArray(segments)) return 'WEBVTT\n\n';
  const body = segments.map((seg) => {
    const start = formatTimestamp(seg.start, false);
    const end = formatTimestamp(seg.start + seg.duration, false);
    return `${start} --> ${end}\n${seg.text}\n`;
  }).join('\n');
  return 'WEBVTT\n\n' + body;
}

function formatTimestamp(seconds, isSrt) {
  const date = new Date(0);
  date.setSeconds(seconds);
  const iso = date.toISOString().substr(11, 12); // HH:MM:SS.mmm
  if (isSrt) return iso.replace('.', ',');
  return iso;
}

window.togglePlatform = function (element) {
  const content = element.querySelector('.row-content');
  const icon = element.querySelector('.expand-icon');

  if (content.style.display === 'none') {
    content.style.display = 'block';
    icon.style.transform = 'rotate(180deg)';
    element.classList.add('expanded');
  } else {
    content.style.display = 'none';
    icon.style.transform = 'rotate(0deg)';
    element.classList.remove('expanded');
  }
};


window.playClip = function (element, sourceType, sourceId, start, end) {
  if (event) event.stopPropagation();

  const container = element.closest('.clip-thumbnail');
  if (!container) return;

  const startSec = Number.isFinite(Number(start)) ? Math.floor(Number(start)) : 0;
  const endSec = Number.isFinite(Number(end)) ? Math.ceil(Number(end)) : startSec + 60;

  if (String(sourceType) === 'upload') {
    const safeSourceId = encodeURIComponent(String(sourceId || ''));
    const mediaUrl = apiUrl(`/api/media/${safeSourceId}`);
    container.innerHTML = `
      <video class="clip-video-player" controls autoplay preload="metadata">
        <source src="${mediaUrl}" type="video/mp4" />
      </video>
    `;
    const video = container.querySelector('video');
    if (video) {
      const onReady = () => {
        try {
          video.currentTime = Math.max(0, startSec);
        } catch (_err) {
          // Ignore seek errors from stale media metadata.
        }
        video.play().catch(() => {});
      };
      if (video.readyState >= 1) {
        onReady();
      } else {
        video.addEventListener('loadedmetadata', onReady, { once: true });
      }
      video.addEventListener('timeupdate', () => {
        if (video.currentTime >= endSec) {
          video.pause();
        }
      });
    }
    return;
  }

  const safeVideoId = String(sourceId || '').replace(/[^a-zA-Z0-9_-]/g, '');
  const embedUrl = `https://www.youtube.com/embed/${safeVideoId}?start=${startSec}&end=${endSec}&autoplay=1&rel=0`;

  container.innerHTML = `
    <iframe 
      width="100%" 
      height="100%" 
      src="${embedUrl}" 
      title="${getCmUiText().ytPlayerTitle}" 
      frameborder="0" 
      allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" 
      allowfullscreen
    ></iframe>
  `;
};

window.copyToClipboard = function (btn, text) {
  const ui = getCmUiText();
  navigator.clipboard.writeText(text).then(() => {
    const originalText = btn.innerText;
    btn.innerText = ui.copiedButton;
    setTimeout(() => btn.innerText = originalText, 2000);
  });
  if (event) event.stopPropagation();
};

window.downloadClip = async function (sourceType, sourceId, start, end, title, btn) {
  if (event) event.stopPropagation();
  const normalizedSourceType = sourceType === 'upload' ? 'upload' : 'youtube';
  const normalizedSourceId = String(sourceId || '');
  const clipKey = buildClipDownloadKey(normalizedSourceType, normalizedSourceId, start, end);
  const existing = getClipDownloadState(clipKey);
  if (existing && (existing.status === 'queued' || existing.status === 'running')) {
    return;
  }

  setClipDownloadState(clipKey, {
    status: 'queued',
    stage: 'preparing',
    progressPercent: 2,
    remainingSeconds: 0,
    estimatedSeconds: 0,
  });
  refreshDownloadControl(clipKey);

  try {
    const response = await fetch(apiUrl('/api/download_clip/start'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        source_type: normalizedSourceType,
        source_id: normalizedSourceId,
        video_id: normalizedSourceId,
        start,
        end,
        title: title || 'clip'
      })
    });
    const payload = await response.json();
    if (!response.ok || !payload.success) {
      throw new Error(payload.error || getCmUiText().unknownError);
    }

    setClipDownloadState(clipKey, {
      status: payload.status || 'running',
      stage: payload.stage || 'preparing',
      progressPercent: payload.progress_percent ?? 5,
      remainingSeconds: payload.remaining_seconds ?? payload.estimated_seconds ?? 0,
      estimatedSeconds: payload.estimated_seconds ?? 0,
      jobId: payload.job_id,
    });
    refreshDownloadControl(clipKey);

    if (payload.clip_cached) {
      showDownloadBubble(getCmUiText().bubbleClipCached, 'success');
    } else if (normalizedSourceType === 'youtube' && payload.first_download_for_video) {
      showDownloadBubble(getCmUiText().bubbleFirstClipHint, 'info');
    } else if (normalizedSourceType === 'youtube') {
      showDownloadBubble(getCmUiText().bubbleNextClipsHint, 'info');
    }

    if (payload.status === 'completed') {
      triggerClipFileDownload(payload.job_id);
      showDownloadBubble(getCmUiText().bubbleClipReady, 'success');
      setTimeout(() => {
        setClipDownloadState(clipKey, { status: 'idle', progressPercent: 0, stage: '' });
        refreshDownloadControl(clipKey);
      }, 2200);
      return;
    }

    await pollClipDownloadStatus(clipKey, payload.job_id);
  } catch (e) {
    console.error(e);
    setClipDownloadState(clipKey, { status: 'error', stage: 'error', progressPercent: 0 });
    refreshDownloadControl(clipKey);
    showDownloadBubble(`${getCmUiText().bubbleClipFailedPrefix}${e.message}`, 'error');
    setTimeout(() => {
      setClipDownloadState(clipKey, { status: 'idle', progressPercent: 0, stage: '' });
      refreshDownloadControl(clipKey);
    }, 2500);
  }
};

// Reset state for fresh load
export function resetContentMaximizer() {
  isProcessed = false;
  currentTab = 'video-clips';
  currentCategory = 'All';
}


