#!/usr/bin/env python3
"""
WPEX Orchestrator — Design System
CSS globale, icone SVG (Lucide), e landing page HTML.
"""

# ────────────────────────────────────────────
# SVG ICON SYSTEM  (Lucide Icons — MIT License)
# ────────────────────────────────────────────

_ICONS = {
    "server": '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="20" height="8" x="2" y="2" rx="2" ry="2"/><rect width="20" height="8" x="2" y="14" rx="2" ry="2"/><line x1="6" x2="6.01" y1="6" y2="6"/><line x1="6" x2="6.01" y1="18" y2="18"/></svg>',
    "key": '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.778 7.778 5.5 5.5 0 0 1 7.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4"/></svg>',
    "play": '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="6 3 20 12 6 21 6 3"/></svg>',
    "stop": '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="16" height="16" x="4" y="4" rx="2"/></svg>',
    "trash": '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 6h18"/><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/></svg>',
    "settings": '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/><circle cx="12" cy="12" r="3"/></svg>',
    "eye": '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M2.062 12.348a1 1 0 0 1 0-.696 10.75 10.75 0 0 1 19.876 0 1 1 0 0 1 0 .696 10.75 10.75 0 0 1-19.876 0"/><circle cx="12" cy="12" r="3"/></svg>',
    "save": '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M15.2 3a2 2 0 0 1 1.4.6l3.8 3.8a2 2 0 0 1 .6 1.4V19a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2z"/><path d="M17 21v-7a1 1 0 0 0-1-1H8a1 1 0 0 0-1 1v7"/><path d="M7 3v4a1 1 0 0 0 1 1h7"/></svg>',
    "plus": '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14"/><path d="M12 5v14"/></svg>',
    "arrow-left": '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m12 19-7-7 7-7"/><path d="M19 12H5"/></svg>',
    "log-in": '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4"/><polyline points="10 17 15 12 10 7"/><line x1="15" x2="3" y1="12" y2="12"/></svg>',
    "user-plus": '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><line x1="19" x2="19" y1="8" y2="14"/><line x1="22" x2="16" y1="11" y2="11"/></svg>',
    "user": '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>',
    "log-out": '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" x2="9" y1="12" y2="12"/></svg>',
    "shield": '<svg xmlns="http://www.w3.org/2000/svg" width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z"/></svg>',
    "zap": '<svg xmlns="http://www.w3.org/2000/svg" width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M4 14a1 1 0 0 1-.78-1.63l9.9-10.2a.5.5 0 0 1 .86.46l-1.92 6.02A1 1 0 0 0 13 10h7a1 1 0 0 1 .78 1.63l-9.9 10.2a.5.5 0 0 1-.86-.46l1.92-6.02A1 1 0 0 0 11 14z"/></svg>',
    "globe": '<svg xmlns="http://www.w3.org/2000/svg" width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20"/><path d="M2 12h20"/></svg>',
    "lock": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="18" height="11" x="3" y="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>',
    "layout-dashboard": '<svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="7" height="9" x="3" y="3" rx="1"/><rect width="7" height="5" x="14" y="3" rx="1"/><rect width="7" height="9" x="14" y="12" rx="1"/><rect width="7" height="5" x="3" y="16" rx="1"/></svg>',
    "database": '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M3 5V19A9 3 0 0 0 21 19V5"/><path d="M3 12A9 3 0 0 0 21 12"/></svg>',
    "alert-circle": '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" x2="12" y1="8" y2="12"/><line x1="12" x2="12.01" y1="16" y2="16"/></svg>',
    "monitor": '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="20" height="14" x="2" y="3" rx="2"/><line x1="8" x2="16" y1="21" y2="21"/><line x1="12" x2="12" y1="17" y2="21"/></svg>',
    "terminal": '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="4 17 10 11 4 5"/><line x1="12" x2="20" y1="19" y2="19"/></svg>',
    "refresh-cw": '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8"/><path d="M21 3v5h-5"/><path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16"/><path d="M8 16H3v5"/></svg>',
}


def icon(name: str, size: int = 0) -> str:
    """Return inline SVG HTML for a Lucide icon by name."""
    svg = _ICONS.get(name, "")
    if size and svg:
        svg = svg.replace('width="18"', f'width="{size}"').replace('height="18"', f'height="{size}"')
        svg = svg.replace('width="16"', f'width="{size}"').replace('height="16"', f'height="{size}"')
    return f'<span class="wpex-icon">{svg}</span>'


def icon_raw(name: str) -> str:
    """Return raw SVG string (no wrapper span)."""
    return _ICONS.get(name, "")


# ────────────────────────────────────────────
# STATUS INDICATORS
# ────────────────────────────────────────────

def status_dot(status: str) -> str:
    """Return an animated status dot HTML."""
    if status == "running":
        return '<span class="status-dot status-running"></span>'
    elif status in ("exited", "stopped"):
        return '<span class="status-dot status-stopped"></span>'
    else:
        return '<span class="status-dot status-unknown"></span>'


# ────────────────────────────────────────────
# GLOBAL CSS
# ────────────────────────────────────────────

GLOBAL_CSS = """
<style>
    /* ── Google Font ─────────────────────── */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    /* ── CSS Variables ───────────────────── */
    :root {
        --bg-primary:    #0d0d1a;
        --bg-secondary:  #141428;
        --bg-card:       rgba(255, 255, 255, 0.04);
        --bg-card-hover: rgba(255, 255, 255, 0.07);
        --border-subtle: rgba(255, 255, 255, 0.08);
        --border-focus:  rgba(124, 106, 239, 0.5);
        --accent:        #7c6aef;
        --accent-soft:   #9b8afb;
        --accent-glow:   rgba(124, 106, 239, 0.25);
        --text-primary:  #e8e8f0;
        --text-secondary:#9090a8;
        --text-muted:    #606078;
        --success:       #34d399;
        --danger:        #f87171;
        --warning:       #fbbf24;
        --radius:        14px;
        --radius-sm:     8px;
        --shadow-card:   0 4px 24px rgba(0, 0, 0, 0.3);
        --shadow-hover:  0 8px 32px rgba(124, 106, 239, 0.15);
        --transition:    all 0.25s cubic-bezier(.4,0,.2,1);
    }

    /* ── Base ────────────────────────────── */
    html, body, .stApp, [data-testid="stAppViewContainer"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
        color: var(--text-primary) !important;
    }
    
    .stApp {
        background: linear-gradient(145deg, var(--bg-primary) 0%, var(--bg-secondary) 100%) !important;
    }

    /* ── Hide Streamlit defaults ─────────── */
    header[data-testid="stHeader"] { display: none !important; }
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    .stDeployButton { display: none !important; }

    /* ── Sidebar ─────────────────────────── */
    section[data-testid="stSidebar"] {
        background: var(--bg-secondary) !important;
        border-right: 1px solid var(--border-subtle) !important;
    }
    section[data-testid="stSidebar"] .stMarkdown p {
        color: var(--text-secondary) !important;
    }

    /* ── Tabs ────────────────────────────── */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background: transparent;
        border-bottom: 1px solid var(--border-subtle);
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: var(--radius-sm) var(--radius-sm) 0 0;
        padding: 10px 20px;
        color: var(--text-secondary);
        font-weight: 500;
        transition: var(--transition);
    }
    .stTabs [data-baseweb="tab"]:hover {
        color: var(--accent-soft);
        background: var(--bg-card);
    }
    .stTabs [aria-selected="true"] {
        color: var(--accent) !important;
        border-bottom: 2px solid var(--accent) !important;
        background: var(--bg-card) !important;
    }

    /* ── Cards (generic container) ───────── */
    div[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlockBorderWrapper"] {
        background: var(--bg-card) !important;
        border: 1px solid var(--border-subtle) !important;
        border-radius: var(--radius) !important;
        padding: 0 !important;
        transition: var(--transition);
    }
    div[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlockBorderWrapper"]:hover {
        border-color: rgba(124, 106, 239, 0.2) !important;
        box-shadow: var(--shadow-hover);
    }

    /* ── Expanders ───────────────────────── */
    .streamlit-expanderHeader {
        font-size: 0.9em;
        font-weight: 500;
        color: var(--text-secondary) !important;
        border-radius: var(--radius-sm);
    }
    details[data-testid="stExpander"] {
        background: var(--bg-card) !important;
        border: 1px solid var(--border-subtle) !important;
        border-radius: var(--radius) !important;
    }

    /* ── Buttons ─────────────────────────── */
    .stButton > button {
        border-radius: var(--radius-sm) !important;
        font-weight: 500 !important;
        font-family: 'Inter', sans-serif !important;
        padding: 8px 20px !important;
        transition: var(--transition) !important;
        border: 1px solid var(--border-subtle) !important;
        background: var(--bg-card) !important;
        color: var(--text-primary) !important;
    }
    .stButton > button:hover {
        border-color: var(--accent) !important;
        background: var(--accent-glow) !important;
        color: var(--accent-soft) !important;
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(124, 106, 239, 0.2) !important;
    }
    .stButton > button[kind="primary"],
    .stButton > button[data-testid="stFormSubmitButton"] {
        background: linear-gradient(135deg, var(--accent), #6355d8) !important;
        color: white !important;
        border: none !important;
    }
    .stButton > button[kind="primary"]:hover {
        box-shadow: 0 6px 20px var(--accent-glow) !important;
        transform: translateY(-2px);
    }

    /* ── Inputs ──────────────────────────── */
    .stTextInput > div > div > input,
    .stNumberInput > div > div > input,
    .stSelectbox > div > div,
    .stMultiSelect > div > div {
        border-radius: var(--radius-sm) !important;
        border: 1px solid var(--border-subtle) !important;
        background: rgba(255, 255, 255, 0.03) !important;
        color: var(--text-primary) !important;
        transition: var(--transition) !important;
    }
    .stTextInput > div > div > input:focus,
    .stNumberInput > div > div > input:focus {
        border-color: var(--accent) !important;
        box-shadow: 0 0 0 3px var(--accent-glow) !important;
    }

    /* ── Form Submit Buttons ─────────────── */
    [data-testid="stFormSubmitButton"] > button {
        background: linear-gradient(135deg, var(--accent), #6355d8) !important;
        color: white !important;
        border: none !important;
        width: 100%;
    }
    [data-testid="stFormSubmitButton"] > button:hover {
        box-shadow: 0 6px 20px var(--accent-glow) !important;
        transform: translateY(-2px);
    }

    /* ── Secret Hover (key values) ───────── */
    .secret-hover {
        background-color: rgba(255, 255, 255, 0.06);
        color: rgba(255, 255, 255, 0.06);
        border-radius: var(--radius-sm);
        padding: 5px 12px;
        font-family: 'JetBrains Mono', monospace;
        transition: var(--transition);
        cursor: text;
        user-select: all;
        border: 1px solid var(--border-subtle);
        font-size: 0.85em;
    }
    .secret-hover:hover {
        background-color: rgba(124, 106, 239, 0.1);
        color: var(--success);
        border-color: var(--success);
    }

    /* ── Status dots ─────────────────────── */
    .status-dot {
        display: inline-block;
        width: 10px;
        height: 10px;
        border-radius: 50%;
        margin-right: 6px;
        vertical-align: middle;
    }
    .status-running {
        background: var(--success);
        box-shadow: 0 0 8px var(--success);
        animation: pulse-green 2s ease-in-out infinite;
    }
    .status-stopped {
        background: var(--danger);
        box-shadow: 0 0 4px rgba(248, 113, 113, 0.4);
    }
    .status-unknown {
        background: var(--text-muted);
    }

    @keyframes pulse-green {
        0%, 100% { box-shadow: 0 0 4px var(--success); }
        50%      { box-shadow: 0 0 14px var(--success), 0 0 24px rgba(52, 211, 153, 0.3); }
    }

    /* ── Icon helper ─────────────────────── */
    .wpex-icon {
        display: inline-flex;
        align-items: center;
        vertical-align: middle;
        margin-right: 4px;
    }
    .wpex-icon svg {
        vertical-align: middle;
    }

    /* ── Dividers ─────────────────────────── */
    hr {
        border: none !important;
        border-top: 1px solid var(--border-subtle) !important;
        margin: 16px 0 !important;
    }

    /* ── Toasts ──────────────────────────── */
    [data-testid="stToast"] {
        border-radius: var(--radius-sm) !important;
        backdrop-filter: blur(10px);
    }

    /* ── Code blocks ─────────────────────── */
    .stCodeBlock {
        border-radius: var(--radius-sm) !important;
        border: 1px solid var(--border-subtle) !important;
    }

    /* ── Server card title ───────────────── */
    .server-title {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 1.15em;
        font-weight: 600;
        color: var(--text-primary);
        margin: 0;
    }

    /* ── Login page overrides ─────────────── */
    .login-card {
        max-width: 420px;
        margin: 60px auto;
        padding: 2.5rem;
        border-radius: 20px;
        background: rgba(255, 255, 255, 0.04);
        backdrop-filter: blur(16px);
        border: 1px solid var(--border-subtle);
        box-shadow: 0 16px 48px rgba(0, 0, 0, 0.4);
    }
    .login-title {
        text-align: center;
        font-size: 1.8em;
        font-weight: 700;
        margin-bottom: 0.5rem;
        color: var(--text-primary);
    }
    .login-subtitle {
        text-align: center;
        color: var(--text-secondary);
        font-size: 0.9em;
        margin-bottom: 2rem;
    }

    /* ── Metric / info labels ────────────── */
    .info-badge {
        display: inline-block;
        padding: 3px 10px;
        border-radius: 20px;
        font-size: 0.78em;
        font-weight: 500;
        background: var(--bg-card);
        border: 1px solid var(--border-subtle);
        color: var(--text-secondary);
        margin-right: 6px;
    }
    .info-badge-accent {
        background: var(--accent-glow);
        border-color: rgba(124, 106, 239, 0.3);
        color: var(--accent-soft);
    }
</style>
"""

# ────────────────────────────────────────────
# LANDING PAGE HTML
# ────────────────────────────────────────────

LANDING_HTML = """
<style>
    .landing-wrapper {
        max-width: 960px;
        margin: 0 auto;
        padding: 40px 20px;
        text-align: center;
    }

    /* Hero */
    .hero {
        padding: 80px 0 60px;
    }
    .hero-badge {
        display: inline-block;
        padding: 6px 16px;
        border-radius: 20px;
        font-size: 0.8em;
        font-weight: 500;
        background: rgba(124, 106, 239, 0.12);
        color: #9b8afb;
        border: 1px solid rgba(124, 106, 239, 0.25);
        margin-bottom: 24px;
        letter-spacing: 0.5px;
    }
    .hero h1 {
        font-family: 'Inter', sans-serif;
        font-size: 3.2em;
        font-weight: 700;
        line-height: 1.15;
        color: #e8e8f0;
        margin: 0 0 20px;
    }
    .hero h1 .gradient-text {
        background: linear-gradient(135deg, #7c6aef, #a78bfa, #34d399);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    .hero p {
        font-size: 1.15em;
        color: #9090a8;
        max-width: 560px;
        margin: 0 auto 40px;
        line-height: 1.7;
    }
    .hero-cta {
        display: inline-block;
        padding: 14px 36px;
        border-radius: 12px;
        background: linear-gradient(135deg, #7c6aef, #6355d8);
        color: white !important;
        text-decoration: none;
        font-weight: 600;
        font-size: 1.05em;
        transition: all 0.3s cubic-bezier(.4,0,.2,1);
        box-shadow: 0 4px 16px rgba(124, 106, 239, 0.3);
    }
    .hero-cta:hover {
        transform: translateY(-3px);
        box-shadow: 0 8px 28px rgba(124, 106, 239, 0.45);
    }

    /* Features */
    .features {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 24px;
        margin: 60px 0;
    }
    .feature-card {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.07);
        border-radius: 16px;
        padding: 32px 24px;
        text-align: left;
        transition: all 0.3s ease;
    }
    .feature-card:hover {
        background: rgba(255, 255, 255, 0.06);
        border-color: rgba(124, 106, 239, 0.2);
        transform: translateY(-4px);
        box-shadow: 0 12px 32px rgba(0, 0, 0, 0.3);
    }
    .feature-icon {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 56px;
        height: 56px;
        border-radius: 14px;
        margin-bottom: 18px;
    }
    .feature-icon.icon-purple {
        background: rgba(124, 106, 239, 0.12);
        color: #9b8afb;
    }
    .feature-icon.icon-green {
        background: rgba(52, 211, 153, 0.12);
        color: #34d399;
    }
    .feature-icon.icon-blue {
        background: rgba(96, 165, 250, 0.12);
        color: #60a5fa;
    }
    .feature-card h3 {
        font-family: 'Inter', sans-serif;
        font-size: 1.1em;
        font-weight: 600;
        color: #e8e8f0;
        margin: 0 0 10px;
    }
    .feature-card p {
        font-size: 0.9em;
        color: #9090a8;
        line-height: 1.6;
        margin: 0;
    }

    /* Footer */
    .landing-footer {
        padding: 30px 0;
        border-top: 1px solid rgba(255, 255, 255, 0.06);
        color: #606078;
        font-size: 0.8em;
    }

    /* Responsive */
    @media (max-width: 768px) {
        .hero h1 { font-size: 2.2em; }
        .features { grid-template-columns: 1fr; }
    }
</style>

<div class="landing-wrapper">
    <div class="hero">
        <div class="hero-badge">WPEX Orchestrator v2</div>
        <h1>Gestisci i tuoi server<br/><span class="gradient-text">in modo semplice</span></h1>
        <p>Monitora, controlla e gestisci le tue istanze WPEX da un'unica dashboard moderna. Provisioning automatico, gestione chiavi integrata e monitoraggio in tempo reale.</p>
    </div>

    <div class="features">
        <div class="feature-card">
            <div class="feature-icon icon-purple">
                ICON_SHIELD
            </div>
            <h3>Sicurezza Integrata</h3>
            <p>Autenticazione JWT, chiavi crittografate con PGP e sessioni sicure con blacklist automatica.</p>
        </div>
        <div class="feature-card">
            <div class="feature-icon icon-green">
                ICON_ZAP
            </div>
            <h3>Deploy Istantaneo</h3>
            <p>Crea e avvia nuovi server con un click. Gestione Docker automatizzata con rete overlay condivisa.</p>
        </div>
        <div class="feature-card">
            <div class="feature-icon icon-blue">
                ICON_GLOBE
            </div>
            <h3>Monitoraggio Live</h3>
            <p>Console integrata con iframe live, log in tempo reale e controlli rapidi per ogni istanza.</p>
        </div>
    </div>

    <div class="landing-footer">
        WPEX Orchestrator &mdash; Built with Streamlit & Docker Swarm
    </div>
</div>
"""

# Replace placeholders with actual SVGs
LANDING_HTML = LANDING_HTML.replace("ICON_SHIELD", icon_raw("shield"))
LANDING_HTML = LANDING_HTML.replace("ICON_ZAP", icon_raw("zap"))
LANDING_HTML = LANDING_HTML.replace("ICON_GLOBE", icon_raw("globe"))
