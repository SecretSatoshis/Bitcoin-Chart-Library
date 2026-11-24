const state = {
  catalog: null,
  query: '',
  category: 'All',
  lastTrigger: null,
  activeChart: null,
};

const elements = {
  latestDataDate: document.getElementById('latestDataDate'),
  totalChartCount: document.getElementById('totalChartCount'),
  resultsCount: document.getElementById('resultsCount'),
  search: document.getElementById('chartSearch'),
  filters: document.getElementById('categoryFilters'),
  status: document.getElementById('catalogStatus'),
  groups: document.getElementById('chartGroups'),
  viewer: document.getElementById('viewer'),
  viewerCategory: document.getElementById('viewerCategory'),
  viewerTitle: document.getElementById('viewerTitle'),
  viewerDescription: document.getElementById('viewerDescription'),
  standaloneLink: document.getElementById('standaloneLink'),
  closeViewer: document.getElementById('closeViewer'),
  frameWrap: document.getElementById('chartFrameWrap'),
  frame: document.getElementById('chartFrame'),
};

const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');

function scrollBehavior() {
  return reducedMotion.matches ? 'auto' : 'smooth';
}

function safeHistory(method, data, url) {
  try {
    history[method](data, '', url);
  } catch {
    // Ignore history API restrictions in sandboxed or non-HTTP contexts.
  }
}

function formatDate(value) {
  const date = new Date(`${value}T00:00:00Z`);
  return new Intl.DateTimeFormat('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    timeZone: 'UTC',
  }).format(date);
}

function chartSearchText(chart) {
  return [chart.title, chart.description, chart.category, ...chart.tags]
    .join(' ')
    .toLocaleLowerCase();
}

function filteredCharts() {
  const normalizedQuery = state.query.trim().toLocaleLowerCase();
  return state.catalog.charts.filter(chart => {
    const matchesCategory = state.category === 'All' || chart.category === state.category;
    const matchesQuery = !normalizedQuery || chartSearchText(chart).includes(normalizedQuery);
    return matchesCategory && matchesQuery;
  });
}

function makeElement(tag, className, text) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (text !== undefined) element.textContent = text;
  return element;
}

function syncQueryParams(push = false) {
  const url = new URL(window.location.href);
  const trimmed = state.query.trim();
  if (trimmed) url.searchParams.set('q', trimmed);
  else url.searchParams.delete('q');
  if (state.category !== 'All') url.searchParams.set('category', state.category);
  else url.searchParams.delete('category');
  safeHistory(push ? 'pushState' : 'replaceState', { chart: state.activeChart, q: trimmed, category: state.category }, url);
}

function filterByTag(tag) {
  state.query = tag;
  state.category = 'All';
  elements.search.value = tag;
  syncQueryParams(true);
  renderFilters();
  renderCards();
  document.getElementById('catalog').scrollIntoView({ behavior: scrollBehavior(), block: 'start' });
}

function renderFilters() {
  elements.filters.replaceChildren();
  ['All', ...state.catalog.categories].forEach(category => {
    const button = makeElement('button', 'filter-button', category);
    button.type = 'button';
    button.dataset.category = category;
    button.setAttribute('aria-pressed', String(category === state.category));
    button.addEventListener('click', () => {
      state.category = category;
      syncQueryParams(false);
      renderFilters();
      renderCards();
    });
    elements.filters.appendChild(button);
  });
}

function createCard(chart, cardClass = 'chart-card') {
  const article = makeElement('article', cardClass);
  if (chart.featured) {
    article.appendChild(
      makeElement('span', 'featured-label', cardClass === 'featured-card' ? chart.category : 'Featured')
    );
  }

  const title = makeElement('h4', '', chart.title);
  const description = makeElement('p', 'card-description', chart.description);
  const tags = makeElement('ul', 'tag-list');
  chart.tags.slice(0, 4).forEach(tag => {
    const li = makeElement('li');
    const tagButton = makeElement('button', 'tag-button', tag);
    tagButton.type = 'button';
    tagButton.setAttribute('aria-label', `Filter charts by tag ${tag}`);
    tagButton.addEventListener('click', () => filterByTag(tag));
    li.appendChild(tagButton);
    tags.appendChild(li);
  });

  const actions = makeElement('div', 'card-actions');
  const viewButton = makeElement('button', 'button button-primary', 'View chart');
  viewButton.type = 'button';
  viewButton.addEventListener('click', () => openChart(chart, true, viewButton));

  const standalone = makeElement('a', 'button button-secondary', 'Open chart in a new tab ↗');
  standalone.href = chart.url;
  standalone.target = '_blank';
  standalone.rel = 'noopener noreferrer';

  actions.append(viewButton, standalone);
  article.append(title, description, tags, actions);
  return article;
}

function renderFeaturedShelf(fragment) {
  if (state.category !== 'All' || state.query.trim()) return;
  const featured = state.catalog.charts.filter(chart => chart.featured);
  if (!featured.length) return;

  const section = makeElement('section', 'category-group featured-shelf');
  section.setAttribute('aria-labelledby', 'featured-shelf-heading');

  const header = makeElement('div', 'category-heading');
  const title = makeElement('h3', 'category-title', 'Featured · Start Here');
  title.id = 'featured-shelf-heading';
  header.append(title, makeElement('span', 'category-count', `${featured.length} essential charts`));

  const grid = makeElement('div', 'chart-grid featured-grid');
  featured.forEach(chart => grid.appendChild(createCard(chart, 'featured-card')));
  section.append(header, grid);
  fragment.appendChild(section);
}

function renderCards() {
  const charts = filteredCharts();
  elements.groups.replaceChildren();
  elements.groups.setAttribute('aria-busy', 'false');
  elements.resultsCount.textContent = `${charts.length} of ${state.catalog.chart_count} charts`;

  if (!charts.length) {
    elements.groups.appendChild(
      makeElement('p', 'no-results', 'No charts match this search. Try another term or category.')
    );
    return;
  }

  const fragment = document.createDocumentFragment();
  renderFeaturedShelf(fragment);
  state.catalog.categories.forEach((category, categoryIndex) => {
    const categoryCharts = charts.filter(chart => chart.category === category);
    if (!categoryCharts.length) return;

    const section = makeElement('section', 'category-group');
    const headingId = `category-${categoryIndex}`;
    section.setAttribute('aria-labelledby', headingId);

    const header = makeElement('div', 'category-heading');
    const title = makeElement('h3', 'category-title', category);
    title.id = headingId;
    header.append(title, makeElement('span', 'category-count', `${categoryCharts.length} charts`));

    const grid = makeElement('div', 'chart-grid');
    categoryCharts.forEach(chart => grid.appendChild(createCard(chart, 'chart-card')));
    section.append(header, grid);
    fragment.appendChild(section);
  });
  elements.groups.appendChild(fragment);
}

let viewportFrame = 0;
let lastSentViewportHeight = 0;

function sendChartViewport(force = false) {
  if (!state.activeChart || elements.viewer.hidden) return;
  const height = window.innerHeight;
  if (!force && height === lastSentViewportHeight) return;
  lastSentViewportHeight = height;
  elements.frame.contentWindow?.postMessage(
    { type: 'ss-chart-viewport', id: state.activeChart, height },
    location.origin
  );
}

function scheduleViewportSync() {
  cancelAnimationFrame(viewportFrame);
  viewportFrame = requestAnimationFrame(() => sendChartViewport(false));
}

function openChart(chart, updateHistory, trigger = null) {
  state.lastTrigger = trigger;
  state.activeChart = chart.filename;
  lastSentViewportHeight = 0;
  elements.status.textContent = '';
  elements.viewer.hidden = false;
  const accent = makeElement('span', 'accent', '//');
  elements.viewerCategory.replaceChildren(accent, document.createTextNode(` ${chart.category}`));
  elements.viewerTitle.textContent = chart.title;
  elements.viewerDescription.textContent = chart.description;
  elements.standaloneLink.href = chart.url;
  elements.frame.title = `${chart.title} — interactive Bitcoin chart`;
  elements.frame.style.height = `${Math.max(520, chart.height)}px`;
  elements.frameWrap.classList.remove('loaded');

  const embeddedUrl = chart.url + '?embed=1';
  if (elements.frame.getAttribute('src') !== embeddedUrl) {
    elements.frame.src = embeddedUrl;
  } else {
    elements.frameWrap.classList.add('loaded');
    sendChartViewport(true);
  }

  if (updateHistory) {
    const url = new URL(window.location.href);
    url.searchParams.set('chart', chart.filename);
    safeHistory('pushState', { chart: chart.filename }, url);
  }

  elements.viewer.scrollIntoView({ behavior: scrollBehavior(), block: 'start' });
}

function closeViewer(updateHistory = true, restoreFocus = false) {
  state.activeChart = null;
  lastSentViewportHeight = 0;
  elements.viewer.hidden = true;
  elements.frame.removeAttribute('src');
  elements.frameWrap.classList.remove('loaded');
  if (updateHistory) {
    const url = new URL(window.location.href);
    url.searchParams.delete('chart');
    safeHistory('pushState', {}, url);
  }
  if (restoreFocus && state.lastTrigger?.isConnected) state.lastTrigger.focus();
}

function chartFromUrl() {
  const requested = new URL(window.location.href).searchParams.get('chart');
  if (!requested) return null;
  return state.catalog.charts.find(chart => chart.filename === requested) || null;
}

function syncFromUrl() {
  const params = new URL(window.location.href).searchParams;
  const query = params.get('q') || '';
  const requestedCategory = params.get('category') || 'All';
  state.query = query;
  elements.search.value = query;
  state.category =
    requestedCategory === 'All' || state.catalog.categories.includes(requestedCategory)
      ? requestedCategory
      : 'All';
  renderFilters();
  renderCards();

  const requested = params.get('chart');
  const chart = chartFromUrl();
  if (chart) {
    elements.status.textContent = '';
    openChart(chart, false);
  } else if (requested) {
    closeViewer(false);
    elements.status.textContent = `Chart “${requested}” was not found in this catalog.`;
  } else {
    elements.status.textContent = '';
    closeViewer(false);
  }
}

async function loadCatalog() {
  try {
    state.catalog = JSON.parse(document.getElementById('catalog-data').textContent);

    elements.latestDataDate.dateTime = state.catalog.latest_data_date;
    elements.latestDataDate.textContent = formatDate(state.catalog.latest_data_date);
    elements.totalChartCount.textContent = state.catalog.chart_count.toLocaleString();
    elements.search.placeholder = `Search ${state.catalog.chart_count} Bitcoin charts…`;
    syncFromUrl();
  } catch (error) {
    elements.groups.setAttribute('aria-busy', 'false');
    elements.resultsCount.textContent = 'Catalog unavailable';
    elements.status.textContent = 'The chart catalog could not be loaded. Please refresh and try again.';
    console.error(error);
  }
}

elements.search.addEventListener('input', event => {
  state.query = event.target.value;
  syncQueryParams(false);
  renderCards();
});

elements.closeViewer.addEventListener('click', () => {
  closeViewer(true, true);
  document.getElementById('catalog').scrollIntoView({ behavior: scrollBehavior(), block: 'start' });
});

elements.frame.addEventListener('load', () => {
  elements.frameWrap.classList.add('loaded');
  sendChartViewport(true);
});
window.addEventListener('resize', scheduleViewportSync);

const navToggle = document.getElementById('navToggle');
const navLinks = document.getElementById('navLinks');

function closeNavigation() {
  navLinks.classList.remove('open');
  navToggle.setAttribute('aria-expanded', 'false');
  navToggle.setAttribute('aria-label', 'Open menu');
}

navToggle.addEventListener('click', () => {
  const isOpen = navToggle.getAttribute('aria-expanded') === 'true';
  if (isOpen) {
    closeNavigation();
  } else {
    navLinks.classList.add('open');
    navToggle.setAttribute('aria-expanded', 'true');
    navToggle.setAttribute('aria-label', 'Close menu');
  }
});

navLinks.addEventListener('click', event => {
  if (event.target.closest('a')) closeNavigation();
});

window.addEventListener('popstate', () => {
  if (state.catalog) syncFromUrl();
});

document.addEventListener('keydown', event => {
  const target = event.target;
  const isTyping = target instanceof HTMLInputElement || target instanceof HTMLTextAreaElement;
  if (event.key === '/' && !isTyping) {
    event.preventDefault();
    elements.search.focus();
  }
  if (event.key === 'Escape' && !elements.viewer.hidden) {
    closeViewer(true, true);
  }
  if (event.key === 'Escape' && navToggle.getAttribute('aria-expanded') === 'true') {
    closeNavigation();
    navToggle.focus();
  }
});

loadCatalog();

window.addEventListener('message', event => {
  if (event.source !== elements.frame.contentWindow) return;
  if (event.origin !== location.origin) return;
  const message = event.data;
  if (message?.type !== 'ss-chart-size' || !state.activeChart || message.id !== state.activeChart || !Number.isFinite(message.height)) return;
  const nextHeight = `${Math.max(400, Math.min(3000, Math.ceil(message.height)))}px`;
  if (elements.frame.style.height !== nextHeight) {
    elements.frame.style.height = nextHeight;
  }
});
