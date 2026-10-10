"""
Configuration and Styling System for Zero-Waste Grocery
Theme: Sustainability-Tech (Emerald, Forest, Lime, Warm Cream, Coral, Purple)
"""

# Brand Color Palette
COLORS = {
    # Primary Greens
    "primary_dark": "#062E1E",     # Deep Forest Green
    "primary": "#0D472C",          # Rich Emerald
    "primary_light": "#10B981",    # Vibrant Emerald
    "accent_lime": "#84CC16",      # Fresh Lime (Eco vitality)
    "accent_lime_light": "#D9F99D",# Light Lime Tint
    
    # Warms & Alerts
    "cream_bg": "#FDFBF7",         # Warm Cream Background
    "cream_card": "#FFFFFF",       # Crisp White Card
    "coral_alert": "#EA580C",      # Coral Orange for Urgent Expiry
    "coral_light": "#FFEDD5",      # Coral light badge
    "amber_warn": "#D97706",       # Amber for medium risk
    "amber_light": "#FEF3C7",
    
    # AI & Agent Accents
    "ai_purple": "#7C3AED",        # Deep Royal Purple
    "ai_purple_light": "#8B5CF6",  # Bright Violet
    "ai_purple_bg": "#F5F3FF",     # Subtle Purple Tint
    "ai_purple_border": "#DDD6FE",
    
    # Neutrals
    "text_dark": "#0F172A",        # Slate 900
    "text_muted": "#475569",       # Slate 600
    "text_light": "#94A3B8",       # Slate 400
    "border_subtle": "#E2E8F0",    # Light border
    "border_green": "#A7F3D0",     # Subtle emerald border
}

# Custom CSS for Streamlit
CUSTOM_CSS = """
<style>
/* Import Google Fonts */
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=Space+Grotesk:wght@500;600;700&display=swap');

/* Root reset & typography */
html, body, [class*="css"] {
    font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
    color: #0F172A;
}

/* Hide Streamlit default chrome */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
.viewerBadge_container__1QSob {display: none !important;}

/* Background & main container padding */
.main .block-container {
    padding-top: 1.8rem;
    padding-bottom: 3rem;
    padding-left: 2.2rem;
    padding-right: 2.2rem;
    max-width: 1400px;
}

/* Sidebar styling */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #062E1E 0%, #0A3D27 60%, #083321 100%);
    border-right: 1px solid rgba(16, 185, 129, 0.2);
}

[data-testid="stSidebar"] .stMarkdown, 
[data-testid="stSidebar"] p, 
[data-testid="stSidebar"] span, 
[data-testid="stSidebar"] label {
    color: #E2E8F0 !important;
}

[data-testid="stSidebar"] h1, 
[data-testid="stSidebar"] h2, 
[data-testid="stSidebar"] h3 {
    color: #F8FAFC !important;
    font-family: 'Space Grotesk', sans-serif;
}

/* App Hero Banner */
.hero-card {
    background: linear-gradient(135deg, #062E1E 0%, #0A452C 45%, #064E3B 100%);
    border: 1px solid rgba(132, 204, 22, 0.3);
    border-radius: 16px;
    padding: 1.8rem 2.2rem;
    color: #FFFFFF;
    box-shadow: 0 10px 25px -5px rgba(6, 46, 30, 0.25);
    margin-bottom: 1.8rem;
    position: relative;
    overflow: hidden;
}

.hero-card::after {
    content: "";
    position: absolute;
    top: -40px;
    right: -40px;
    width: 200px;
    height: 200px;
    background: radial-gradient(circle, rgba(132, 204, 22, 0.25) 0%, rgba(132, 204, 22, 0) 70%);
    border-radius: 50%;
    pointer-events: none;
}

.hero-title {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 2.1rem;
    font-weight: 700;
    color: #FFFFFF;
    margin-bottom: 0.35rem;
    letter-spacing: -0.02em;
}

.hero-tag {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: rgba(132, 204, 22, 0.2);
    border: 1px solid rgba(132, 204, 22, 0.5);
    color: #D9F99D;
    font-size: 0.78rem;
    font-weight: 600;
    padding: 4px 10px;
    border-radius: 20px;
    margin-bottom: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

.hero-subtitle {
    color: #CBD5E1;
    font-size: 1.02rem;
    line-height: 1.5;
    max-width: 900px;
}

/* Glass & Clean Cards */
.custom-card {
    background: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 14px;
    padding: 1.4rem;
    box-shadow: 0 4px 12px rgba(15, 23, 42, 0.04);
    transition: transform 0.2s ease, box-shadow 0.2s ease;
    margin-bottom: 1.2rem;
}

.custom-card:hover {
    border-color: #10B981;
    box-shadow: 0 8px 20px rgba(16, 185, 129, 0.08);
}

.agent-card {
    background: #FFFFFF;
    border-left: 4px solid #7C3AED;
    border-top: 1px solid #EDE9FE;
    border-right: 1px solid #EDE9FE;
    border-bottom: 1px solid #EDE9FE;
    border-radius: 12px;
    padding: 1.2rem 1.4rem;
    box-shadow: 0 4px 12px rgba(124, 58, 237, 0.05);
    margin-bottom: 1rem;
}

/* KPI Card */
.kpi-container {
    background: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 14px;
    padding: 1.25rem 1.4rem;
    box-shadow: 0 4px 10px rgba(15, 23, 42, 0.03);
    position: relative;
    overflow: hidden;
}

.kpi-title {
    font-size: 0.82rem;
    font-weight: 600;
    color: #64748B;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    margin-bottom: 0.4rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
}

.kpi-value {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 2rem;
    font-weight: 700;
    color: #0F172A;
    line-height: 1.1;
    margin-bottom: 0.35rem;
}

.kpi-trend {
    font-size: 0.8rem;
    font-weight: 600;
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 2px 8px;
    border-radius: 12px;
}

.trend-positive {
    background: #DCFCE7;
    color: #15803D;
}

.trend-neutral {
    background: #FEF3C7;
    color: #B45309;
}

.trend-alert {
    background: #FEE2E2;
    color: #B91C1C;
}

/* Badges */
.badge {
    display: inline-block;
    padding: 3px 9px;
    border-radius: 12px;
    font-size: 0.75rem;
    font-weight: 600;
    letter-spacing: 0.02em;
}

.badge-reorder {
    background: #E0E7FF;
    color: #4338CA;
    border: 1px solid #C7D2FE;
}

.badge-markdown {
    background: #FFEDD5;
    color: #C2410C;
    border: 1px solid #FDBA74;
}

.badge-transfer {
    background: #F3E8FF;
    color: #6B21A8;
    border: 1px solid #D8B4FE;
}

.badge-donate {
    background: #FEF9C3;
    color: #854D0E;
    border: 1px solid #FDE047;
}

.badge-keep {
    background: #DCFCE7;
    color: #166534;
    border: 1px solid #BBF7D0;
}

/* Buttons */
.stButton > button {
    border-radius: 10px;
    font-weight: 600;
    font-family: 'Plus Jakarta Sans', sans-serif;
    border: none;
    transition: all 0.2s ease;
}

.stButton > button:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(16, 185, 129, 0.2);
}

/* Status dots */
.status-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    display: inline-block;
    margin-right: 6px;
}

.dot-green { background: #10B981; }
.dot-amber { background: #F59E0B; }
.dot-red { background: #EF4444; }
.dot-purple { background: #8B5CF6; }

/* Custom section headers */
.section-header {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 1.35rem;
    font-weight: 700;
    color: #062E1E;
    margin-top: 1rem;
    margin-bottom: 0.8rem;
    display: flex;
    align-items: center;
    gap: 8px;
}

/* Agent Pill */
.agent-pill {
    background: #F5F3FF;
    color: #6D28D9;
    border: 1px solid #DDD6FE;
    padding: 3px 10px;
    border-radius: 20px;
    font-size: 0.78rem;
    font-weight: 600;
    display: inline-flex;
    align-items: center;
    gap: 5px;
}

/* Landing Page Hero Specifics */
.landing-hero {
    background: linear-gradient(135deg, #062E1E 0%, #0D472C 50%, #064E3B 100%);
    border: 1px solid rgba(132, 204, 22, 0.35);
    border-radius: 20px;
    padding: 2.5rem 2.8rem;
    color: #FFFFFF;
    box-shadow: 0 16px 36px -8px rgba(6, 46, 30, 0.35);
    margin-bottom: 2rem;
    position: relative;
    overflow: hidden;
}

.landing-hero::before {
    content: "";
    position: absolute;
    top: -60px;
    right: -40px;
    width: 280px;
    height: 280px;
    background: radial-gradient(circle, rgba(163, 230, 53, 0.18) 0%, rgba(16, 185, 129, 0.05) 60%, transparent 75%);
    border-radius: 50%;
    pointer-events: none;
}

.landing-title {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 2.7rem;
    font-weight: 800;
    color: #FFFFFF;
    line-height: 1.15;
    letter-spacing: -0.03em;
    margin-bottom: 0.8rem;
}

.landing-highlight {
    background: linear-gradient(120deg, #A3E635 0%, #34D399 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}

.landing-subtitle {
    color: #E2E8F0;
    font-size: 1.15rem;
    line-height: 1.6;
    max-width: 820px;
    margin-bottom: 1.5rem;
}

/* 4 Overview Metric Cards */
.metric-card-overview {
    background: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 16px;
    padding: 1.4rem 1.5rem;
    box-shadow: 0 4px 14px rgba(15, 23, 42, 0.04);
    transition: transform 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease;
    height: 100%;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
}

.metric-card-overview:hover {
    transform: translateY(-2px);
    box-shadow: 0 10px 24px rgba(16, 185, 129, 0.10);
    border-color: #10B981;
}

.overview-card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 0.6rem;
}

.overview-card-label {
    font-size: 0.85rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: #475569;
}

.overview-card-icon {
    width: 36px;
    height: 36px;
    border-radius: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.15rem;
}

.overview-card-value {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 2.3rem;
    font-weight: 800;
    color: #0F172A;
    line-height: 1.1;
    margin-bottom: 0.35rem;
}

.overview-card-sub {
    font-size: 0.82rem;
    color: #64748B;
    line-height: 1.4;
}

.overview-empty-state {
    color: #94A3B8;
    font-style: italic;
    font-size: 0.92rem;
    padding: 0.6rem 0;
}

/* How It Works Step Cards */
.step-card {
    background: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 16px;
    padding: 1.6rem;
    box-shadow: 0 4px 12px rgba(15, 23, 42, 0.03);
    position: relative;
    height: 100%;
}

.step-card:hover {
    border-color: #A3E635;
    box-shadow: 0 8px 20px rgba(132, 204, 22, 0.12);
}

.step-number {
    position: absolute;
    top: -14px;
    left: 20px;
    background: linear-gradient(135deg, #062E1E 0%, #10B981 100%);
    color: #FFFFFF;
    font-family: 'Space Grotesk', sans-serif;
    font-size: 0.85rem;
    font-weight: 800;
    width: 32px;
    height: 32px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    border: 2px solid #FFFFFF;
    box-shadow: 0 4px 8px rgba(6, 46, 30, 0.2);
}

.step-title {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 1.15rem;
    font-weight: 700;
    color: #062E1E;
    margin-top: 0.6rem;
    margin-bottom: 0.4rem;
}

.step-desc {
    font-size: 0.88rem;
    color: #475569;
    line-height: 1.5;
}

/* Sustainability Callout Box */
.sustainability-box {
    background: linear-gradient(135deg, #F0FDF4 0%, #ECFDF5 50%, #F5F3FF 100%);
    border: 1px solid #A7F3D0;
    border-left: 6px solid #10B981;
    border-radius: 16px;
    padding: 1.8rem 2rem;
    margin-top: 1.8rem;
    box-shadow: 0 4px 16px rgba(16, 185, 129, 0.06);
}

.sustainability-header {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 1.3rem;
    font-weight: 700;
    color: #064E3B;
    margin-bottom: 0.6rem;
    display: flex;
    align-items: center;
    gap: 10px;
}

.sustainability-content {
    font-size: 0.95rem;
    color: #1E293B;
    line-height: 1.6;
}
</style>

"""

# App Constants
APP_TITLE = "Zero-Waste Grocery"
APP_SUBTITLE = "Agentic AI Approach to Perishable Demand & Shelf-Life Management"
HACKATHON_EVENT = "GDGoC HITAM · Agentic AI Hackathon (Sustainability Track)"
VERSION = "v2.6 Enterprise Edition"
