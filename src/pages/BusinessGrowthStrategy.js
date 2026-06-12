import './BusinessGrowthStrategy.css';
import { notifyBusinessGrowthStrategyComplete, requestNotificationPermission } from '../utils/notifications.js';
import { jobManager } from '../utils/JobManager.js';
import { decodeHtmlEntities, escapeAttribute, escapeHtml, sanitizeDeep } from '../utils/sanitize.js';
import { syncAIConfigToBackend, withAIConfig } from '../utils/storage.js';
import { getAppLanguage } from '../utils/settings.js';
import { apiUrl } from '../utils/api.js';

// State
let selectedModel = null;
let currentStep = 1;
let gamePlanData = {};

// Content Ideas State (Tab 4)
let contentIdeasStep = 1;  // 1: Titles, 2: Chapters, 3: Script
let generatedTitles = [];
let selectedTitle = null;
let selectedTitleIndex = -1;
let chapterStructure = null;
let scriptChapters = {};
let selectedScriptOptions = {}; // Track selected option per chapter: { 0: 'a', 1: 'b', ... }
let currentChapterIndex = 0;
let isGenerating = false;
let isGeneratingEntireScript = false;
let awaitingGamePlanResult = false;

const BGS_JOB_TYPE = 'business-growth-strategy';
const LEGACY_BGS_JOB_TYPE = ['game', 'plan'].join('-');
const BGS_PROJECT_TYPE = 'business-growth-strategy';
const BGS_GENERATE_ENDPOINT = apiUrl('/api/generate_business_growth_strategy');

function getGenerationLanguage() {
  return getAppLanguage() === 'en' ? 'en' : 'pl';
}

function getGamePlanUiText() {
  const isPolish = getAppLanguage() === 'pl';
  if (isPolish) {
    return {
      step1Title: 'Strategia wzrostu biznesu',
      step1Subtitle: 'Zdefiniujmy strategię treści z użyciem agentów AI',
      step1Indicator: 'Krok 1: Wybierz Model Biznesowy',
      b2bAgencyTitle: 'Agencja B2B',
      b2bSaasTitle: 'Software House / SaaS B2B',
      b2cMobileTitle: 'Aplikacja Mobilna B2C',
      b2cCoachingTitle: 'Coaching / Edukacja B2C',
      b2bAgencyDesc: 'Wybierz, jeśli prowadzisz biznes usługowy, agencję marketingową lub konsulting.',
      b2bSaasDesc: 'Wybierz, jeśli prowadzisz biznes produktowy lub software house.',
      b2cMobileDesc: 'Wybierz, jeśli prowadzisz konsumencką aplikację mobilną.',
      b2cCoachingDesc: 'Wybierz, jeśli jesteś coachem, twórcą kursów lub edukatorem.',
      nextStep: 'Następny Krok ->',
      step2Title: 'Dodaj Kontekst',
      step2Subtitle: 'Dostarcz naszym agentom dane, których potrzebują.',
      step2Indicator: 'Krok 2: Materiały Referencyjne',
      websiteLabel: '1. URL strony biznesowej',
      websitePlaceholder: 'https://twojastrona.pl',
      transcriptsLabel: '2. Transkrypcje rozmów sprzedażowych (3+)',
      transcriptsDrop: 'Kliknij lub przeciągnij i upuść .txt, .pdf lub .docx',
      filePrefix: 'Plik',
      contextLabel: '3. O Twoim Biznesie',
      optional: '(Opcjonalnie)',
      contextPlaceholder: 'Dodatkowy kontekst...',
      progressInitializing: 'Inicjalizacja...',
      progressStartingJob: 'Uruchamianie zadania...',
      progressScraping: 'Pobieranie treści strony...',
      progressScrapingDone: 'Pobrano treść strony',
      progressLoadedContext: 'Wczytano kontekst projektu',
      progressMarketResearch: 'Analiza rynku i konkurencji...',
      progressMarketResearchDone: 'Badanie rynku zakończone',
      progressPsychoanalysis: 'Analiza psychoanalityczna...',
      progressPsychoanalysisDone: 'Psychoanaliza zakończona',
      progressCreativeBrief: 'Tworzenie briefu kreatywnego...',
      progressFinalizing: 'Finalizowanie strategii wzrostu biznesu...',
      back: 'Wstecz',
      startWorkflow: 'Uruchom Workflow Agentów',
      step3Title: 'Strategia Wzrostu Biznesu',
      step3SubtitlePrefix: 'Wynik analizy AI dla',
      tabMarketResearch: 'Badanie Rynku',
      tabPsychoanalysis: 'Psychoanaliza',
      tabCreativeBrief: 'Brief Kreatywny',
      tabContentIdeas: 'Pomysły na Treści',
      startOver: '<- Zacznij od nowa',
      exportLabel: 'Eksport:',
      copy: 'Kopiuj',
      copyClipboardTitle: 'Kopiuj do schowka',
      downloadTxtTitle: 'Pobierz jako TXT',
      downloadPdfTitle: 'Pobierz jako PDF',
      openGoogleDocsTitle: 'Otwórz w Google Docs',
      copySuccess: 'Skopiowano do schowka.',
      copyFailed: 'Nie udało się skopiować. Spróbuj ponownie.',
      sectionNotFound: 'Nie znaleziono sekcji. Najpierw przełącz się na odpowiednią zakładkę.',
      openGoogleDocsCopiedPrompt: 'Otworzono Dokumenty Google. Treść została skopiowana, wklej ją skrótem Ctrl+V.',
      openGoogleDocsCopyFallback: 'Otworzono Dokumenty Google, ale nie udało się skopiować treści automatycznie. Użyj przycisku Kopiuj.',
      contentIdeasLoadingTitle: 'Generowanie 5 skutecznych tytułów wideo...',
      contentIdeasLoadingDesc: 'Analiza strategii wzrostu biznesu pod kątem koncepcji o wysokim potencjale.',
      contentIdeasEmptyTitle: 'Generuj pomysły na treści',
      contentIdeasEmptyDesc: 'Wygeneruj 5 skutecznych tytułów na podstawie strategii wzrostu biznesu.',
      generateFiveTitles: 'Wygeneruj 5 tytułów wideo',
      titlesStepHeading: 'Krok 1: Wybierz tytuł wideo',
      regenerating: 'Generowanie ponownie...',
      generateFiveNew: 'Wygeneruj 5 nowych',
      titlesStepSubtitle: 'Wybierz najlepszy tytuł do kolejnego dłuższego materiału.',
      pillarValue: 'Wartość',
      generateSimilarTooltip: 'Wygeneruj podobne warianty',
      idealClient: 'Idealny klient',
      selectTitle: 'Wybierz tytuł',
      selectedLabel: 'Wybrano',
      nextGenerateChapters: 'Dalej: wygeneruj strukturę rozdziałów',
      backToTitles: '<- Wróć do Tytułów',
      chaptersLoading: 'Projektowanie optymalnej struktury rozdziałów...',
      chaptersStepHeading: 'Krok 2: Struktura Rozdziałów',
      regenerate: 'Wygeneruj ponownie',
      videoTitleLabel: 'Tytuł wideo',
      approveStartScripting: 'Zatwierdź i rozpocznij pisanie skryptu ->',
      chapterLabel: 'Rozdział',
      purposeLabel: 'Cel',
      keyPointsLabel: 'Kluczowe punkty',
      transitionLabel: 'Przejście',
      backToChapters: '<- Wróć do Rozdziałów',
      scriptStepHeading: 'Krok 3: Generowanie Skryptu',
      chapterWord: 'Rozdział',
      ofWord: 'z',
      progressLabel: 'Postęp',
      exportFullScript: 'Eksportuj pełny skrypt',
      saveToPipeline: 'Zapisz do Zarządzania skryptami',
      startNewScript: 'Nowy skrypt',
      previousScripts: 'Poprzednie skrypty:',
      fileLabel: 'Plik',
      writingOptionsFor: 'Tworzenie dwóch wersji skryptu dla',
      estimatedTime: 'Szacowany czas: ~30 sekund',
      savedBadge: 'Zapisano',
      useThis: 'Wybierz tę',
      readyToWriteScript: 'Gotowy, aby napisać skrypt?',
      readyToWriteScriptDesc: 'Wygenerujemy dwie opcje dla tego rozdziału. Możesz je edytować i dopracować obok siebie.',
      writeChapterScript: 'Napisz skrypt rozdziału',
      writeEntireScript: 'Napisz cały skrypt',
      generatingEntireScript: 'Generowanie całego skryptu...',
      failedGenerateEntireScript: 'Nie udało się wygenerować całego skryptu.',
      previousChapter: 'Poprzedni rozdział',
      nextChapter: 'Następny rozdział',
      resetScriptConfirm: 'To wyczyści aktualny postęp skryptu i pozwoli zacząć od nowa. Dotychczasowy skrypt w Zarządzaniu skryptami pozostanie bez zmian. Kontynuować?',
      exportButtonsHint: 'Użyj przycisków eksportu w zakładkach sekcji.',
      titleExportPrefix: 'TYTUŁ',
      chapterExportPrefix: 'ROZDZIAŁ',
      scriptNotGeneratedYet: '[Skrypt nie został jeszcze wygenerowany]',
      restoredLabel: 'Przywrócono',
      notAvailableLabel: 'Brak',
      modelLabelAgency: 'Agencja B2B',
      modelLabelSaas: 'Software House / SaaS B2B',
      failedGenerateTitles: 'Nie udało się wygenerować tytułów.',
      failedGenerateChapters: 'Nie udało się wygenerować rozdziałów.',
      failedGenerateScript: 'Nie udało się wygenerować skryptu.',
      failedSaveScriptPrefix: 'Nie udało się zapisać skryptu: ',
      saveScriptPipelineError: 'Błąd zapisu skryptu do Zarządzania skryptami.',
      networkErrorPrefix: 'Błąd sieci: ',
      generationErrorPrefix: 'Błąd generowania: ',
      anotherJobRunning: 'Inny workflow jest uruchomiony. Poczekaj na jego zakończenie.',
      marketResearchTitle: 'Badanie Rynku',
      yourAudience: 'Twoja grupa odbiorców',
      demographics: 'Demografia',
      genderMix: 'Struktura płci',
      ageRange: 'Zakres wieku',
      idealClientDescription: 'Opis idealnego klienta',
      attitudes: 'Postawy',
      desires: 'Pragnienia',
      fears: 'Obawy',
      currentIdentity: 'Obecna tożsamość',
      desiredIdentity: 'Docelowa tożsamość',
      perceivedObstacles: 'Postrzegane przeszkody',
      lifeBeliefs: 'Przekonania życiowe',
      existingSolutionsAnalysis: 'Analiza istniejących rozwiązań',
      productsTried: 'Testowane rozwiązania',
      successes: 'Sukcesy',
      failures: 'Porażki',
      horrorStories: 'Negatywne doświadczenia',
      marketBelief: 'Przekonanie rynku',
      gapAnalysis: 'Analiza luk',
      yourProduct: 'Twój produkt',
      uniqueDifferentiators: 'Unikalne wyróżniki',
      interestingFacts: 'Ciekawe fakty',
      customerTestimonialThemes: 'Motywy opinii klientów',
      competitiveAdvantages: 'Przewagi konkurencyjne',
      positioningStatement: 'Pozycjonowanie',
      notAnalyzed: 'Brak analizy',
      noneDocumented: 'Brak danych',
      notDefined: 'Brak definicji'
    };
  }
  return {
    step1Title: 'Build Your Business Growth Strategy',
    step1Subtitle: "Let's define your content strategy using AI agents",
    step1Indicator: 'Step 1: Choose Your Business Model',
    b2bAgencyTitle: 'B2B Agency',
    b2bSaasTitle: 'B2B Software House / SaaS',
    b2cMobileTitle: 'B2C Mobile App',
    b2cCoachingTitle: 'B2C Coaching / Education',
    b2bAgencyDesc: 'Select this if you run a service-based business, marketing agency, or consultancy.',
    b2bSaasDesc: 'Select this if you run a product-based business or software development house.',
    b2cMobileDesc: 'Select this if you run a consumer-facing mobile application.',
    b2cCoachingDesc: 'Select this if you are a coach, course creator, or educator.',
    nextStep: 'Next Step ->',
    step2Title: 'Provide Context',
    step2Subtitle: 'Give our agents the data they need.',
    step2Indicator: 'Step 2: Reference Materials',
    websiteLabel: '1. Business Website URL',
    websitePlaceholder: 'https://yourwebsite.com',
    transcriptsLabel: '2. Sales Call Transcripts (3+)',
    transcriptsDrop: 'Click or Drag & Drop .txt, .pdf, or .docx',
    filePrefix: 'File',
    contextLabel: '3. About Your Business',
    optional: '(Optional)',
    contextPlaceholder: 'Any additional context...',
    progressInitializing: 'Initializing...',
    progressStartingJob: 'Starting job...',
    progressScraping: 'Scraping website...',
    progressScrapingDone: 'Scraped website content',
    progressLoadedContext: 'Loaded project context',
    progressMarketResearch: 'Analyzing Market & Competition...',
    progressMarketResearchDone: 'Market Research Complete',
    progressPsychoanalysis: 'Performing Psychoanalysis...',
    progressPsychoanalysisDone: 'Psychoanalysis Complete',
    progressCreativeBrief: 'Drafting Creative Brief...',
    progressFinalizing: 'Finalizing Business Growth Strategy...',
    back: 'Back',
    startWorkflow: 'Start Agentic Workflow',
    step3Title: 'Business Growth Strategy',
    step3SubtitlePrefix: 'AI output for',
    tabMarketResearch: 'Market Research',
    tabPsychoanalysis: 'Psychoanalysis',
    tabCreativeBrief: 'Creative Brief',
    tabContentIdeas: 'Content Ideas',
    startOver: '<- Start Over',
    exportLabel: 'Export:',
    copy: 'Copy',
    copyClipboardTitle: 'Copy to Clipboard',
    downloadTxtTitle: 'Download as TXT',
    downloadPdfTitle: 'Download as PDF',
    openGoogleDocsTitle: 'Open in Google Docs',
    copySuccess: 'Copied to clipboard.',
    copyFailed: 'Failed to copy. Please try again.',
    sectionNotFound: 'Section not found. Switch to the tab first.',
    openGoogleDocsCopiedPrompt: 'Google Docs opened. Content was copied, paste it with Ctrl+V.',
    openGoogleDocsCopyFallback: 'Google Docs opened, but content could not be copied automatically. Use the Copy button first.',
    contentIdeasLoadingTitle: 'Generating 5 High-Performing Video Titles...',
    contentIdeasLoadingDesc: 'Analyzing your business growth strategy to create viral-worthy concepts.',
    contentIdeasEmptyTitle: 'Generate Content Ideas',
    contentIdeasEmptyDesc: 'Create 5 high-performing video titles based on your business growth strategy.',
    generateFiveTitles: 'Generate 5 Video Titles',
    titlesStepHeading: 'Step 1: Choose Your Video Title',
    regenerating: 'Regenerating...',
    generateFiveNew: 'Generate 5 New',
    titlesStepSubtitle: 'Select the best title for your next long-form video.',
    pillarValue: 'Value',
    generateSimilarTooltip: 'Generate similar variations',
    idealClient: 'Ideal Client',
    selectTitle: 'Select Title',
    selectedLabel: 'Selected',
    nextGenerateChapters: 'Next: Generate Chapter Structure',
    backToTitles: '<- Back to Titles',
    chaptersLoading: 'Designing optimal chapter structure...',
    chaptersStepHeading: 'Step 2: Chapter Structure',
    regenerate: 'Regenerate',
    videoTitleLabel: 'Video Title',
    approveStartScripting: 'Approve & Start Scripting ->',
    chapterLabel: 'Chapter',
    purposeLabel: 'Purpose',
    keyPointsLabel: 'Key Points',
    transitionLabel: 'Transition',
    backToChapters: '<- Back to Chapters',
    scriptStepHeading: 'Step 3: Script Generation',
    chapterWord: 'Chapter',
    ofWord: 'of',
    progressLabel: 'Progress',
    exportFullScript: 'Export Full Script',
    saveToPipeline: 'Save to Script Management',
    startNewScript: 'Start New Script',
    previousScripts: 'Previous Scripts:',
    fileLabel: 'File',
    writingOptionsFor: 'Writing two script options for',
    estimatedTime: 'Estimated time: ~30 seconds',
    savedBadge: 'Saved',
    useThis: 'Use this',
    readyToWriteScript: 'Ready to write script?',
    readyToWriteScriptDesc: "We'll generate two options for this chapter. You can edit and refine them side-by-side.",
    writeChapterScript: 'Write Chapter Script',
    writeEntireScript: 'Write Entire Script',
    generatingEntireScript: 'Generating entire script...',
    failedGenerateEntireScript: 'Failed to generate entire script.',
    previousChapter: 'Previous Chapter',
    nextChapter: 'Next Chapter',
    resetScriptConfirm: 'This will clear the current script progress and let you start a new one. The existing script in the pipeline will remain safe. Continue?',
    exportButtonsHint: 'Use the export buttons in each section tab.',
    titleExportPrefix: 'TITLE',
    chapterExportPrefix: 'CHAPTER',
    scriptNotGeneratedYet: '[Script not generated yet]',
    restoredLabel: 'Restored',
    notAvailableLabel: 'N/A',
    modelLabelAgency: 'B2B Agency',
    modelLabelSaas: 'B2B SaaS',
    failedGenerateTitles: 'Failed to generate titles.',
    failedGenerateChapters: 'Failed to generate chapters.',
    failedGenerateScript: 'Failed to generate script.',
    failedSaveScriptPrefix: 'Failed to save script: ',
    saveScriptPipelineError: 'Error saving script to Script Management.',
    networkErrorPrefix: 'Network error: ',
    generationErrorPrefix: 'Generation Error: ',
    anotherJobRunning: 'Another workflow is running. Please wait until it finishes.',
    marketResearchTitle: 'Market Research',
    yourAudience: 'Your Audience',
    demographics: 'Demographics',
    genderMix: 'Gender Mix',
    ageRange: 'Age Range',
    idealClientDescription: 'Ideal Client',
    attitudes: 'Attitudes',
    desires: 'Desires',
    fears: 'Fears',
    currentIdentity: 'Current Identity',
    desiredIdentity: 'Desired Identity',
    perceivedObstacles: 'Perceived Obstacles',
    lifeBeliefs: 'Life Beliefs',
    existingSolutionsAnalysis: 'Existing Solutions Analysis',
    productsTried: "Products They've Tried",
    successes: 'Successes',
    failures: 'Failures',
    horrorStories: 'Horror Stories',
    marketBelief: 'Market Belief',
    gapAnalysis: 'Gap Analysis',
    yourProduct: 'Your Product',
    uniqueDifferentiators: 'Unique Differentiators',
    interestingFacts: 'Interesting Facts',
    customerTestimonialThemes: 'Customer Testimonial Themes',
    competitiveAdvantages: 'Competitive Advantages',
    positioningStatement: 'Positioning Statement',
    notAnalyzed: 'Not analyzed',
    noneDocumented: 'None documented',
    notDefined: 'Not defined'
  };
}

function localizeGamePlanProgressMessage(stage, fallbackMessage = '') {
  const ui = getGamePlanUiText();
  const raw = fallbackMessage || '';

  if (stage === 'init') {
    if (/starting job/i.test(raw)) return ui.progressStartingJob;
    if (/loaded\s+\d+\s+chars/i.test(raw)) return ui.progressLoadedContext;
    return ui.progressInitializing;
  }

  if (stage === 'scraping') return ui.progressScraping;
  if (stage === 'scraping_done') {
    const charsMatch = raw.match(/(\d+)\s+chars/i);
    if (!charsMatch) return ui.progressScrapingDone;
    return getAppLanguage() === 'pl'
      ? `Pobrano ${charsMatch[1]} znaków`
      : `Scraped ${charsMatch[1]} chars`;
  }

  if (stage === 'market_research') return ui.progressMarketResearch;
  if (stage === 'market_research_done') return ui.progressMarketResearchDone;
  if (stage === 'psychoanalysis') return ui.progressPsychoanalysis;
  if (stage === 'psychoanalysis_warn') return raw || ui.progressPsychoanalysis;
  if (stage === 'psychoanalysis_done') return ui.progressPsychoanalysisDone;
  if (stage === 'creative_brief') return ui.progressCreativeBrief;
  if (stage === 'creative_brief_done') return ui.progressFinalizing;

  return raw || ui.progressInitializing;
}

function localizeGamePlanTimeRemaining(timeRemaining = '') {
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

function getGamePlanJobState() {
  const state = jobManager.getState();
  const isGrowthStrategyJob = state.jobType === BGS_JOB_TYPE || state.jobType === LEGACY_BGS_JOB_TYPE;
  if (state.jobType && !isGrowthStrategyJob) {
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

export function renderBusinessGrowthStrategyPage() {
  if (currentStep === 1) {
    return renderStep1();
  } else if (currentStep === 2) {
    return renderStep2();
  } else if (currentStep === 3) {
    return renderStep3();
  }
}

function renderStep1() {
  const ui = getGamePlanUiText();
  return `
  <div class="growth-strategy-page">
      <header class="growth-strategy-header">
        <span class="growth-strategy-icon">&#x1F680;</span>
        <h1>${ui.step1Title}</h1>
        <p>${ui.step1Subtitle}</p>
      </header>
      
      <div class="step-indicator">
        ${ui.step1Indicator}
      </div>
      
      <div class="business-model-grid">
        <!-- B2B Agency -->
        <div class="model-card ${selectedModel === 'b2b-agency' ? 'selected' : ''}" 
             onclick="window.selectGamePlanModel('b2b-agency')">
          <h3>${ui.b2bAgencyTitle}</h3>
          <p>${ui.b2bAgencyDesc}</p>
        </div>
        
        <!-- B2B SaaS -->
        <div class="model-card ${selectedModel === 'b2b-saas' ? 'selected' : ''}" 
             onclick="window.selectGamePlanModel('b2b-saas')">
          <h3>${ui.b2bSaasTitle}</h3>
          <p>${ui.b2bSaasDesc}</p>
        </div>
        
        <!-- Mobile App (Soon) -->
        <div class="model-card disabled">
          <span class="badge-soon">SOON</span>
          <h3>${ui.b2cMobileTitle}</h3>
          <p>${ui.b2cMobileDesc}</p>
        </div>
        
        <!-- Coaching (Soon) -->
        <div class="model-card disabled">
          <span class="badge-soon">SOON</span>
          <h3>${ui.b2cCoachingTitle}</h3>
          <p>${ui.b2cCoachingDesc}</p>
        </div>
      </div>
      
      <div class="action-row">
        <button class="btn btn-next" id="btn-growth-strategy-next" ${selectedModel ? '' : 'disabled'} onclick="window.nextGamePlanStep()">
          ${ui.nextStep}
        </button>
      </div>
    </div>
  `;
}

function renderStep2() {
  const ui = getGamePlanUiText();
  const progressState = getGamePlanJobState();
  const progressMessage = escapeHtml(localizeGamePlanProgressMessage(progressState.stage, progressState.message || ui.progressInitializing));
  const safeWebsite = escapeAttribute(gamePlanData.website || '');
  const safeContext = escapeHtml(gamePlanData.context || '');
  const safeTranscriptNames = (gamePlanData.transcripts || []).map((file) => escapeHtml(file?.name || ''));

  return `
  <div class="growth-strategy-page">
      <header class="growth-strategy-header">
        <span class="growth-strategy-icon">&#x1F9E0;</span>
        <h1>${ui.step2Title}</h1>
        <p>${ui.step2Subtitle}</p>
      </header>

      <div class="step-indicator">
        ${ui.step2Indicator}
      </div>
      
      <div class="context-box">
        <div class="form-group">
            <label for="website-url">${ui.websiteLabel}</label>
            <input 
                type="text" 
                id="website-url" 
                placeholder="${ui.websitePlaceholder}" 
                value="${safeWebsite}"
                onchange="window.updateGamePlanData('website', this.value)"
            >
        </div>

        <div class="form-group">
            <label>${ui.transcriptsLabel}</label>
            <div class="file-upload-area" 
                 onclick="document.getElementById('transcript-upload').click()"
                 ondragover="event.preventDefault(); this.classList.add('dragover');"
                 ondragleave="this.classList.remove('dragover');"
                 ondrop="event.preventDefault(); this.classList.remove('dragover'); const dt = new DataTransfer(); Array.from(event.dataTransfer.files).forEach(f => dt.items.add(f)); document.getElementById('transcript-upload').files = dt.files; window.handleTranscriptUpload(document.getElementById('transcript-upload'));">
                <span class="upload-icon">&#x1F4C2;</span>
                <p>${ui.transcriptsDrop}</p>
                <input 
                    type="file" 
                    id="transcript-upload" 
                    multiple 
                    accept=".txt,.pdf,.docx" 
                    style="display: none"
                    onchange="window.handleTranscriptUpload(this)"
                >
                <div id="file-list" style="margin-top: 1rem; font-size: 0.9rem; color: var(--accent-primary);">
                    ${safeTranscriptNames.length > 0 ? safeTranscriptNames.map(name => `<div>${ui.filePrefix}: ${name}</div>`).join('') : ''}
                </div>
            </div>
        </div>

        <div class="form-group">
            <label for="business-context">${ui.contextLabel} <span style="color: var(--text-muted);">${ui.optional}</span></label>
            <textarea 
                id="business-context" 
                placeholder="${ui.contextPlaceholder}"
                onchange="window.updateGamePlanData('context', this.value)"
            >${safeContext}</textarea>
        </div>

        <!-- Progress Bar Container (Moved Inside Card) -->
        <div id="progress-container" style="display: ${progressState.isGenerating ? 'block' : 'none'}; margin-top: 20px; text-align: center; padding-top: 20px; border-top: 1px solid var(--border-subtle);">
            <div style="display: flex; justify-content: space-between; margin-bottom: 5px; font-size: 0.9rem; color: var(--text-muted);">
                <span id="progress-message">${progressMessage}</span>
                <div style="text-align: right;">
                    <span id="progress-percent">${progressState.progress || 0}%</span>
                    <span id="progress-time" style="display: block; font-size: 0.8em; color: var(--text-muted);">${escapeHtml(localizeGamePlanTimeRemaining(progressState.timeRemaining || ''))}</span>
                </div>
            </div>
            <div style="width: 100%; height: 8px; background: var(--bg-input); border-radius: 4px; overflow: hidden;">
                <div id="progress-bar-fill" style="width: ${progressState.progress || 0}%; height: 100%; background: linear-gradient(90deg, #6366f1 0%, #a855f7 100%); transition: width 0.3s ease;">
                    ${progressState.isGenerating ? '<div class="progress-bar-pulse"></div>' : ''}
                </div>
            </div>
        </div>
      </div>
      
      <div class="action-row" style="margin-top: 2rem;">
        <button class="btn btn-back" onclick="window.prevGamePlanStep()" ${progressState.isGenerating ? 'disabled' : ''}>${ui.back}</button>
        <button class="btn btn-start-workflow" onclick="window.startJobManagerWorkflow()" 
            style="display: ${progressState.isGenerating ? 'none' : 'inline-block'};">
            ${ui.startWorkflow}
        </button>
      </div>
  </div>
  `;
}

function renderStep3() {
  const ui = getGamePlanUiText();
  const modelLabel = selectedModel === 'b2b-agency' ? ui.modelLabelAgency : ui.modelLabelSaas;
  // Step 3: Results with 3 Tabbed Sections
  const result = sanitizeDeep(gamePlanData.result || {});
  const marketResearch = result.market_research || {};
  const psychoanalysis = result.psychoanalysis || {};
  const creativeBrief = result.creative_brief || {};

  // Default to first tab
  const activeTab = window.gamePlanActiveTab || 'market-research';

  return `
  <div class="growth-strategy-page growth-strategy-results">
      <header class="growth-strategy-header">
        <span class="growth-strategy-icon">&#x1F3AF;</span>
        <h1>${ui.step3Title}</h1>
        <p>${ui.step3SubtitlePrefix} <strong>${modelLabel}</strong></p>
      </header>
      
      <!-- Section Tabs -->
      <div class="gp-tabs">
        <button class="gp-tab ${activeTab === 'market-research' ? 'active' : ''}" 
                onclick="window.switchGamePlanTab('market-research')">
          &#x1F4CA; ${ui.tabMarketResearch}
        </button>
        <button class="gp-tab ${activeTab === 'psychoanalysis' ? 'active' : ''}" 
                onclick="window.switchGamePlanTab('psychoanalysis')">
          &#x1F9E0; ${ui.tabPsychoanalysis}
        </button>
        <button class="gp-tab ${activeTab === 'creative-brief' ? 'active' : ''}" 
                onclick="window.switchGamePlanTab('creative-brief')">
          &#x1F4DD; ${ui.tabCreativeBrief}
        </button>
        <button class="gp-tab ${activeTab === 'content-ideas' ? 'active' : ''}" 
                onclick="window.switchGamePlanTab('content-ideas')">
          &#x1F3AC; ${ui.tabContentIdeas}
        </button>
      </div>
      
      <!-- Tab Content -->
      <div class="gp-tab-content">
        ${activeTab === 'market-research' ? renderMarketResearchSection(marketResearch) : ''}
        ${activeTab === 'psychoanalysis' ? renderPsychoanalysisSection(psychoanalysis) : ''}
        ${activeTab === 'creative-brief' ? renderCreativeBriefSection(creativeBrief) : ''}
        ${activeTab === 'content-ideas' ? renderContentIdeasSection() : ''}
      </div>
      
      <div class="action-row results-actions">
        <button class="btn btn-back" onclick="window.resetGamePlan()">${ui.startOver}</button>
      </div>
  </div>
  `;
}

// Tab switching
window.gamePlanActiveTab = 'market-research';
window.switchGamePlanTab = function (tab) {
  window.gamePlanActiveTab = tab;
  render();
};

// Export Toolbar Component
function renderExportToolbar(sectionName, sectionData) {
  const ui = getGamePlanUiText();
  const isPolish = getAppLanguage() === 'pl';
  const googleDocsLabel = isPolish ? 'Dokumenty Google' : 'Google Docs';
  return `
    <div class="export-toolbar">
      <span class="export-label">${ui.exportLabel}</span>
      <button class="export-btn" onclick="window.copySection('${sectionName}')" title="${ui.copyClipboardTitle}">
        &#x1F4CB; ${ui.copy}
      </button>
      <button class="export-btn" onclick="window.downloadSectionTXT('${sectionName}')" title="${ui.downloadTxtTitle}">
        &#x1F4DD; TXT
      </button>
      <button class="export-btn" onclick="window.downloadSectionPDF('${sectionName}')" title="${ui.downloadPdfTitle}">
        &#x1F4C4; PDF
      </button>
      <button class="export-btn" onclick="window.openInGoogleDocs('${sectionName}')" title="${ui.openGoogleDocsTitle}">
        &#x1F4E4; ${googleDocsLabel}
      </button>
    </div>
  `;
}

// Render helper: List with fallback
function renderList(items, fallback = null) {
  const fallbackLabel = fallback || getGamePlanUiText().notAvailableLabel;
  if (!items || items.length === 0) return `<span class="text-muted">${escapeHtml(fallbackLabel)}</span>`;
  const formatListItem = (value) => {
    const raw = typeof value === 'string' ? value : escapeHtml(JSON.stringify(value));
    return raw
      .replace(/â€˘\s*/g, '')
      .replace(/^\s*(?:â€˘|•|\*|-)\s*/g, '')
      .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
      .replace(/__(.+?)__/g, '<strong>$1</strong>');
  };
  return `<ul class="gp-list">${items.map(item => `<li>${formatListItem(item)}</li>`).join('')}</ul>`;
}

function localizeObjectKey(key) {
  const fallback = key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
  if (getAppLanguage() !== 'pl') {
    return fallback;
  }

  const map = {
    religious: 'Religijne',
    political: 'Polityczne',
    social: 'Społeczne',
    economic: 'Ekonomiczne',
    demographic: 'Demograficzne',
    demographics: 'Demografia',
    financial_language: 'Język finansowy',
    program_experience_language: 'Język doświadczeń programu',
    execution_tools_language: 'Język narzędzi wykonawczych',
    tone_markers: 'Wskaźniki tonu',
    common_biases: 'Najczęstsze błędy poznawcze'
  };

  return map[key] || fallback;
}

// Render helper: Object as definition list
function renderObject(obj, fallback = null) {
  const fallbackLabel = fallback || getGamePlanUiText().notAvailableLabel;
  if (!obj || Object.keys(obj).length === 0) return `<span class="text-muted">${escapeHtml(fallbackLabel)}</span>`;
  return `<dl class="gp-dl">${Object.entries(obj).map(([k, v]) => `
    <dt>${escapeHtml(localizeObjectKey(k))}</dt>
    <dd>${typeof v === 'string' ? v : Array.isArray(v) ? renderList(v) : escapeHtml(JSON.stringify(v))}</dd>
  `).join('')}</dl>`;
}

// ============ SECTION 1: MARKET RESEARCH ============
function renderMarketResearchSection(data) {
  const ui = getGamePlanUiText();
  if (data.error) {
    return `<div class="gp-section-error">&#x26A0; ${data.error}</div>`;
  }
  const audience = data.audience || {};
  const solutions = data.existing_solutions || {};
  const product = data.your_product || {};
  const notAnalyzed = ui.notAnalyzed;

  return `
    <div class="gp-section" id="section-market-research">
      ${renderExportToolbar('market-research')}
      
      <h2>&#x1F4CA; ${ui.marketResearchTitle}</h2>
      
      <div class="gp-subsection">
        <h3>&#x1F464; ${ui.yourAudience}</h3>
        <div class="gp-grid-2">
          <div class="gp-block">
            <h4>${ui.demographics}</h4>
            <p><strong>${ui.genderMix}:</strong> ${audience.gender_mix || notAnalyzed}</p>
            <p><strong>${ui.ageRange}:</strong> ${audience.age_range || notAnalyzed}</p>
            <p><strong>${ui.idealClientDescription}:</strong> ${audience.ideal_client_description || notAnalyzed}</p>
          </div>
          <div class="gp-block">
            <h4>${ui.attitudes}</h4>
            ${renderObject(audience.attitudes)}
          </div>
        </div>
        <div class="gp-grid-2">
          <div class="gp-block">
            <h4>${ui.desires}</h4>
            ${renderList(audience.desires)}
          </div>
          <div class="gp-block">
            <h4>${ui.fears}</h4>
            ${renderList(audience.fears)}
          </div>
        </div>
        <div class="gp-grid-2">
          <div class="gp-block">
            <h4>${ui.currentIdentity}</h4>
            <p>${audience.current_identity || notAnalyzed}</p>
          </div>
          <div class="gp-block">
            <h4>${ui.desiredIdentity}</h4>
            <p>${audience.desired_identity || notAnalyzed}</p>
          </div>
        </div>
        <div class="gp-block">
          <h4>${ui.perceivedObstacles}</h4>
          <p>${audience.perceived_obstacles || notAnalyzed}</p>
        </div>
        <div class="gp-block">
          <h4>${ui.lifeBeliefs}</h4>
          <p>${audience.life_beliefs || notAnalyzed}</p>
        </div>
      </div>
      
      <div class="gp-subsection">
        <h3>&#x1F501; ${ui.existingSolutionsAnalysis}</h3>
        <div class="gp-grid-2">
          <div class="gp-block">
            <h4>${ui.productsTried}</h4>
            ${renderList(solutions.products_tried)}
          </div>
          <div class="gp-block">
            <h4>${ui.successes}</h4>
            ${renderList(solutions.successes)}
          </div>
        </div>
        <div class="gp-grid-2">
          <div class="gp-block">
            <h4>${ui.failures}</h4>
            ${renderList(solutions.failures)}
          </div>
          <div class="gp-block">
            <h4>${ui.horrorStories}</h4>
            <p>${solutions.horror_stories || ui.noneDocumented}</p>
          </div>
        </div>
        <div class="gp-block">
          <h4>${ui.marketBelief}</h4>
          <p>${solutions.market_belief || notAnalyzed}</p>
        </div>
        <div class="gp-block">
          <h4>${ui.gapAnalysis}</h4>
          <p>${solutions.gap_analysis || notAnalyzed}</p>
        </div>
      </div>
      
      <div class="gp-subsection">
        <h3>&#x2728; ${ui.yourProduct}</h3>
        <div class="gp-block">
          <h4>${ui.uniqueDifferentiators}</h4>
          ${renderList(product.unique_differentiators)}
        </div>
        <div class="gp-block">
          <h4>${ui.interestingFacts}</h4>
          ${renderList(product.interesting_facts)}
        </div>
        <div class="gp-block">
          <h4>${ui.customerTestimonialThemes}</h4>
          <p>${product.customer_testimonials_themes || notAnalyzed}</p>
        </div>
        <div class="gp-block">
          <h4>${ui.competitiveAdvantages}</h4>
          <p>${product.competitive_advantages || notAnalyzed}</p>
        </div>
        <div class="gp-block highlight">
          <h4>${ui.positioningStatement}</h4>
          <p class="highlight-text">${product.positioning_statement || ui.notDefined}</p>
        </div>
      </div>
      
      <!-- Market Trends removed as requested -->
    </div>
  `;
}

// ============ SECTION 2: PSYCHOANALYSIS ============
function renderPsychoanalysisSection(data) {
  const isPolish = getAppLanguage() === 'pl';
  const txt = (pl, en) => (isPolish ? pl : en);
  const ui = getGamePlanUiText();
  const notAnalyzed = ui.notAnalyzed;
  if (data.error) {
    return `<div class="gp-section-error">&#x26A0; ${data.error}<p class="error-hint">${txt('Prześlij transkrypcje rozmów sprzedażowych, aby uruchomić tę analizę.', 'Upload sales call transcripts to enable this analysis.')}</p></div>`;
  }
  const prospects = data.individual_prospect_analysis || [];
  const biases = data.cognitive_biases || {};
  const phrases = data.common_phrases || {};
  const quotes = data.correlating_quotes || {};
  const crossPersona = data.cross_persona_insights || {};

  return `
    <div class="gp-section" id="section-psychoanalysis">
      ${renderExportToolbar('psychoanalysis')}
      
      <h2>&#x1F9E0; ${ui.tabPsychoanalysis}</h2>
      
      <div class="gp-subsection">
        <h3>&#x1F501; ${txt('Powtarzające się motywy', 'Recurring Themes')}</h3>
        ${renderList(data.recurring_themes)}
      </div>
      
      <div class="gp-subsection">
        <h3>&#x1F91D; ${txt('Wspólne cechy prospektów', 'Prospect Commonalities')}</h3>
        ${renderList(data.prospect_commonalities)}
      </div>
      
      <div class="gp-subsection">
        <h3>&#x1F630; ${txt('30 problemów, z którymi się utożsamiają', '30 Problems They Relate To')}</h3>
        <div class="gp-problems-grid">
          ${renderList(data.problems_they_relate_to)}
        </div>
      </div>
      
      <div class="gp-subsection">
        <h3>&#x1F464; ${txt('Analiza indywidualnych prospektów', 'Individual Prospect Analysis')}</h3>
        <div class="gp-prospects">
          ${prospects.map((p, i) => `
            <div class="gp-prospect-card">
              <h4>${p.name || `${txt('Prospekt', 'Prospect')} ${i + 1}`}</h4>
              <div class="prospect-details">
                ${p.core_identity ? `<p><strong>${txt('Tożsamość bazowa', 'Core Identity')}:</strong> ${p.core_identity}</p>` : ''}
                ${p.dominant_archetype ? `<p><strong>${txt('Archetyp', 'Archetype')}:</strong> ${p.dominant_archetype}</p>` : ''}
                ${p.primary_motivations ? `<p><strong>${txt('Motywacje', 'Motivations')}:</strong> ${p.primary_motivations}</p>` : ''}
                ${p.decision_style ? `<p><strong>${txt('Styl podejmowania decyzji', 'Decision Style')}:</strong> ${p.decision_style}</p>` : ''}
                ${p.buying_triggers ? `<p><strong>${txt('Triggery zakupowe', 'Buying Triggers')}:</strong> ${p.buying_triggers}</p>` : ''}
                ${p.fears_and_objections ? `<p><strong>${txt('Obawy / Obiekcje', 'Fears/Objections')}:</strong> ${p.fears_and_objections}</p>` : ''}
                ${p.messaging_that_lands ? `<p class="highlight-text"><strong>${txt('Komunikat, który działa', 'Messaging')}:</strong> "${p.messaging_that_lands}"</p>` : ''}
              </div>
            </div>
          `).join('')}
        </div>
      </div>
      
      <div class="gp-subsection">
        <h3>&#x1F9E9; ${txt('Błędy poznawcze', 'Cognitive Biases')}</h3>
        ${renderList(biases.common_biases)}
        ${biases.bias_by_prospect_type ? `<p><strong>${txt('Wg typu prospekta', 'By Prospect Type')}:</strong> ${biases.bias_by_prospect_type}</p>` : ''}
      </div>
      
      <div class="gp-subsection">
        <h3>&#x1F4AC; ${txt('Najczęstsze sformułowania', 'Common Phrases')}</h3>
        <div class="gp-grid-2">
          <div class="gp-block">
            <h4>${txt('Język finansowy', 'Financial Language')}</h4>
            ${renderList(phrases.financial_language)}
          </div>
          <div class="gp-block">
            <h4>${txt('Język doświadczeń programu', 'Experience Language')}</h4>
            ${renderList(phrases.program_experience_language)}
          </div>
        </div>
        <div class="gp-grid-2">
          <div class="gp-block">
            <h4>${txt('Język narzędzi wykonawczych', 'Execution/Tools Language')}</h4>
            ${renderList(phrases.execution_tools_language)}
          </div>
          <div class="gp-block">
            <h4>${txt('Wskaźniki tonu', 'Tone Markers')}</h4>
            ${renderList(phrases.tone_markers)}
          </div>
        </div>
        ${phrases.theme_summary ? `<p><strong>${txt('Podsumowanie motywów', 'Theme Summary')}:</strong> ${phrases.theme_summary}</p>` : ''}
      </div>
      
      <div class="gp-subsection">
        <h3>&#x1F4D8; ${txt('Cytaty potwierdzające', 'Correlating Quotes')}</h3>
        <div class="gp-quotes">
          ${quotes.desire_for_expert_access ? `<div class="quote-category"><h4>${txt('Potrzeba dostępu do eksperta', 'Desire for Expert Access')}</h4>${renderList(quotes.desire_for_expert_access)}</div>` : ''}
          ${quotes.roi_focus ? `<div class="quote-category"><h4>${txt('Nastawienie na ROI', 'ROI Focus')}</h4>${renderList(quotes.roi_focus)}</div>` : ''}
          ${quotes.past_burns ? `<div class="quote-category"><h4>${txt('Negatywne doświadczenia z przeszłości', 'Past Burns')}</h4>${renderList(quotes.past_burns)}</div>` : ''}
          ${quotes.urgency_readiness ? `<div class="quote-category"><h4>${txt('Pilność i gotowość', 'Urgency & Readiness')}</h4>${renderList(quotes.urgency_readiness)}</div>` : ''}
        </div>
      </div>
      
      <div class="gp-subsection highlight">
        <h3>&#x1F3AF; ${txt('Wnioski między personami', 'Cross-Persona Insights')}</h3>
        <p><strong>${txt('Dlaczego kupują', 'Why They Buy')}:</strong> ${crossPersona.why_they_buy || notAnalyzed}</p>
        <div class="gp-grid-2">
          <div class="gp-block">
            <h4>${txt('Uniwersalne triggery', 'Universal Triggers')}</h4>
            ${renderList(crossPersona.universal_triggers)}
          </div>
          <div class="gp-block">
            <h4>${txt('Uniwersalne obiekcje', 'Universal Objections')}</h4>
            ${renderList(crossPersona.universal_objections)}
          </div>
        </div>
      </div>
    </div>
  `;
}

// ============ SECTION 3: CREATIVE BRIEF ============
function renderCreativeBriefSection(data) {
  const isPolish = getAppLanguage() === 'pl';
  const txt = (pl, en) => (isPolish ? pl : en);
  const ui = getGamePlanUiText();
  if (data.error) {
    return `<div class="gp-section-error">&#x26A0; ${data.error}</div>`;
  }
  const promise = data.promise || {};
  const problem = data.problem || {};
  const solution = data.solution || {};
  const salesArg = data.sales_argument || {};
  const avatar = data.primary_avatar || {};
  const journey = data.client_journey || {};
  const guarantee = data.guarantee || {};
  const tone = data.tone_and_style || {};
  const pillars = data.content_pillars || [];
  const videoIdeas = data.video_ideas || [];

  return `
    <div class="gp-section" id="section-creative-brief">
      ${renderExportToolbar('creative-brief')}
      
      <h2>&#x1F4DD; ${ui.tabCreativeBrief}</h2>
      <p class="offer-name">${data.offer_name || txt('Twoja oferta', 'Your Offer')}</p>
      
      <div class="gp-subsection">
        <h3>&#x1F3AF; ${txt('Obietnica', 'The Promise')}</h3>
        <p class="highlight-text">${promise.main_promise || ui.notDefined}</p>
        ${promise.supporting_promises ? `<h4>${txt('Obietnice wspierające', 'Supporting Promises')}</h4>${renderList(promise.supporting_promises)}` : ''}
      </div>
      
      <div class="gp-subsection">
        <h3>&#x1F630; ${txt('Problem', 'The Problem')}</h3>
        <p><strong>${txt('Główny problem', 'Core Problem')}:</strong> ${problem.core_problem || ui.notDefined}</p>
        ${problem.manifestations ? `<h4>${txt('Jak to się objawia', 'How It Shows Up')}</h4>${renderList(problem.manifestations)}` : ''}
        ${problem.cost_of_inaction ? `<p><strong>${txt('Koszt braku działania', 'Cost of Inaction')}:</strong> ${problem.cost_of_inaction}</p>` : ''}
      </div>
      
      <div class="gp-subsection">
        <h3>&#x1F4A1; ${txt('Rozwiązanie', 'The Solution')}</h3>
        <p><strong>${txt('Główne rozwiązanie', 'Core Solution')}:</strong> ${solution.core_solution || ui.notDefined}</p>
        ${solution.mechanism ? `<p><strong>${txt('Mechanizm', 'Mechanism')}:</strong> ${solution.mechanism}</p>` : ''}
        ${solution.why_it_works ? `<p><strong>${txt('Dlaczego to działa', 'Why It Works')}:</strong> ${solution.why_it_works}</p>` : ''}
      </div>
      
      <div class="gp-subsection">
        <h3>&#x1F4D8; ${txt('Argument sprzedażowy', 'Sales Argument')}</h3>
        <p class="highlight-text">${salesArg.main_argument || ui.notDefined}</p>
        ${salesArg.supporting_points ? `<h4>${txt('Argumenty wspierające', 'Supporting Points')}</h4>${renderList(salesArg.supporting_points)}` : ''}
        ${salesArg.objection_handlers ? `<h4>${txt('Odpowiedzi na obiekcje', 'Objection Handlers')}</h4>${renderList(salesArg.objection_handlers)}` : ''}
      </div>
      
      <div class="gp-subsection">
        <h3>&#x2705; ${txt('Powody, by uwierzyć', 'Reasons to Believe')}</h3>
        ${renderList(data.reasons_to_believe)}
      </div>
      
      <div class="gp-subsection">
        <h3>&#x1F464; ${txt('Główny avatar klienta', 'Primary Avatar')}</h3>
        <p>${avatar.description || ui.notDefined}</p>
        ${avatar.dream_outcome ? `<p><strong>${txt('Wymarzony rezultat', 'Dream Outcome')}:</strong> ${avatar.dream_outcome}</p>` : ''}
        ${avatar.obstacles ? `<h4>${txt('Przeszkody', 'Obstacles')}</h4>${renderList(avatar.obstacles)}` : ''}
        ${avatar.key_bullets ? `<h4>${txt('Kluczowe korzyści', 'Key Benefits')}</h4>${renderList(avatar.key_bullets)}` : ''}
        ${avatar.deliverables_they_want ? `
          <h4>${txt('Rezultaty dostarczane klientowi', 'Deliverables')}</h4>
          <table class="gp-table">
            <thead><tr><th>${txt('Element', 'Feature')}</th><th>${txt('Korzyść', 'Benefit')}</th></tr></thead>
            <tbody>
              ${avatar.deliverables_they_want.map(d => `<tr><td>${d.feature || ''}</td><td>${d.benefit || ''}</td></tr>`).join('')}
            </tbody>
          </table>
        ` : ''}
      </div>
      
      <div class="gp-subsection">
        <h3>&#x1F5FA; ${txt('Ścieżka klienta', 'Client Journey')}</h3>
        <div class="gp-journey">
          ${journey.week_1 ? `<div class="journey-week"><span class="week-label">${txt('Tydzień 1', 'Week 1')}</span><p>${journey.week_1}</p></div>` : ''}
          ${journey.week_2 ? `<div class="journey-week"><span class="week-label">${txt('Tydzień 2', 'Week 2')}</span><p>${journey.week_2}</p></div>` : ''}
          ${journey.week_3 ? `<div class="journey-week"><span class="week-label">${txt('Tydzień 3', 'Week 3')}</span><p>${journey.week_3}</p></div>` : ''}
          ${journey.week_4 ? `<div class="journey-week"><span class="week-label">${txt('Tydzień 4+', 'Week 4+')}</span><p>${journey.week_4}</p></div>` : ''}
        </div>
        ${journey.transformation_arc ? `<p><strong>${txt('Łuk transformacji', 'Transformation Arc')}:</strong> ${journey.transformation_arc}</p>` : ''}
      </div>
      
      <div class="gp-subsection">
        <h3>&#x1F6E1; ${txt('Gwarancja', 'Guarantee')}</h3>
        <p class="highlight-text">${guarantee.guarantee_statement || ui.notDefined}</p>
        ${guarantee.risk_reversal ? `<p><strong>${txt('Odwrócenie ryzyka', 'Risk Reversal')}:</strong> ${guarantee.risk_reversal}</p>` : ''}
      </div>
      
      <div class="gp-subsection highlight">
        <h3>&#x1F3A4; ${txt('Finalny argument sprzedażowy', 'Final Sales Argument')}</h3>
        <p class="highlight-text large">${data.final_sales_argument || ui.notDefined}</p>
      </div>
      
      <!-- Tone & Style and Content Pillars sections removed as requested -->
    </div>
  `;
}

// ============ EXPORT FUNCTIONS ============

// Get section content as plain text
function getSectionAsText(sectionName) {
  const ui = getGamePlanUiText();
  const result = gamePlanData.result || {};
  let data, title;

  if (sectionName === 'market-research') {
    data = result.market_research || {};
    title = ui.marketResearchTitle.toUpperCase();
  } else if (sectionName === 'psychoanalysis') {
    data = result.psychoanalysis || {};
    title = ui.tabPsychoanalysis.toUpperCase();
  } else if (sectionName === 'creative-brief') {
    data = result.creative_brief || {};
    title = ui.tabCreativeBrief.toUpperCase();
  } else {
    return '';
  }

  // Convert JSON to readable text
  return formatDataAsText(title, normalizeTextExportData(data));
}

function normalizeTextExportData(input) {
  if (Array.isArray(input)) {
    return input.map((item) => normalizeTextExportData(item));
  }

  if (input && typeof input === 'object') {
    const out = {};
    Object.entries(input).forEach(([key, value]) => {
      out[key] = normalizeTextExportData(value);
    });
    return out;
  }

  if (typeof input === 'string') {
    const decoded = decodeHtmlEntities(input);
    return decoded
      .replace(/<br\s*\/?>/gi, '\n')
      .replace(/<\/p>/gi, '\n')
      .replace(/<[^>]+>/g, '')
      .trim();
  }

  return input;
}

function formatDataAsText(title, data, indent = 0) {
  const pad = '  '.repeat(indent);
  let text = indent === 0 ? `${'='.repeat(50)}\n${title}\n${'='.repeat(50)}\n\n` : '';

  for (const [key, value] of Object.entries(data)) {
    const label = key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());

    if (Array.isArray(value)) {
      text += `${pad}${label}:\n`;
      value.forEach((item, i) => {
        if (typeof item === 'object') {
          text += `${pad}  ${i + 1}. ${JSON.stringify(item)}\n`;
        } else {
          text += `${pad}  - ${item}\n`;
        }
      });
      text += '\n';
    } else if (typeof value === 'object' && value !== null) {
      text += `${pad}${label}:\n`;
      text += formatDataAsText('', value, indent + 1);
    } else {
      text += `${pad}${label}: ${value}\n\n`;
    }
  }

  return text;
}

window.copySection = function (sectionName) {
  const text = getSectionAsText(sectionName);
  const ui = getGamePlanUiText();
  navigator.clipboard.writeText(text).then(() => {
    alert(ui.copySuccess);
  }).catch(err => {
    console.error('Copy failed:', err);
    alert(ui.copyFailed);
  });
};

window.downloadSectionTXT = function (sectionName) {
  const text = getSectionAsText(sectionName);
  const blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `business-growth-strategy-${sectionName}-${new Date().toISOString().slice(0, 10)}.txt`;
  a.click();
  URL.revokeObjectURL(url);
};

window.downloadSectionPDF = function (sectionName) {
  const ui = getGamePlanUiText();
  const text = getSectionAsText(sectionName);
  if (!text.trim()) {
    alert(getGamePlanUiText().sectionNotFound);
    return;
  }

  const sectionLabels = {
    'market-research': ui.marketResearchTitle,
    psychoanalysis: ui.tabPsychoanalysis,
    'creative-brief': ui.tabCreativeBrief
  };
  const sectionLabel = sectionLabels[sectionName] || sectionName;
  const exportRoot = document.createElement('div');
  const printable = document.createElement('div');
  const heading = document.createElement('h1');
  const pre = document.createElement('pre');

  exportRoot.style.position = 'fixed';
  exportRoot.style.left = '-10000px';
  exportRoot.style.top = '0';
  exportRoot.style.width = '800px';
  exportRoot.style.pointerEvents = 'none';

  printable.style.background = '#ffffff';
  printable.style.color = '#111111';
  printable.style.padding = '32px';
  printable.style.fontFamily = 'Arial, sans-serif';
  printable.style.fontSize = '12px';
  printable.style.lineHeight = '1.55';
  printable.style.whiteSpace = 'normal';

  heading.textContent = sectionLabel;
  heading.style.margin = '0 0 16px 0';
  heading.style.fontSize = '24px';
  heading.style.fontWeight = '700';

  pre.textContent = text;
  pre.style.margin = '0';
  pre.style.whiteSpace = 'pre-wrap';
  pre.style.wordBreak = 'break-word';
  pre.style.fontFamily = 'Arial, sans-serif';

  printable.appendChild(heading);
  printable.appendChild(pre);
  exportRoot.appendChild(printable);
  document.body.appendChild(exportRoot);

  const opt = {
    margin: [10, 10, 10, 10],
    filename: `BusinessGrowthStrategy-${sectionName}-${new Date().toISOString().slice(0, 10)}.pdf`,
    image: { type: 'jpeg', quality: 0.95 },
    html2canvas: { scale: 1.7, useCORS: true, backgroundColor: '#ffffff' },
    jsPDF: { unit: 'mm', format: 'a4', orientation: 'portrait' }
  };

  html2pdf()
    .set(opt)
    .from(printable)
    .save()
    .finally(() => {
      exportRoot.remove();
    });
};

// ============ SECTION 4: CONTENT IDEAS (Interactive Workflow) ============

function renderContentIdeasSection() {
  const ui = getGamePlanUiText();
  if (contentIdeasStep === 1) {
    // Auto-generate if empty
    if (generatedTitles.length === 0 && !isGenerating) {
      setTimeout(() => window.generateContentTitles(), 100);
      return `
        <div class="gp-section loading-state">
           <span class="spinner large"></span>
           <h3>${ui.contentIdeasLoadingTitle}</h3>
           <p>${ui.contentIdeasLoadingDesc}</p>
        </div>
      `;
    }
    return renderTitlesStep();
  } else if (contentIdeasStep === 2) {
    return renderChaptersStep();
  } else if (contentIdeasStep === 3) {
    return renderScriptStep();
  }
}

// --- STEP 1: TITLE GENERATION ---
function renderTitlesStep() {
  const ui = getGamePlanUiText();
  const safeTitles = sanitizeDeep(generatedTitles || []);
  const safeSelectedTitle = sanitizeDeep(selectedTitle || {});

  if (generatedTitles.length === 0 && !isGenerating) {
    return `
      <div class="gp-section content-ideas-empty">
        <div class="empty-state">
          <span class="empty-icon">&#x1F3AC;</span>
          <h3>${ui.contentIdeasEmptyTitle}</h3>
          <p>${ui.contentIdeasEmptyDesc}</p>
          <button class="btn btn-primary" onclick="window.generateContentTitles()">
            &#x2728; ${ui.generateFiveTitles}
          </button>
        </div>
      </div>
    `;
  }

  return `
    <div class="gp-section" id="section-content-titles">
      <div class="section-header-row">
        <h2>&#x1F3AC; ${ui.titlesStepHeading}</h2>
        <button class="btn btn-subtle" onclick="window.generateContentTitles()" ${isGenerating ? 'disabled' : ''}>
          ${isGenerating ? `<span class="spinner"></span> ${ui.regenerating}` : `&#x1F501; ${ui.generateFiveNew}`}
        </button>
      </div>
      
      <p class="section-subtitle">${ui.titlesStepSubtitle}</p>
      
      <div class="titles-grid">
        ${safeTitles.map((item, i) => `
          <div class="title-card ${selectedTitleIndex === i ? 'selected' : ''}" onclick="window.selectVideoTitle(${i})">
            <div class="title-header">
              <span class="pillar-tag">${item.content_pillar || ui.pillarValue}</span>
              <button class="btn-icon-bg" onclick="event.stopPropagation(); window.generateSimilarTitle(${i})" title="${ui.generateSimilarTooltip}">
                &#x1F501;
              </button>
            </div>
            <h4>${item.title}</h4>
            <p>${item.concept}</p>
            <div class="title-footer">
              <span class="target-tag">&#x1F464; ${item.target_audience || ui.idealClient}</span>
              <button class="btn btn-select-title">${ui.selectTitle} &rarr;</button>
            </div>
          </div>
        `).join('')}
      </div>

      ${selectedTitle ? `
        <div class="selection-footer">
          <div class="selection-info">
            <span>${ui.selectedLabel}: <strong>${safeSelectedTitle.title || ''}</strong></span>
          </div>
          <button class="btn btn-primary" onclick="window.confirmVideoTitle()">
            ${ui.nextGenerateChapters} &rarr;
          </button>
        </div>
      ` : ''}
    </div>
  `;
}

// --- STEP 2: CHAPTER STRUCTURE ---
function renderChaptersStep() {
  const ui = getGamePlanUiText();
  if (!chapterStructure && isGenerating) {
    return `<div class="gp-section loading-state"><span class="spinner large"></span><p>${ui.chaptersLoading}</p></div>`;
  }

  const chapters = sanitizeDeep(chapterStructure?.chapters || []);
  const safeSelectedTitle = sanitizeDeep(selectedTitle || {});

  return `
    <div class="gp-section" id="section-chapters">
      <div class="section-header-row">
        <button class="btn-icon-back" onclick="window.setContentIdeasStep(1)">${ui.backToTitles}</button>
        <h2>&#x1F3AC; ${ui.chaptersStepHeading}</h2>
        <button class="btn btn-subtle" onclick="window.generateChapterStructure()" ${isGenerating ? 'disabled' : ''}>
          &#x1F501; ${ui.regenerate}
        </button>
      </div>

      <div class="selected-context">
        <span class="context-label">${ui.videoTitleLabel}:</span>
        <span class="context-value">${safeSelectedTitle.title || ''}</span>
      </div>

      <div class="chapters-workflow">
        <div class="chapters-sidebar">
          <div class="chapters-list">
            ${chapters.map((ch, i) => `
              <div class="chapter-item ${currentChapterIndex === i ? 'active' : ''}" onclick="window.setCurrentChapter(${i})">
                <span class="chapter-num">${ch.number || i + 1}</span>
                <span class="chapter-title">${ch.title}</span>
                <span class="chapter-time">${ch.duration_minutes}m</span>
              </div>
            `).join('')}
          </div>
          <button class="btn btn-primary full-width mt-4" onclick="window.approveChapterStructure()">
            ${ui.approveStartScripting}
          </button>
        </div>

        <div class="chapter-detail">
          ${chapters[currentChapterIndex] ? `
            <div class="detail-card">
              <div class="detail-header">
                <h3>${ui.chapterLabel} ${chapters[currentChapterIndex].number}: ${chapters[currentChapterIndex].title}</h3>
                <span class="time-tag">&#x23F1; ${chapters[currentChapterIndex].duration_minutes} min</span>
              </div>
              
              <div class="detail-group">
                <label>${ui.purposeLabel}</label>
                <p>${chapters[currentChapterIndex].purpose}</p>
              </div>

              <div class="detail-group">
                <label>${ui.keyPointsLabel}</label>
                ${renderList(chapters[currentChapterIndex].key_points)}
              </div>

              <div class="detail-group">
                <label>${ui.transitionLabel}</label>
                <p class="text-italic">${chapters[currentChapterIndex].transition}</p>
              </div>
            </div>
          ` : ''}
        </div>
      </div>
    </div>
  `;
}

// --- STEP 3: SCRIPT GENERATION ---
function renderScriptStep() {
  const ui = getGamePlanUiText();
  const chapters = sanitizeDeep(chapterStructure?.chapters || []);
  const safeScriptChapters = sanitizeDeep(scriptChapters || {});
  const currentChapter = chapters[currentChapterIndex];
  const scriptData = safeScriptChapters[currentChapterIndex];

  return `
    <div class="gp-section" id="section-script">
      <div class="section-header-row">
        <button class="btn-icon-back" onclick="window.setContentIdeasStep(2)">${ui.backToChapters}</button>
        <h2>&#x1F3AC; ${ui.scriptStepHeading}</h2>
        <div class="script-progress">
          ${ui.chapterWord} ${currentChapterIndex + 1} ${ui.ofWord} ${chapters.length}
        </div>
      </div>

      <div class="script-workflow">
        <div class="script-sidebar">
          <h3>${ui.progressLabel}</h3>
          <div class="script-nav">
             ${chapters.map((ch, i) => `
               <div class="script-nav-item ${currentChapterIndex === i ? 'active' : ''} ${safeScriptChapters[i] ? 'done' : ''}" 
                    onclick="window.setCurrentChapter(${i})">
                 <span class="nav-icon">${safeScriptChapters[i] ? '&#x2705;' : '-'}</span>
                 <span class="nav-title">${ch.title}</span>
               </div>
             `).join('')}
          </div>
          <button class="btn btn-export full-width mt-4" onclick="window.exportFinalScript()">
            &#x1F4E5; ${ui.exportFullScript}
          </button>
          <button class="btn btn-primary full-width mt-2" onclick="window.saveToScriptPipeline()">
            &#x1F4DD; ${ui.saveToPipeline}
          </button>
          <div class="mt-4 pt-4" style="border-top: 1px solid var(--border-subtle);">
            <button class="btn btn-subtle full-width" onclick="window.resetScriptWorkflow()">
              &#x1F501; ${ui.startNewScript}
            </button>
            
            ${gamePlanData.projectScripts && gamePlanData.projectScripts.length > 1 ? `
              <div class="mt-4">
                <h4 style="font-size: 0.8rem; color: var(--text-muted); margin-bottom: 8px;">${ui.previousScripts}</h4>
                <div style="display: flex; flex-direction: column; gap: 6px;">
                  ${gamePlanData.projectScripts.map((s, idx) => `
                    <button class="btn btn-sm btn-outline" style="text-align: left; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" onclick="window.loadProjectScriptByIndex(${idx})">
                      ${ui.fileLabel}: ${escapeHtml((s.title || '').substring(0, 25))}...
                    </button>
                  `).join('')}
                </div>
              </div>
            ` : ''}
          </div>
        </div>

        <div class="script-main">
          ${!scriptData && isGenerating ? `
            <div class="script-loading">
              <span class="spinner large"></span>
              <p>${isGeneratingEntireScript ? ui.generatingEntireScript : ui.writingOptionsFor} <strong>${currentChapter.title}</strong>...</p>
              <span class="time-estimate">&#x23F1; ${ui.estimatedTime}</span>
            </div>
          ` : scriptData ? `
            ${selectedScriptOptions[currentChapterIndex] ? `
              <!-- LOCKED STATE: Show only selected option -->
              <div class="script-single">
                <div class="script-option full-width locked">
                  <header>
                    <h4>${selectedScriptOptions[currentChapterIndex] === 'a' ? scriptData.option_a.style : scriptData.option_b.style}</h4>
                    <span class="saved-badge">&#x2705; ${ui.savedBadge}</span>
                  </header>
                  <textarea class="script-editor" onchange="window.updateScriptText(${currentChapterIndex}, '${selectedScriptOptions[currentChapterIndex] === 'a' ? 'option_a' : 'option_b'}', this.value)">${selectedScriptOptions[currentChapterIndex] === 'a' ? scriptData.option_a.script : scriptData.option_b.script}</textarea>
                </div>
              </div>
            ` : `
              <!-- UNLOCKED STATE: Show both options -->
              <div class="script-comparison">
                <div class="script-option">
                  <header>
                    <h4>${scriptData.option_a.style}</h4>
                    <button class="btn btn-subtle btn-sm" onclick="window.selectScriptOption('a')">${ui.useThis}</button>
                  </header>
                  <textarea class="script-editor" onchange="window.updateScriptText(${currentChapterIndex}, 'option_a', this.value)">${scriptData.option_a.script}</textarea>
                </div>
                <div class="script-option">
                  <header>
                    <h4>${scriptData.option_b.style}</h4>
                    <button class="btn btn-subtle btn-sm" onclick="window.selectScriptOption('b')">${ui.useThis}</button>
                  </header>
                  <textarea class="script-editor" onchange="window.updateScriptText(${currentChapterIndex}, 'option_b', this.value)">${scriptData.option_b.script}</textarea>
                </div>
              </div>
            `}
          ` : `
            <div class="script-empty">
              <h3>${ui.readyToWriteScript}</h3>
              <p>${ui.readyToWriteScriptDesc}</p>
              <p class="time-estimate">&#x23F1; ${ui.estimatedTime}</p>
              <div style="display: flex; gap: 10px; justify-content: center; flex-wrap: wrap;">
                <button class="btn btn-primary" onclick="window.generateScriptForChapter()">
                  &#x270D; ${ui.writeChapterScript}
                </button>
                <button class="btn btn-subtle" onclick="window.generateEntireScript()">
                  &#x1F4DC; ${ui.writeEntireScript}
                </button>
              </div>
            </div>
          `}
          
          <div class="script-footer">
            <button class="btn btn-back" onclick="window.prevChapter()" ${currentChapterIndex === 0 ? 'disabled' : ''}>
              &larr; ${ui.previousChapter}
            </button>
            <button class="btn btn-primary" onclick="window.nextChapter()" ${currentChapterIndex === chapters.length - 1 ? 'disabled' : ''}>
              ${ui.nextChapter} &rarr;
            </button>
          </div>
        </div>
      </div>
    </div>
  `;
}

// --- CONTENT IDEAS WORKFLOW LOGIC ---

window.setContentIdeasStep = function (step) {
  contentIdeasStep = step;
  render();
};

window.generateContentTitles = async function () {
  isGenerating = true;
  render();
  try {
    const response = await fetch(apiUrl('/api/bgs/generate_titles'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(withAIConfig({ context: gamePlanData.result, language: getGenerationLanguage() }))
    });
    const result = await response.json();
    if (result.success) {
      generatedTitles = result.data.titles;
    }
  } catch (e) {
    console.error(e);
    alert(getGamePlanUiText().failedGenerateTitles);
  } finally {
    isGenerating = false;
    render();
  }
};

window.generateSimilarTitle = async function (index) {
  const original = generatedTitles[index];
  isGenerating = true;
  render();
  try {
    const response = await fetch(apiUrl('/api/bgs/generate_similar_titles'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(withAIConfig({ original_title: original.title, context: gamePlanData.result, language: getGenerationLanguage(), count: 4 }))
    });
    const result = await response.json();
    if (result.success && result.data && result.data.length > 0) {
      // Replace the clicked title + insert new variations after it
      // Keep all other titles
      const before = generatedTitles.slice(0, index);
      const after = generatedTitles.slice(index + 1);
      generatedTitles = [...before, ...result.data, ...after];
    }
  } catch (e) {
    console.error(e);
  } finally {
    isGenerating = false;
    render();
  }
};

window.selectVideoTitle = function (index) {
  selectedTitleIndex = index;
  selectedTitle = generatedTitles[index];
  render();
};

window.confirmVideoTitle = function () {
  contentIdeasStep = 2;
  window.generateChapterStructure();
};

window.generateChapterStructure = async function () {
  isGenerating = true;
  chapterStructure = null;
  render();
  try {
    const response = await fetch(apiUrl('/api/bgs/generate_chapters'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(withAIConfig({ title: selectedTitle.title, context: gamePlanData.result, language: getGenerationLanguage() }))
    });
    const result = await response.json();
    if (result.success) {
      chapterStructure = result.data;
    }
  } catch (e) {
    console.error(e);
    alert(getGamePlanUiText().failedGenerateChapters);
  } finally {
    isGenerating = false;
    render();
  }
};

window.setCurrentChapter = function (index) {
  if (isGenerating) return;
  currentChapterIndex = index;
  render();
};

window.approveChapterStructure = function () {
  contentIdeasStep = 3;
  currentChapterIndex = 0;
  render();
};

window.generateScriptForChapter = async function () {
  if (isGenerating) return;
  const chapters = chapterStructure?.chapters || [];
  const chapter = chapters[currentChapterIndex];

  // Get previous chapter's selected script for continuity
  let previousChapterScript = null;
  if (currentChapterIndex > 0) {
    const prevIndex = currentChapterIndex - 1;
    const prevOption = selectedScriptOptions[prevIndex];
    const prevScriptData = scriptChapters[prevIndex];
    if (prevOption && prevScriptData) {
      const optionKey = prevOption === 'a' ? 'option_a' : 'option_b';
      previousChapterScript = prevScriptData[optionKey]?.script || null;
    }
  }

  isGenerating = true;
  render();
  try {
    const response = await fetch(apiUrl('/api/bgs/generate_script'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(withAIConfig({
        title: selectedTitle.title,
        chapter: chapter,
        context: gamePlanData.result,
        language: getGenerationLanguage(),
        previous_chapter_script: previousChapterScript
      }))
    });
    const result = await response.json();
    if (result.success) {
      scriptChapters[currentChapterIndex] = result.data;
    }
  } catch (e) {
    console.error(e);
    alert(getGamePlanUiText().failedGenerateScript);
  } finally {
    isGenerating = false;
    render();
  }
};

window.generateEntireScript = async function () {
  if (isGenerating) return;
  const chapters = chapterStructure?.chapters || [];
  if (!chapters.length) return;

  const ui = getGamePlanUiText();
  const originalChapterIndex = currentChapterIndex;
  isGenerating = true;
  isGeneratingEntireScript = true;
  render();

  try {
    for (let i = 0; i < chapters.length; i++) {
      if (scriptChapters[i]) {
        continue;
      }

      currentChapterIndex = i;
      render();

      let previousChapterScript = null;
      if (i > 0) {
        const prevIndex = i - 1;
        const prevOption = selectedScriptOptions[prevIndex];
        const prevScriptData = scriptChapters[prevIndex];
        if (prevScriptData) {
          const optionKey = prevOption === 'b' ? 'option_b' : 'option_a';
          previousChapterScript = prevScriptData[optionKey]?.script || null;
        }
      }

      const response = await fetch(apiUrl('/api/bgs/generate_script'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(withAIConfig({
          title: selectedTitle.title,
          chapter: chapters[i],
          context: gamePlanData.result,
          language: getGenerationLanguage(),
          previous_chapter_script: previousChapterScript
        }))
      });
      const result = await response.json();
      if (!result.success) {
        throw new Error(result.error || ui.failedGenerateScript);
      }
      scriptChapters[i] = result.data;
    }
  } catch (e) {
    console.error(e);
    alert(ui.failedGenerateEntireScript);
  } finally {
    isGenerating = false;
    isGeneratingEntireScript = false;
    currentChapterIndex = Math.min(originalChapterIndex, chapters.length - 1);
    render();
  }
};

window.updateScriptText = function (index, option, text) {
  if (scriptChapters[index] && scriptChapters[index][option]) {
    scriptChapters[index][option].script = text;
  }
};

window.selectScriptOption = function (option) {
  // Lock this chapter's selection
  selectedScriptOptions[currentChapterIndex] = option;
  render();
};

window.nextChapter = function () {
  if (isGenerating) return;
  const chapters = chapterStructure?.chapters || [];
  if (currentChapterIndex < chapters.length - 1) {
    currentChapterIndex++;
    render();
  }
};

window.prevChapter = function () {
  if (isGenerating) return;
  if (currentChapterIndex > 0) {
    currentChapterIndex--;
    render();
  }
};

window.exportFinalScript = function () {
  const ui = getGamePlanUiText();
  let fullScript = `${ui.titleExportPrefix}: ${selectedTitle.title}\n\n`;
  const chapters = chapterStructure?.chapters || [];

  chapters.forEach((ch, i) => {
    fullScript += `### ${ui.chapterExportPrefix} ${i + 1}: ${ch.title}\n`;
    const selectedOption = selectedScriptOptions[i];
    const scriptData = scriptChapters[i];

    if (scriptData) {
      if (selectedOption === 'a') {
        fullScript += scriptData.option_a.script + '\n\n';
      } else if (selectedOption === 'b') {
        fullScript += scriptData.option_b.script + '\n\n';
      } else {
        // Default to A if nothing selected
        fullScript += scriptData.option_a.script + '\n\n';
      }
    } else {
      fullScript += `${ui.scriptNotGeneratedYet}\n\n`;
    }
  });

  const blob = new Blob([fullScript], { type: 'text/plain;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `video-script-${selectedTitle.title.slice(0, 20)}.txt`;
  a.click();
  URL.revokeObjectURL(url);
};

window.saveToScriptPipeline = async function () {
  const chapters = chapterStructure?.chapters || [];
  const formattedChapters = chapters.map((ch, i) => {
    const selectedOption = selectedScriptOptions[i];
    const scriptData = scriptChapters[i];
    let finalizedScript = "";

    if (selectedOption === 'a' && scriptData?.option_a) {
      finalizedScript = scriptData.option_a.script;
    } else if (selectedOption === 'b' && scriptData?.option_b) {
      finalizedScript = scriptData.option_b.script;
    } else {
      // Fallback if none selected but generated
      finalizedScript = scriptData?.option_a?.script || scriptData?.option_b?.script || "";
    }

    return {
      title: ch.title,
      script: finalizedScript
    };
  });

  const scriptData = {
    project_id: gamePlanData.id,
    title: (selectedTitle?.title || "Untitled Script").slice(0, 100),
    chapters: formattedChapters,
    status: 'written'
  };

  try {
    const response = await fetch(apiUrl('/api/scripts/save'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(scriptData)
    });
    const result = await response.json();
    if (result.success) {
      if (window.setPage) {
        window.setPage('script-management');
      } else {
        location.assign('/script-management'); // More direct fallback if setPage isn't ready
      }
    } else {
      alert(getGamePlanUiText().failedSaveScriptPrefix + result.error);
    }
  } catch (e) {
    console.error('Failed to save to Script Management:', e);
    alert(getGamePlanUiText().saveScriptPipelineError);
  }
};


window.resetScriptWorkflow = function () {
  if (!confirm(getGamePlanUiText().resetScriptConfirm)) return;

  scriptChapters = {};
  selectedScriptOptions = {};
  currentChapterIndex = 0;
  selectedTitle = null;
  chapterStructure = null;
  isGeneratingEntireScript = false;
  contentIdeasStep = 1; // Back to title selection
  render();
};

window.openInGoogleDocs = async function (sectionName) {
  const ui = getGamePlanUiText();
  const text = getSectionAsText(sectionName);
  if (!text.trim()) {
    alert(ui.sectionNotFound);
    return;
  }

  let copied = false;
  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(text);
      copied = true;
    }
  } catch (err) {
    console.warn('Clipboard copy failed before opening Google Docs:', err);
  }

  window.open('https://docs.new', '_blank', 'noopener,noreferrer');
  alert(copied ? ui.openGoogleDocsCopiedPrompt : ui.openGoogleDocsCopyFallback);
};

window.exportGamePlan = function () {
  alert(getGamePlanUiText().exportButtonsHint);
};


window.resetGamePlan = function () {
  awaitingGamePlanResult = false;
  currentStep = 1;
  selectedModel = null;
  gamePlanData = {};
  render();
};

// Event Handlers
window.selectGamePlanModel = function (model) {
  selectedModel = model;
  render();

  // Update state locally to avoid full re-render on Step 1
  if (currentStep === 1) {
    document.querySelectorAll('.model-card').forEach(card => {
      card.classList.remove('selected');
      if (card.getAttribute('onclick')?.includes(model)) {
        card.classList.add('selected');
      }
    });
    const btn = document.getElementById('btn-growth-strategy-next');
    if (btn) btn.disabled = false;
  }
};

window.nextGamePlanStep = function () {
  if (currentStep === 1 && selectedModel) {
    currentStep = 2;
    render();
  }
};

window.handleTranscriptUpload = function (input) {
  if (input.files && input.files.length > 0) {
    // Store ACTUAL File objects for submission later
    gamePlanData.files = Array.from(input.files);
    // Metadata for display
    gamePlanData.transcripts = Array.from(input.files).map(f => ({ name: f.name, size: f.size }));
    render();
  }
};

window.startGamePlanWorkflow = async function () {
  console.log('Starting Workflow with data:', gamePlanData);

  // Request notification permission early
  requestNotificationPermission();

  const startBtn = document.querySelector('.btn-start-workflow');
  const progressContainer = document.getElementById('progress-container');
  const progressBarFill = document.getElementById('progress-bar-fill');
  const progressMessage = document.getElementById('progress-message');
  const progressPercent = document.getElementById('progress-percent');

  if (startBtn) {
    startBtn.style.display = 'none'; // Hide button
  }
  if (progressContainer) {
    progressContainer.style.display = 'block'; // Show progress bar
  }

  try {
    await syncAIConfigToBackend();

    const formData = new FormData();
    formData.append('context', gamePlanData.context || '');
    formData.append('website', gamePlanData.website || '');
    formData.append('business_model', selectedModel || 'b2b-agency');
    formData.append('language', getGenerationLanguage());

    const fileInput = document.getElementById('transcript-upload');

    // Priority: Use stored files (from drag/drop or previous select), fallback to input
    const filesToUpload = gamePlanData.files || (fileInput ? fileInput.files : []);

    if (filesToUpload && filesToUpload.length > 0) {
      for (const file of filesToUpload) {
        formData.append('transcripts', file);
      }
    }

    const response = await fetch(BGS_GENERATE_ENDPOINT, {
      method: 'POST',
      body: formData
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop(); // Keep the last partial line

      for (const line of lines) {
        if (!line.trim()) continue;
        try {
          const event = JSON.parse(line);

          if (event.type === 'progress') {
            if (progressMessage) progressMessage.textContent = event.message;
            if (progressPercent) progressPercent.textContent = `${event.percent}%`;
            if (progressBarFill) progressBarFill.style.width = `${event.percent}%`;
          } else if (event.type === 'complete') {
            // Success!
            gamePlanData.result = event.business_growth_strategy || event.game_plan;
            currentStep = 3; // Go to results

            // Save to project history
            await saveGamePlanProject();

            // Show notification and focus window
            const ui = getGamePlanUiText();
            const modelLabel = selectedModel === 'b2b-agency' ? ui.modelLabelAgency : ui.modelLabelSaas;
            notifyBusinessGrowthStrategyComplete(modelLabel);

            render();

            // PARALLEL: Auto-generate titles immediately so they are ready
            setTimeout(() => {
              if (window.generateContentTitles) {
                console.log("Auto-triggering title generation...");
                window.generateContentTitles();
              }
            }, 1000);
            return; // Exit loop
          } else if (event.type === 'error') {
            throw new Error(event.message);
          }
        } catch (jsonError) {
          console.warn("JSON Parse error:", jsonError, line);
        }
      }
    }

  } catch (error) {
    console.error('Workflow error:', error);
    alert(getGamePlanUiText().networkErrorPrefix + error.message);
    if (startBtn) {
      startBtn.style.display = 'block';
      startBtn.innerHTML = getGamePlanUiText().startWorkflow;
      startBtn.disabled = false;
    }
    if (progressContainer) {
      progressContainer.style.display = 'none';
    }
  }
};

async function saveGamePlanProject() {
  try {
    const ui = getGamePlanUiText();
    const modelLabel = selectedModel === 'b2b-agency' ? ui.modelLabelAgency : ui.modelLabelSaas;
    const date = new Date().toLocaleDateString('en-GB').replace(/\//g, '-');
    const title = `BGS - ${modelLabel} - ${date}`;

    const projectData = {
      type: BGS_PROJECT_TYPE, // Differentiates from content-maximizer
      title: title,
      business_model: selectedModel,
      website: gamePlanData.website || '',
      result: gamePlanData.result
    };

    const response = await fetch(apiUrl('/api/save_project'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(projectData)
    });

    if (response.ok) {
      const result = await response.json();
      if (result.success && result.project_id) {
        gamePlanData.id = result.project_id;
        console.log("Business Growth Strategy project saved with ID:", gamePlanData.id);
      }

      // Refresh project list in sidebar
      if (window.refreshProjects) {
        window.refreshProjects();
      }
    }
  } catch (error) {
    console.error('Failed to save Business Growth Strategy project:', error);
  }
}

window.prevGamePlanStep = function () {
  if (currentStep > 1) {
    currentStep--;
    render();
  }
};

window.updateGamePlanData = function (field, value) {
  gamePlanData[field] = value;
};

// Helper: Re-render the Business Growth Strategy page content within the main layout
function render() {
  const content = document.querySelector('.main-content');
  if (content) {
    content.innerHTML = renderBusinessGrowthStrategyPage();
    initBusinessGrowthStrategyEvents();
  }
}

let unsubscribeJob = null;

export function initBusinessGrowthStrategyEvents() {
  // Unsubscribe previous if any
  if (unsubscribeJob) {
    unsubscribeJob();
    unsubscribeJob = null;
  }

  // Subscribe to JobManager
  unsubscribeJob = jobManager.subscribe(state => {
    const onGamePlanPage = Boolean(document.querySelector('.growth-strategy-page'));
    if (!onGamePlanPage) {
      return;
    }

    const isGamePlanJob = state.jobType === BGS_JOB_TYPE || state.jobType === LEGACY_BGS_JOB_TYPE;
    // 1. Update Progress Bar DOM if it exists
    const container = document.getElementById('progress-container');
    const fill = document.getElementById('progress-bar-fill');
    const msg = document.getElementById('progress-message');
    const pct = document.getElementById('progress-percent');
    const time = document.getElementById('progress-time');
    const btn = document.querySelector('.btn-start-workflow');
    const backBtn = document.querySelector('.btn-back');

    if (!isGamePlanJob) {
      if (container) container.style.display = 'none';
      if (btn) btn.style.display = 'inline-block';
      if (backBtn) backBtn.disabled = false;
      return;
    }

    if (container) {
      container.style.display = state.isGenerating ? 'block' : 'none';
      // Also toggle button visibility
      if (btn) btn.style.display = state.isGenerating ? 'none' : 'inline-block';
      if (backBtn) backBtn.disabled = state.isGenerating;

      if (state.isGenerating || state.progress === 100) {
        if (fill) fill.style.width = `${state.progress}%`;
        if (msg) msg.textContent = localizeGamePlanProgressMessage(state.stage, state.message);
        if (pct) pct.textContent = `${state.progress}%`;
        if (time) time.textContent = localizeGamePlanTimeRemaining(state.timeRemaining || '');
      }
    }

    // 2. Handle Completion (Transition to Results)
    if (awaitingGamePlanResult && !state.isGenerating && state.result && currentStep === 2) {
      // Only transition if we are currently waiting on Step 2
      // To avoid repeated transitions, we check if we already have the result in gamePlanData
      // But gamePlanData.result might be from a previous run.
      // We can simply check if the result is different? 
      // For now, let's just proceed.

      console.log("Job completed, transitioning...");
      awaitingGamePlanResult = false;
      gamePlanData.result = state.result;
      currentStep = 3;

      saveGamePlanProject();
      const ui = getGamePlanUiText();
      const modelLabel = selectedModel === 'b2b-agency' ? ui.modelLabelAgency : ui.modelLabelSaas;
      notifyBusinessGrowthStrategyComplete(modelLabel);

      render(); // Re-render to show Step 3

      // Auto-generate titles
      setTimeout(() => {
        if (window.generateContentTitles) {
          console.log("Auto-triggering title generation...");
          window.generateContentTitles();
        }
      }, 1000);
    } else if (awaitingGamePlanResult && !state.isGenerating && state.error && currentStep === 2) {
      // Show error
      awaitingGamePlanResult = false;
      alert(getGamePlanUiText().generationErrorPrefix + state.error);
      // Reset UI to allow retry
      render();
    }
  });
}


// Load saved Business Growth Strategy project from history
window.loadBusinessGrowthStrategyData = async function (projectData) {
  awaitingGamePlanResult = false;
  // Restore state from saved project
  selectedModel = projectData.business_model || 'b2b-agency';
  gamePlanData = {
    id: projectData.id,
    website: projectData.website || '',
    result: projectData.result || {},
    transcripts: projectData.transcripts || []
  };

  // Try to load any existing script for this project from Script Management
  try {
    const res = await fetch(apiUrl('/api/scripts/list'));
    const scriptsRes = await res.json();
    if (scriptsRes.success) {
      // Find ALL scripts for this project
      const projectScripts = scriptsRes.data.filter(s => s.project_id === projectData.id);

      if (projectScripts.length > 0) {
        console.log("Restoring scripts from Script Management:", projectScripts);

        // If multiple scripts, we might want to let the user choose, but for now
        // let's load the most recent one and clear the others if any.
        // Actually, let's load the most recent one by default but store the others 
        // in a global variable so we can maybe show a list? 
        // For now, let's just picking the first one (most recent usually due to insert(0))
        const latestScript = projectScripts[0];

        window.loadScriptIntoView(latestScript);

        // Store all project scripts for potential UI usage (e.g. switching)
        gamePlanData.projectScripts = projectScripts;
      }
    }
  } catch (err) {
    console.error("Error restoring script data:", err);
  }

  currentStep = 3; // Go directly to results
  render();
};

window.loadScriptIntoView = function (scriptData) {
  const ui = getGamePlanUiText();
  selectedTitle = { title: scriptData.title };
  if (scriptData.chapters) {
    chapterStructure = { chapters: scriptData.chapters };
    scriptData.chapters.forEach((ch, i) => {
      scriptChapters[i] = {
        option_a: { style: ui.restoredLabel, script: ch.script },
        option_b: { style: ui.notAvailableLabel, script: '' }
      };
      selectedScriptOptions[i] = 'a';
    });
    contentIdeasStep = 3;
    render();
  }
};

window.loadProjectScriptByIndex = function (index) {
  if (!Array.isArray(gamePlanData.projectScripts)) return;
  const script = gamePlanData.projectScripts[index];
  if (script) {
    window.loadScriptIntoView(script);
  }
};

window.startJobManagerWorkflow = async function () {
  console.log('Starting Workflow via JobManager...');
  const managerState = jobManager.getState();
  if (
    managerState.isGenerating &&
    managerState.jobType &&
    managerState.jobType !== BGS_JOB_TYPE &&
    managerState.jobType !== LEGACY_BGS_JOB_TYPE
  ) {
    alert(getGamePlanUiText().anotherJobRunning);
    return;
  }
  requestNotificationPermission();
  try {
    await syncAIConfigToBackend();
  } catch (error) {
    console.warn('AI config sync failed before workflow start:', error);
  }

  const formData = new FormData();
  formData.append('context', gamePlanData.context || '');
  formData.append('website', gamePlanData.website || '');
  formData.append('business_model', selectedModel || 'b2b-agency');
  formData.append('language', getGenerationLanguage());

  const fileInput = document.getElementById('transcript-upload');
  const filesToUpload = gamePlanData.files || (fileInput ? fileInput.files : []);
  if (filesToUpload && filesToUpload.length > 0) {
    for (const file of filesToUpload) {
      formData.append('transcripts', file);
    }
  }

  awaitingGamePlanResult = true;
  jobManager.startJob(
    BGS_GENERATE_ENDPOINT,
    formData,
    { jobType: BGS_JOB_TYPE }
  );
  render();
};


window.onbeforeunload = function (e) {
  if (jobManager && jobManager.getState().isGenerating) {
    e.preventDefault();
    e.returnValue = '';
    return 'Job is running, are you sure you want to leave?';
  }
};





