const categories = [
  ['UX and critical task completion', 20, true],
  ['Visual distinction and brand accuracy', 15, false],
  ['Accessibility', 15, true],
  ['Responsive experience', 10, false],
  ['Architecture and component quality', 10, false],
  ['Performance', 10, true],
  ['Motion and interaction', 5, false],
  ['Content accuracy and trust', 5, false],
  ['Security and privacy', 5, true],
  ['Test evidence', 5, false],
];

const wcagChecks = [
  ['Keyboard Navigation (2.1.1)', 'All navigation tabs, modals, forms, and action controls operable via Tab/Shift+Tab/Enter/Escape without keyboard traps.'],
  ['Focus Visibility (2.4.7 / 2.4.11)', 'Explicit 2px Burnished Gold focus ring with 2px offset applied globally to every interactive element.'],
  ['Labels & ARIA Landmarks (1.3.1 / 4.1.2)', 'Semantic <aside>, <nav>, <main>, <header>, <section>, role="status" live region, and explicit <label> bindings on all inputs.'],
  ['Touch Target Size (2.5.8)', 'Primary buttons and navigation controls maintain >= 40-44px hit height with generous spacing on mobile viewports.'],
  ['200% Zoom & Mobile Reflow (1.4.4 / 1.4.10)', 'Responsive CSS Grid collapses cleanly to single column at <= 760px with zero horizontal overflow.'],
  ['Reduced Motion (2.3.3)', '@media (prefers-reduced-motion: reduce) disables all transitions, animations, and smooth scrolling automatically.'],
];

const integrations = [
  ['Scrypt Auth, Signed Sessions & RBAC', 'Working', 'HttpOnly/SameSite=Strict HMAC-SHA256 sessions, 3 roles (principal, director, viewer), sliding-window rate limiter, and immutable audit log.', true],
  ['Protected Settlement Vault', 'Working', 'Banking & settlement instructions removed from shared templates; requires recipient verification + Principal approval before PDF attachment.', true],
  ['Real Headless Chrome PDF Pipeline', 'Working', 'GET /api/brand/export/pdf renders Executive Investor Memoranda into real binary %PDF files via local Headless Chrome with @page rules.', true],
  ['Versioned Design Contract Engine (v2.1)', 'Working', 'Strict HEX/font/geometry/WCAG schema validator rejecting invalid mutations and prohibiting financial data inside brand tokens.', true],
  ['8-Department AI Creative Director & Industry Registry', 'Working', 'Executable 8-department orchestration across 8 sector profiles with client-inheritable palettes + React/TypeScript/Tailwind v4 scaffold generator.', true],
  ['SQLite Online Backup Engine', 'Working', 'POST /api/admin/backup uses sqlite3.Connection.backup() for consistent live snapshots with audit logging.', true],
  ['Cloudflare Workers + D1 + R2 Deployment', 'Planned (Phase 5)', 'Target cloud deployment for secure iPhone/remote access with MFA, Durable Objects, and R2 asset storage.', false],
  ['Isolated GPU 3D / Video & Image Workers', 'Planned (Phase 3)', 'Connect external Blender/Three.js GPU workers and authorized commercial image/video generation APIs.', false],
];

const state = {
  user: null,
  styles: [],
  components: [],
  industries: [],
  departments: [],
  brand: null,
  projects: [],
  current: null,
  activeCategory: 'All',
};

const $ = (id) => document.getElementById(id);

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = String(text);
  return node;
}

function clear(node) {
  node.replaceChildren();
  return node;
}

function notify(message) {
  const node = $('alert');
  node.textContent = message;
  node.classList.remove('hidden');
  clearTimeout(notify._t);
  notify._t = setTimeout(() => node.classList.add('hidden'), 5500);
}

async function api(path, options) {
  const response = await fetch('/api/' + path, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  let value;
  try {
    value = await response.json();
  } catch {
    throw new Error('Server returned an invalid response');
  }
  if (!response.ok) throw new Error(value.error || 'Request failed');
  return value;
}

function button(label, onClick, className = 'button outline') {
  const node = el('button', className, label);
  node.type = 'button';
  node.addEventListener('click', onClick);
  return node;
}

function screen(name) {
  for (const item of document.querySelectorAll('.screen')) {
    item.classList.toggle('active', item.id === name);
  }
  for (const item of document.querySelectorAll('.navitem')) {
    item.classList.toggle('active', item.dataset.screen === name);
  }
  const titles = {
    overview: 'Executive Overview',
    brandkit: 'Global Brand Kit & Versioned Contracts',
    vault: 'RJ Sovereign Envato & Brand Asset Vault',
    orchestrator: 'AI Creative Director & Industry Intelligence',
    production: 'Production Studio, Repo Adapter & Automated QA',
    components: 'Design System Component Showroom',
    studio: 'Visual Direction Studio',
    projects: 'Client Mandates & Production Runs',
    settlements: 'Protected Settlement & Audit Vault',
    quality: 'Visual Quality & Full WCAG 2.2 Lab',
    integrations: 'Architecture, Security & Roadmap',
  };
  $('page-title').textContent = titles[name] || 'Command Overview';
  if (name === 'settlements' && state.user) {
    loadSettlementsAndAudit();
  }
  if (name === 'production') {
    loadProductionAndQA();
  }
  if (name === 'vault') {
    loadVault();
  }
}

/* Auth UI */
function renderAuthState() {
  const btn = $('auth-btn');
  const label = $('auth-status-label');
  if (state.user) {
    btn.textContent = `Sign Out (${state.user.role.toUpperCase()})`;
    label.textContent = `SIGNED IN: ${state.user.username.toUpperCase()}`;
  } else {
    btn.textContent = 'Sign In (RBAC)';
    label.textContent = 'SESSION: PUBLIC READ';
  }
}

/* WCAG Contrast */
function hexToRgb(hex) {
  const clean = String(hex || '').replace('#', '').trim();
  if (clean.length !== 6) return [0, 0, 0];
  return [parseInt(clean.slice(0, 2), 16), parseInt(clean.slice(2, 4), 16), parseInt(clean.slice(4, 6), 16)];
}
function luminance(hex) {
  const [r, g, b] = hexToRgb(hex).map((v) => {
    const s = v / 255;
    return s <= 0.03928 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4);
  });
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}
function contrastRatio(hex1, hex2) {
  const l1 = luminance(hex1), l2 = luminance(hex2);
  return (Math.max(l1, l2) + 0.05) / (Math.min(l1, l2) + 0.05);
}

/* Brand Kit */
function applyBrandToUI(kit) {
  if (!kit) return;
  const { identity, palette, typography } = kit;
  $('brand-name-nav').textContent = identity.firm_name.toUpperCase();
  $('sidebar-firm').textContent = identity.firm_name;
  $('sidebar-principal').textContent = identity.principal;
  $('topbar-subline').textContent = identity.subline;
  $('brand-logo-nav').src = identity.logo_url;
  $('type-pairing-label').textContent = `${typography.display_font} · ${typography.body_font}`;

  const palGrid = clear($('brand-palette-grid'));
  for (const [key, hex] of Object.entries(palette)) {
    const chip = el('button', 'color-chip');
    chip.type = 'button';
    const box = el('span', 'color-box');
    box.style.background = hex;
    const info = el('div');
    info.append(el('strong', '', key.replace(/_/g, ' ')), el('code', '', `${hex} · --rj-${key.replace(/_/g, '-')}`));
    chip.append(box, info);
    chip.addEventListener('click', () => {
      if (navigator.clipboard) navigator.clipboard.writeText(hex).catch(() => {});
      notify(`Copied ${key.replace(/_/g, ' ')} (${hex}) to clipboard.`);
    });
    palGrid.append(chip);
  }

  const form = $('brand-form');
  const mapping = {
    firm_name: identity.firm_name,
    principal: identity.principal,
    principal_title: identity.principal_title,
    subline: identity.subline,
    website: identity.website,
    email: identity.email,
    positioning: identity.positioning,
    gold: palette.gold,
    obsidian: palette.obsidian,
    alabaster: palette.alabaster,
    display_font: typography.display_font,
    body_font: typography.body_font,
    numeric_font: typography.numeric_font,
  };
  for (const [name, val] of Object.entries(mapping)) {
    const input = form.elements.namedItem(name);
    if (input) input.value = val;
  }

  renderContrastMatrix(palette);
}

function renderContrastMatrix(p) {
  const target = clear($('contrast-matrix'));
  const pairs = [
    ['Ivory Text on Sovereign Obsidian', '#F5F2EB', p.obsidian],
    ['Brushed Champagne Gold on Obsidian', p.champagne, p.obsidian],
    ['Sovereign Obsidian Text on Burnished Gold CTA', p.obsidian, p.gold],
    ['Primary Ink on Warm Alabaster Paper', p.ink, p.alabaster],
    ['Deep Antique Bronze on Pure Ivory', p.bronze, p.ivory],
    ['Institutional Emerald on Parchment Mist', p.emerald, p.parchment],
  ];
  for (const [label, fg, bg] of pairs) {
    const ratio = contrastRatio(fg, bg);
    const grade = ratio >= 7 ? 'AAA' : ratio >= 4.5 ? 'AA' : ratio >= 3 ? 'AA Large' : 'Check';
    const row = el('div', 'contrast-item');
    row.style.background = bg;
    row.style.color = fg;
    row.append(el('strong', '', label), el('span', 'tabular-nums', `${ratio.toFixed(2)}:1 · ${grade}`));
    target.append(row);
  }
}

/* Styles */
function styleCard(style) {
  const card = el('article', 'style-card' + (style.is_default ? ' default-flag' : ''));
  const visual = el('div', 'swatch');
  visual.style.background = `linear-gradient(135deg, ${style.colors[0]} 0%, ${style.colors[1]} 74%, ${style.colors[2]} 100%)`;
  if (style.is_default) visual.append(el('span', 'default-ribbon', 'RJ GLOBAL STANDARD'));
  visual.append(el('div', 'swatch-type', style.name.split(' ')[0]));
  const dots = el('div', 'swatch-dots');
  for (const hex of style.colors) {
    const dot = el('span', 'swatch-dot');
    dot.style.background = hex;
    dot.title = hex;
    dots.append(dot);
  }
  visual.append(dots);
  card.append(visual);
  const copy = el('div', 'style-copy');
  copy.append(
    el('small', '', style.category.toUpperCase()),
    el('h4', '', style.name),
    el('p', '', style.description),
    el('div', 'font-info', style.font)
  );
  card.append(copy);
  return card;
}

function renderStyles() {
  $('style-count').textContent = String(state.styles.length).padStart(2, '0');
  const overview = clear($('overview-styles'));
  for (const item of state.styles.slice(0, 3)) overview.append(styleCard(item));

  const cats = ['All', ...new Set(state.styles.map((s) => s.category))];
  const filterBar = clear($('style-filters'));
  for (const cat of cats) {
    const btn = el('button', 'filter-btn' + (state.activeCategory === cat ? ' active' : ''), cat);
    btn.type = 'button';
    btn.addEventListener('click', () => { state.activeCategory = cat; renderStyles(); });
    filterBar.append(btn);
  }

  const studio = clear($('studio-styles'));
  const visible = state.activeCategory === 'All' ? state.styles : state.styles.filter((s) => s.category === state.activeCategory);
  for (const item of visible) studio.append(styleCard(item));
}

/* AI Creative Director & Industry Intelligence */
function renderOrchestratorCatalog() {
  $('dept-count').textContent = String(state.departments.length).padStart(2, '0');
  $('overview-industries-count').textContent = String(state.industries.length).padStart(2, '0');

  const dGrid = clear($('departments-grid'));
  for (const dept of state.departments) {
    const box = el('div', 'integration');
    box.append(
      el('h4', '', dept.name),
      el('span', 'seal-pill gold', `${dept.specialists} SPECIALISTS · HANDOFF -> ${dept.handoff_to}`),
      el('p', '', dept.responsibility),
      el('p', '', `Outputs: ${dept.outputs.join(', ')} · Gate: ${dept.acceptance_threshold}`)
    );
    dGrid.append(box);
  }

  const iGrid = clear($('industries-grid'));
  for (const ind of state.industries) {
    const box = el('div', 'integration');
    const dots = el('div', 'component-row');
    dots.style.margin = '8px 0';
    for (const hex of ind.client_palette) {
      const dot = el('span', 'swatch-dot');
      dot.style.background = hex;
      dot.title = hex;
      dots.append(dot);
    }
    box.append(
      el('h4', '', ind.name),
      dots,
      el('p', '', `Expectations: ${ind.audience_expectations}`),
      el('p', '', `Typography: ${ind.typography_family} · Motion/3D: ${ind.motion_3d_intensity}`),
      el('p', '', `Compliance: ${ind.compliance_constraints.join('; ')}`)
    );
    iGrid.append(box);
  }
}

function renderComponentsRegistry() {
  $('component-count').textContent = String(state.components.length).padStart(2, '0');
  const list = clear($('component-registry-list'));
  for (const comp of state.components) {
    const row = el('div', 'rubric-row');
    row.append(el('span', '', `${comp.name} · ${comp.category}`), el('strong', 'tabular-nums', comp.wcag));
    list.append(row);
  }
}

/* Settlements & Audit Vault */
async function loadSettlementsAndAudit() {
  try {
    const [settlements, logs] = await Promise.all([api('settlements'), api('audit')]);
    const sTarget = clear($('settlements-list'));
    if (!settlements.length) {
      sTarget.append(el('p', 'section-intro', 'No settlement records yet. Create one on the left to test the 2-step approval workflow.'));
    } else {
      for (const s of settlements) {
        const card = el('div', 'direction-row');
        const statusClass = s.approval_status === 'approved' ? 'emerald' : s.approval_status === 'revoked' ? 'crimson' : 'amber';
        card.append(
          el('strong', '', `${s.recipient_name} (${s.method.toUpperCase()})`),
          el('p', '', `${s.institution} · Ref: ${s.reference_code}`),
          el('span', `seal-pill ${statusClass}`, `${s.approval_status.toUpperCase()} · ${s.recipient_verified ? 'RECIPIENT VERIFIED' : 'UNVERIFIED'}`)
        );
        const actions = el('div', 'component-row');
        actions.style.marginTop = '10px';
        if (!s.recipient_verified) {
          actions.append(button('Verify Recipient', async () => {
            try { await api(`settlements/${s.id}/verify`, { method: 'POST', body: '{}' }); notify('Recipient verified.'); await loadSettlementsAndAudit(); }
            catch (err) { notify(err.message); }
          }));
        }
        if (s.recipient_verified && s.approval_status !== 'approved') {
          actions.append(button('Principal Approve', async () => {
            try { await api(`settlements/${s.id}/approve`, { method: 'POST', body: '{}' }); notify('Settlement approved by Principal.'); await loadSettlementsAndAudit(); }
            catch (err) { notify(err.message); }
          }, 'button gold'));
        }
        if (s.recipient_verified && s.approval_status === 'approved') {
          const pdfLink = el('a', 'button gold', 'Issue Authorized PDF ↗');
          pdfLink.href = `/api/brand/export/pdf?settlement_id=${s.id}`;
          pdfLink.target = '_blank';
          pdfLink.rel = 'noopener';
          actions.append(pdfLink);
        }
        card.append(actions);
        sTarget.append(card);
      }
    }

    const aTarget = clear($('audit-log-list'));
    if (!logs.length) {
      aTarget.append(el('p', 'section-intro', 'No audit events recorded yet.'));
    } else {
      for (const log of logs.slice(0, 20)) {
        const row = el('div', 'rubric-row');
        row.append(
          el('span', '', `[${log.role}] ${log.actor} · ${log.action} · ${log.details}`),
          el('strong', 'tabular-nums', log.created_at.slice(0, 19).replace('T', ' '))
        );
        aTarget.append(row);
      }
    }
  } catch (err) {
    notify(err.message);
  }
}

const ENVATO_LUXURY_FONTS = [
  ['Taillevere', 'Investor Luxury Didone Serif', 'Sovereign Private Wealth & Capital'],
  ['Auretha', 'Modern Luxury Serif (7 Weights)', 'Institutional Advisory & Family Offices'],
  ['Siovanni', 'Luxury Display Serif (14 Styles)', 'Confidential Offering Memorandum'],
  ['Pierre Robe', 'Cinematic Luxury Serif', 'Bespoke Executive Branding'],
  ['Editorial Luxury', 'High-Contrast Editorial Serif', 'Annual Investor Stewardship Letter'],
  ['Galante', 'Branding Luxury Family (9 Weights)', 'RJ Business Solutions Sovereign'],
  ['Swarsh Daisy', 'Ultra-High-Contrast Display', 'Private Placement Edition'],
  ['Morgen', 'Sculptural Luxury Display', 'RJ · EST. SOVEREIGN'],
  ['Xenon Nue', 'Neo-Grotesque Sans (18 Styles)', 'Institutional precision, zero startup hype.'],
  ['Grift', 'Geometric Financial Sans (18+Var)', '$1,450,000,000 · +21.6% Net IRR'],
  ['Vank', 'Bold Condensed Impact Display', 'BILLION-DOLLAR ARCHITECTURE'],
  ['Nority', 'Inktrap Bold Display', 'SOVEREIGN CAPITAL COMMAND'],
];

async function loadVault() {
  try {
    const v = await api('vault');
    const fGrid = clear($('vault-fonts-grid'));
    for (const [family, role, sample] of ENVATO_LUXURY_FONTS) {
      const box = el('div', 'integration');
      const specimen = el('div', '', sample);
      specimen.style.fontFamily = `'${family}', Georgia, serif`;
      specimen.style.fontSize = '26px';
      specimen.style.lineHeight = '1.2';
      specimen.style.margin = '10px 0 6px';
      box.append(el('span', 'seal-pill gold', `${family} · ${role}`), specimen);
      fGrid.append(box);
    }

    const lGrid = clear($('vault-logos-grid'));
    for (const url of v.logos || []) {
      const card = el('a', 'vault-thumb');
      card.href = url; card.target = '_blank'; card.rel = 'noopener';
      const img = el('img'); img.src = url; img.alt = url.split('/').pop();
      img.style.objectFit = 'contain'; img.style.background = '#0A0B0E'; img.style.padding = '8px';
      card.append(img, el('small', '', url.split('/').pop()));
      lGrid.append(card);
    }

    const cBox = clear($('vault-contact-box'));
    const c = v.contact_directory || {};
    const rows = [
      ['Managing Principal', `${c.founder || 'Rick Jefferson'} (${c.founder_title || ''})`],
      ['Telephone', c.telephone || '(817) 587-4783'],
      ['Executive Direct Email', c.executive_email || 'rick@rickjefferson.com'],
      ['Primary Support Email', c.primary_email || 'support@rjbusinesssolutions.org'],
      ['DFW / Texas HQ', c.addresses?.dfw_texas_hq || '99 Regency Pkwy., Suite 305, Mansfield, TX 76063'],
      ['New Mexico Corporate', c.addresses?.new_mexico_corporate || '1342 NM 333, Tijeras, NM 87059'],
      ['Websites', `${c.official_websites?.corporate || ''} · ${c.official_websites?.executive_brand || ''}`],
      ['Client Portal', c.official_websites?.client_portal || 'https://rickjefferson.com/portal/'],
    ];
    for (const [k, val] of rows) {
      const r = el('div', 'rubric-row');
      r.append(el('strong', '', k), el('span', '', val));
      cBox.append(r);
    }

    const kGrid = clear($('vault-kits-grid'));
    for (const kit of v.envato_kits || []) {
      const box = el('div', 'integration');
      box.append(
        el('h4', '', `#${kit.rank} · ${kit.title}`),
        el('span', 'seal-pill emerald', `SCORE ${kit.weighted_score}/100 · ${(kit.formats || []).join(', ')}`),
        el('p', '', `Creator: ${kit.creator} · Category: ${kit.category} · Extracted in ${kit.working_dir}`)
      );
      kGrid.append(box);
    }

    const pGrid = clear($('vault-photos-grid'));
    for (const url of [...(v.photos || []), ...(v.textures || [])]) {
      const card = el('a', 'vault-thumb');
      card.href = url; card.target = '_blank'; card.rel = 'noopener';
      const img = el('img'); img.src = url; img.alt = url.split('/').pop();
      card.append(img, el('small', '', url.split('/').pop()));
      pGrid.append(card);
    }
    await runEnvatoSearch();
  } catch (err) {
    notify('Could not load Envato Vault: ' + err.message);
  }
}

async function runEnvatoSearch() {
  try {
    const form = $('envato-search-form');
    const q = form ? form.elements.namedItem('q').value : '';
    const cat = form ? form.elements.namedItem('category').value : 'all';
    const res = await api(`envato/search?q=${encodeURIComponent(q)}&category=${encodeURIComponent(cat)}`);
    $('envato-status-badge').textContent = `${res.vault_count} ARCHIVES CONNECTED`;
    $('envato-live-link').href = res.envato_elements_live_url;
    const grid = clear($('envato-search-results'));
    if (!res.matches.length) {
      grid.append(el('p', 'section-intro', 'No local vault matches. Click "Browse Live Envato Elements" to download a new asset, then ingest it with rj-envato ingest.'));
      return;
    }
    for (const item of res.matches.slice(0, 12)) {
      const box = el('div', 'integration');
      box.append(
        el('h4', '', item.title),
        el('span', 'seal-pill gold', `${item.category.toUpperCase()} · ${item.size_mb} MB · ${item.file_count} FILES`),
        el('p', '', `Formats: ${(item.formats || []).join(', ')}`),
        button('Install & Auto-Rebrand into Project', async () => {
          const targetDir = $('envato-target-dir').value.trim();
          if (!targetDir) { notify('Enter a target project directory first.'); return; }
          try {
            const out = await api('envato/install', {
              method: 'POST',
              body: JSON.stringify({ asset_id: item.id, target_dir: targetDir, apply_rj_branding: true }),
            });
            notify(`Installed ${out.title} (${out.extracted_count} files) + RJ Black & Gold Brand Kit into ${out.target_dir}`);
          } catch (err) { notify(err.message); }
        }, 'button gold')
      );
      grid.append(box);
    }
  } catch (err) {
    notify('Envato search failed: ' + err.message);
  }
}

async function loadProductionAndQA() {
  try {
    const [assets, qaRuns] = await Promise.all([api('production/assets'), api('qa/runs')]);
    const aTarget = clear($('assets-list'));
    for (const a of assets) {
      const row = el('div', 'rubric-row');
      const link = el('a', 'button outline', `Open ${a.asset_type} ↗`);
      link.href = `/api/production/assets/${a.id}`;
      link.target = '_blank';
      link.rel = 'noopener';
      row.append(el('span', '', `${a.title} · SHA256:${a.sha256.slice(0, 10)}`), link);
      aTarget.append(row);
    }
    const qTarget = clear($('qa-runs-list'));
    if (!qaRuns.length) {
      qTarget.append(el('p', 'section-intro', 'No automated QA runs recorded yet. Sign in and click "Run Live Automated QA Audit".'));
    } else {
      for (const run of qaRuns.slice(0, 5)) {
        const row = el('div', 'rubric-row');
        row.append(
          el('span', '', `${run.started_at.slice(0, 19).replace('T', ' ')} · ${run.passed_checks}/${run.total_checks} checks · TTFB ${run.latency_ms}ms · ${run.screenshots.length} screenshots`),
          el('strong', 'tabular-nums', `${run.score}/100 · ${run.release_approved ? 'RELEASE APPROVED' : 'BLOCKED'}`)
        );
        qTarget.append(row);
      }
    }
  } catch (err) {
    notify(err.message);
  }
}

/* Projects */
async function loadProjects() {
  state.projects = await api('projects');
  $('project-count').textContent = state.projects.length;
  $('overview-projects').textContent = state.projects.length;
  renderProjects();
}

function renderProjects() {
  const target = clear($('projects-list'));
  if (!state.projects.length) {
    const empty = el('div', 'info-card');
    empty.append(
      el('h4', '', 'No active mandates yet'),
      el('p', '', 'Sign in and create a client mandate to rank luxury directions, run the 8-department AI Creative Director, generate a React/TypeScript scaffold, and record a 10-category quality audit.')
    );
    target.append(empty);
    return;
  }
  for (const project of state.projects) {
    const card = el('button', 'project-card');
    card.type = 'button';
    card.append(
      el('span', 'overline', project.industry.toUpperCase()),
      el('h4', '', project.name),
      el('p', '', project.brief.slice(0, 140) + (project.brief.length > 140 ? '…' : ''))
    );
    card.addEventListener('click', () => openProject(project.id));
    target.append(card);
  }
}

async function openProject(id) {
  try {
    state.current = await api('projects/' + id);
    screen('projects');
    renderDetail();
  } catch (error) {
    notify(error.message);
  }
}

function renderDetail() {
  const { project, directions, memories, evaluations, orchestration_runs = [] } = state.current;
  const detail = clear($('project-detail'));
  detail.classList.remove('hidden');

  const header = el('div', 'detail-header');
  const titleWrap = el('div');
  titleWrap.append(
    el('span', 'overline', 'MANDATE WORKSPACE'),
    el('h3', '', project.name),
    el('p', 'section-intro', `${project.industry} · ${project.audience} · ${project.mood}`)
  );
  const actions = el('div', 'component-row');
  actions.append(
    button('Run 8-Dept AI Director', async () => {
      try {
        const res = await api(`projects/${project.id}/orchestrate`, { method: 'POST', body: '{}' });
        notify(`AI Creative Director completed ${res.departments_executed} departments (${res.total_specialists} specialists) using ${res.palette_inheritance}.`);
        await openProject(project.id);
      } catch (err) { notify(err.message); }
    }, 'button gold'),
    button('Generate React/TS Scaffold', async () => {
      try {
        const sc = await api(`projects/${project.id}/scaffold`);
        const blob = new Blob([JSON.stringify(sc, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${project.name.toLowerCase().replace(/\s+/g, '-')}-react-scaffold.json`;
        a.click();
        URL.revokeObjectURL(url);
        notify(`Downloaded React + TypeScript + Tailwind v4 scaffold (${sc.industry}).`);
      } catch (err) { notify(err.message); }
    }, 'button outline'),
    button('Download React+3D .ZIP', () => {
      window.open(`/api/projects/${project.id}/bundle.zip`, '_blank', 'noopener');
    }, 'button outline'),
    button('Delete', async () => {
      try {
        await api('projects/' + project.id, { method: 'DELETE' });
        state.current = null;
        detail.classList.add('hidden');
        await loadProjects();
        notify('Mandate deleted.');
      } catch (err) { notify(err.message); }
    }, 'button danger')
  );
  header.append(titleWrap, actions);
  detail.append(header);

  if (orchestration_runs.length) {
    const latest = orchestration_runs[0];
    const runBox = el('section', 'detail-box');
    runBox.style.marginBottom = '20px';
    runBox.append(
      el('h4', '', `Latest AI Creative Director Run · ${latest.industry_intelligence.name}`),
      el('p', 'section-intro', `Palette Inheritance: ${latest.palette_inheritance} · ${latest.departments_executed} Departments (${latest.total_specialists} Specialists) Passed`)
    );
    for (const st of latest.stages) {
      const row = el('div', 'rubric-row');
      row.append(el('span', '', `${st.department_name} (${st.specialists_assigned}) -> ${st.handoff_to}`), el('strong', '', st.status.toUpperCase()));
      runBox.append(row);
    }
    detail.append(runBox);
  }

  const grid = el('div', 'detail-grid');
  const a = el('section', 'detail-box'), b = el('section', 'detail-box');
  a.append(el('h4', '', 'Recommended Visual Directions'));
  for (const choice of directions) {
    const style = state.styles.find((s) => s.id === choice.style_id);
    const row = el('div', 'direction-row' + (choice.selected ? ' selected' : ''));
    row.append(el('strong', '', style ? style.name : choice.style_id), el('p', '', `${choice.score}/100 relevance · ${choice.rationale}`));
    if (style) row.append(el('p', '', style.font));
    row.append(button(
      choice.selected ? 'Approved Direction' : 'Approve Direction',
      async () => {
        try { await api(`projects/${project.id}/select/${choice.id}`, { method: 'POST', body: '{}' }); await openProject(project.id); }
        catch (err) { notify(err.message); }
      },
      choice.selected ? 'button gold' : 'button outline'
    ));
    a.append(row);
  }
  a.append(button(directions.length ? 'Re-rank Directions' : 'Generate 3 Directions', async () => {
    try { await api(`projects/${project.id}/directions`, { method: 'POST', body: '{}' }); await openProject(project.id); }
    catch (err) { notify(err.message); }
  }, 'button gold'));

  b.append(el('h4', '', 'Mandate Design Memory'));
  for (const item of memories) {
    const row = el('div', 'rubric-row');
    row.append(el('strong', '', item.label), el('span', '', item.value));
    b.append(row);
  }
  const memoryForm = el('form', 'mini-form');
  const label = el('input', 'mini-input'); label.placeholder = 'Decision label'; label.required = true;
  const value = el('textarea', 'mini-input'); value.placeholder = 'Approved preference or stakeholder rule'; value.required = true; value.rows = 3;
  const memSubmit = el('button', 'button gold', 'Record Memory'); memSubmit.type = 'submit';
  memoryForm.append(label, value, memSubmit);
  memoryForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    try { await api(`projects/${project.id}/memory`, { method: 'POST', body: JSON.stringify({ label: label.value, value: value.value }) }); await openProject(project.id); }
    catch (err) { notify(err.message); }
  });
  b.append(memoryForm);
  grid.append(a, b);
  detail.append(grid);

  const review = el('section', 'detail-box');
  review.style.marginTop = '20px';
  review.append(el('h4', '', '10-Category 100-Point Release Gate Evaluation'));
  const form = el('form', 'mini-form');
  const name = el('input', 'mini-input'); name.placeholder = 'Review milestone, e.g. Investor Portal v2.1'; name.required = true;
  form.append(name);
  const sliders = {};
  for (const [cat, weight, isCrit] of categories) {
    const wrapper = el('label', 'quality-slider');
    const current = el('span', '', `${cat} · ${weight}%${isCrit ? ' (CRITICAL)' : ''}`);
    const shown = el('strong', 'tabular-nums', '4/5');
    const input = el('input'); input.type = 'range'; input.min = 0; input.max = 5; input.step = 1; input.value = 4;
    input.addEventListener('input', () => { shown.textContent = input.value + '/5'; });
    sliders[cat] = input;
    wrapper.append(current, shown, input);
    form.append(wrapper);
  }
  const evalSubmit = el('button', 'button gold', 'Record Release Gate Audit'); evalSubmit.type = 'submit';
  form.append(evalSubmit);
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    try {
      const metrics = Object.fromEntries(Object.entries(sliders).map(([k, inp]) => [k, Number(inp.value)]));
      const result = await api(`projects/${project.id}/evaluate`, { method: 'POST', body: JSON.stringify({ name: name.value, metrics }) });
      notify(`Audit recorded: ${result.score}/100 · ${result.status}`);
      await openProject(project.id);
    } catch (err) { notify(err.message); }
  });
  review.append(form);
  if (evaluations.length) {
    review.append(el('h4', '', 'Audit History'));
    for (const item of evaluations) {
      const row = el('div', 'rubric-row');
      const blockers = JSON.parse(item.blockers);
      row.append(el('span', '', item.name), el('strong', 'tabular-nums', `${item.score}/100${blockers.length ? ' · Blockers: ' + blockers.join(', ') : ' · Passed'}`));
      review.append(row);
    }
  }
  detail.append(review);
}

function renderQuality() {
  const target = clear($('quality-rubric'));
  for (const [name, weight, isCrit] of categories) {
    const row = el('div', 'rubric-row');
    row.append(el('span', '', name + (isCrit ? ' · Critical Gate' : '')), el('strong', 'tabular-nums', `${weight}%`));
    target.append(row);
  }
  const checklist = clear($('wcag-checklist'));
  for (const [title, desc] of wcagChecks) {
    const box = el('div', 'integration');
    box.append(el('h4', '', title), el('span', 'seal-pill emerald', 'IMPLEMENTED'), el('p', '', desc));
    checklist.append(box);
  }
}

function renderIntegrations() {
  const target = clear($('integration-grid'));
  for (const [name, status, description, ready] of integrations) {
    const box = el('div', 'integration');
    box.append(el('h4', '', name), el('span', 'seal-pill ' + (ready ? 'emerald' : 'amber'), status.toUpperCase()), el('p', '', description));
    target.append(box);
  }
}

async function start() {
  document.querySelectorAll('.navitem').forEach((item) => item.addEventListener('click', () => screen(item.dataset.screen)));
  document.querySelectorAll('[data-goto]').forEach((item) => item.addEventListener('click', () => screen(item.dataset.goto)));

  $('theme-toggle').addEventListener('click', () => {
    const root = document.documentElement;
    const next = root.dataset.theme === 'vault' ? 'alabaster' : 'vault';
    root.dataset.theme = next;
    $('theme-toggle').textContent = next === 'vault' ? 'Alabaster Mode' : 'Vault Dark Mode';
  });

  $('auth-btn').addEventListener('click', async () => {
    if (state.user) {
      await api('auth/logout', { method: 'POST', body: '{}' });
      state.user = null;
      renderAuthState();
      notify('Signed out.');
    } else {
      $('auth-dialog').showModal();
    }
  });
  $('cancel-auth').addEventListener('click', () => $('auth-dialog').close());
  $('auth-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const fields = Object.fromEntries(new FormData(e.currentTarget));
    try {
      const res = await api('auth/login', { method: 'POST', body: JSON.stringify(fields) });
      state.user = res.user;
      $('auth-dialog').close();
      renderAuthState();
      notify(`Authenticated as ${res.user.username} (${res.user.role}).`);
    } catch (err) { notify(err.message); }
  });

  for (const id of ['new-project-top', 'new-project-inline']) {
    $(id).addEventListener('click', () => $('create-dialog').showModal());
  }
  $('cancel-create').addEventListener('click', () => $('create-dialog').close());
  $('create-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const form = e.currentTarget;
    const fields = Object.fromEntries(new FormData(form));
    try {
      const project = await api('projects', { method: 'POST', body: JSON.stringify(fields) });
      form.reset();
      $('create-dialog').close();
      await loadProjects();
      await openProject(project.id);
      notify('Mandate created. Run the 8-department AI Creative Director or rank directions.');
    } catch (err) { notify(err.message); }
  });

  $('brand-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const f = Object.fromEntries(new FormData(e.currentTarget));
    const payload = {
      identity: { firm_name: f.firm_name, principal: f.principal, principal_title: f.principal_title, subline: f.subline, website: f.website, email: f.email, positioning: f.positioning },
      palette: { gold: f.gold, obsidian: f.obsidian, alabaster: f.alabaster },
      typography: { display_font: f.display_font, body_font: f.body_font, numeric_font: f.numeric_font },
    };
    try {
      state.brand = await api('brand', { method: 'PUT', body: JSON.stringify(payload) });
      applyBrandToUI(state.brand);
      notify('Global Brand Contract v2.1.0 validated and saved.');
    } catch (err) { notify(err.message); }
  });

  $('reset-brand-btn').addEventListener('click', async () => {
    try {
      state.brand = await api('brand/reset', { method: 'POST', body: '{}' });
      applyBrandToUI(state.brand);
      notify('Global Brand Kit reset to Sovereign v2.1 defaults.');
    } catch (err) { notify(err.message); }
  });

  $('settlement-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const form = e.currentTarget;
    const fields = Object.fromEntries(new FormData(form));
    try {
      await api('settlements', { method: 'POST', body: JSON.stringify(fields) });
      form.reset();
      notify('Pending settlement record created. Verify recipient before Principal approval.');
      await loadSettlementsAndAudit();
    } catch (err) { notify(err.message); }
  });

  $('backup-db-btn').addEventListener('click', async () => {
    try {
      const res = await api('admin/backup', { method: 'POST', body: '{}' });
      notify(`SQLite online backup created: ${res.backup} (${res.bytes} bytes).`);
      await loadSettlementsAndAudit();
    } catch (err) { notify(err.message); }
  });

  $('asset-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const fields = Object.fromEntries(new FormData(e.currentTarget));
    try {
      const asset = await api('production/assets', { method: 'POST', body: JSON.stringify(fields) });
      notify(`Asset generated: ${asset.filename} (SHA-256 ${asset.sha256.slice(0, 12)}…)`);
      await loadProductionAndQA();
    } catch (err) { notify(err.message); }
  });

  $('repo-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const fields = Object.fromEntries(new FormData(e.currentTarget));
    try {
      const rep = await api('production/inspect-repo', { method: 'POST', body: JSON.stringify(fields) });
      const target = clear($('repo-report'));
      target.append(
        el('div', 'advisory-box', `Framework: ${rep.framework_detected} · Package Manager: ${rep.package_manager} · ${rep.preservation_guarantee}`),
        el('p', 'section-intro', rep.recommended_integration_steps.join(' | '))
      );
      notify(`Inspected repository (${rep.framework_detected}).`);
    } catch (err) { notify(err.message); }
  });

  $('run-qa-btn').addEventListener('click', async () => {
    try {
      notify('Running live Headless Chrome, Security, Accessibility & Performance QA audit…');
      const report = await api('qa/run', { method: 'POST', body: '{}' });
      notify(`Automated QA complete: ${report.score}/100 (${report.passed_checks}/${report.total_checks} checks passed).`);
      await loadProductionAndQA();
    } catch (err) { notify(err.message); }
  });

  $('envato-search-btn').addEventListener('click', runEnvatoSearch);
  $('envato-search-form').addEventListener('submit', (e) => { e.preventDefault(); runEnvatoSearch(); });

  renderQuality();
  renderIntegrations();

  try {
    const [me, styles, components, brand, industries, departments, validation] = await Promise.all([
      api('auth/me'),
      api('styles'),
      api('components'),
      api('brand'),
      api('industries'),
      api('agents'),
      api('contracts/validate'),
    ]);
    state.user = me.user;
    state.styles = styles;
    state.components = components;
    state.brand = brand;
    state.industries = industries;
    state.departments = departments;
    renderAuthState();
    renderStyles();
    renderComponentsRegistry();
    renderOrchestratorCatalog();
    applyBrandToUI(brand);
    $('contract-badge').textContent = validation.valid ? `CONTRACT v${validation.contract_version} VALID` : 'CONTRACT ERROR';
    await loadProjects();
  } catch (err) {
    notify('Cannot connect to Sovereign engine: ' + err.message);
  }
}

start();
