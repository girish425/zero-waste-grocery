"""
Reusable UI Components for Zero-Waste Grocery
Provides executive-grade visual hierarchy, custom metric cards, badges, and status elements.
"""
import streamlit as st

def render_hero(title: str, subtitle: str, badge_text: str = "AGENTIC AI SUSTAINABILITY"):
    """Renders the top executive hero banner."""
    st.markdown(f"""
    <div class="hero-card">
        <div class="hero-tag">⚡ {badge_text}</div>
        <div class="hero-title">{title}</div>
        <div class="hero-subtitle">{subtitle}</div>
    </div>
    """, unsafe_allow_html=True)

def render_kpi_card(
    title: str,
    value: str,
    subtitle: str = "",
    trend_text: str = "",
    trend_type: str = "positive", # 'positive', 'neutral', 'alert'
    icon: str = "🌱"
):
    """Renders a polished KPI card with custom metrics and trend pill."""
    trend_class = {
        "positive": "trend-positive",
        "neutral": "trend-neutral",
        "alert": "trend-alert"
    }.get(trend_type, "trend-positive")
    
    trend_html = f'<div class="kpi-trend {trend_class}">{trend_text}</div>' if trend_text else ''
    
    st.markdown(f"""
    <div class="kpi-container">
        <div class="kpi-title">
            <span>{icon} {title}</span>
            {trend_html}
        </div>
        <div class="kpi-value">{value}</div>
        <div style="font-size: 0.8rem; color: #64748B;">{subtitle}</div>
    </div>
    """, unsafe_allow_html=True)

def get_action_badge_html(action: str) -> str:
    """Returns styled HTML badge for an agent action."""
    action = action.upper()
    if "MARKDOWN" in action:
        return '<span class="badge badge-markdown">🏷️ Dynamic Markdown</span>'
    elif "TRANSFER" in action:
        return '<span class="badge badge-transfer">🚚 Inter-Store Transfer</span>'
    elif "REORDER" in action:
        return '<span class="badge badge-reorder">📦 Auto-PO Restock</span>'
    elif "DONATE" in action:
        return '<span class="badge badge-donate">💛 Food Bank Donation</span>'
    else:
        return '<span class="badge badge-keep">✅ Nominal Velocity</span>'

def get_urgency_badge_html(urgency: str) -> str:
    """Returns styled HTML badge for an urgency status."""
    urgency = urgency.upper()
    if urgency == "CRITICAL":
        return '<span class="badge" style="background:#FEE2E2; color:#B91C1C; border:1px solid #FCA5A5;">🔴 CRITICAL (≤ 24h)</span>'
    elif urgency == "HIGH":
        return '<span class="badge" style="background:#FFEDD5; color:#C2410C; border:1px solid #FDBA74;">🟠 HIGH (≤ 48h)</span>'
    elif urgency == "MEDIUM":
        return '<span class="badge" style="background:#FEF3C7; color:#B45309; border:1px solid #FDE68A;">🟡 MEDIUM</span>'
    elif urgency in ["UNKNOWN", "EXPIRY_UNSPECIFIED"]:
        return '<span class="badge" style="background:#F1F5F9; color:#475569; border:1px solid #CBD5E1;">⚪ EXPIRY UNSPECIFIED</span>'
    else:
        return '<span class="badge" style="background:#DCFCE7; color:#15803D; border:1px solid #86EFAC;">🟢 LOW RISK</span>'


def render_agent_thought_step(step: str, agent_name: str, thought: str, timestamp: str = ""):
    """Renders a single step in the agent Chain-of-Thought (CoT) reasoning audit trail."""
    st.markdown(f"""
    <div style="display:flex; gap:12px; margin-bottom:10px; align-items:flex-start; font-size:0.88rem;">
        <div style="min-width:70px; font-family:'Space Grotesk', monospace; color:#64748B; font-size:0.75rem; padding-top:2px;">
            {timestamp}
        </div>
        <div style="flex-grow:1; background:#F8FAFC; border-left:3px solid #7C3AED; padding:8px 12px; border-radius:0 8px 8px 0; border-top:1px solid #E2E8F0; border-right:1px solid #E2E8F0; border-bottom:1px solid #E2E8F0;">
            <div style="display:flex; justify-content:space-between; margin-bottom:3px;">
                <span style="font-weight:700; color:#4338CA; font-size:0.8rem;">{agent_name}</span>
                <span style="font-family:monospace; background:#EDE9FE; color:#6D28D9; font-size:0.7rem; padding:1px 6px; border-radius:4px;">{step}</span>
            </div>
            <div style="color:#1E293B; line-height:1.4;">{thought}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

def render_landing_hero_banner():
    """Renders the top executive landing hero with main headline and supporting value proposition."""
    st.markdown("""
    <div class="landing-hero">
        <div class="hero-tag">⚡ AGENTIC AI SUSTAINABILITY PLATFORM</div>
        <div class="landing-title">
            Smarter Grocery. <span class="landing-highlight">Less Waste.</span>
        </div>
        <div class="landing-subtitle">
            Zero-Waste Grocery helps supermarket managers and inventory planners predict perishable demand, 
            detect shelf-life hazards before spoilage occurs, and take proactive markdown and transfer decisions 
            to protect retail margins and divert edible food from landfills.
        </div>
    </div>
    """, unsafe_allow_html=True)

def render_overview_card(
    label: str,
    value: str = None,
    subtext: str = "",
    icon: str = "📦",
    icon_bg: str = "#DCFCE7",
    is_empty: bool = False
):
    """Renders one of the four attractive overview cards with real values or elegant empty state."""
    if is_empty or value is None:
        value_html = '<div class="overview-empty-state">Upload data to begin.</div>'
        subtext_html = '<div class="overview-card-sub" style="color:#94A3B8;">Awaiting store inventory feed</div>'
    else:
        value_html = f'<div class="overview-card-value">{value}</div>'
        subtext_html = f'<div class="overview-card-sub">{subtext}</div>'

    st.markdown(f"""
    <div class="metric-card-overview">
        <div class="overview-card-header">
            <span class="overview-card-label">{label}</span>
            <div class="overview-card-icon" style="background:{icon_bg};">
                {icon}
            </div>
        </div>
        {value_html}
        {subtext_html}
    </div>
    """, unsafe_allow_html=True)

def render_how_it_works_section():
    """Renders the 3-step 'How It Works' workflow cards."""
    st.markdown("""
    <div style="margin: 2.2rem 0 1rem 0;">
        <div style="font-family:'Space Grotesk', sans-serif; font-size:1.45rem; font-weight:700; color:#062E1E; display:flex; align-items:center; gap:8px;">
            🔄 How Zero-Waste Grocery Works
        </div>
        <div style="font-size:0.9rem; color:#64748B; margin-top:2px;">
            A three-step autonomous workflow from store data ingestion to downstream operational execution.
        </div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div class="step-card">
            <div class="step-number">1</div>
            <div style="font-size:1.6rem; margin-top:0.4rem;">📤</div>
            <div class="step-title">Upload Store Data</div>
            <div class="step-desc">
                Connect live or batch inventory feeds via Excel or CSV, containing SKU codes, current shelf quantities, batch receipt dates, and cold-chain sensor temperatures.
            </div>
        </div>
        """, unsafe_allow_html=True)
        
    with col2:
        st.markdown("""
        <div class="step-card">
            <div class="step-number">2</div>
            <div style="font-size:1.6rem; margin-top:0.4rem;">🤖</div>
            <div class="step-title">Analyze with AI Agents</div>
            <div class="step-desc">
                Specialized agents forecast consumer demand velocity, evaluate biological Arrhenius decay hazard, calculate safety stock, and assess network inter-store balancing.
            </div>
        </div>
        """, unsafe_allow_html=True)
        
    with col3:
        st.markdown("""
        <div class="step-card">
            <div class="step-number">3</div>
            <div style="font-size:1.6rem; margin-top:0.4rem;">✅</div>
            <div class="step-title">Review Recommendations</div>
            <div class="step-desc">
                A Chief Coordinator arbitrates proposals into a single actionable decision per SKU. Inventory planners review, approve, or override actions with full explainability.
            </div>
        </div>
        """, unsafe_allow_html=True)

def render_sustainability_callout():
    """Renders the sustainability-focused section grounded in real-world retail facts without fake stats."""
    st.markdown("""
    <div class="sustainability-box">
        <div class="sustainability-header">
            🌱 Reducing Avoidable Grocery Waste at the Source
        </div>
        <div class="sustainability-content">
            <p style="margin-bottom:0.7rem;">
                In the grocery sector, fresh produce, dairy, meats, and prepared foods account for the largest proportion of shrink. 
                When perishables pass their sell-by date, traditional stores discard them into municipal landfills where anaerobic decomposition 
                generates significant methane emissions.
            </p>
            <p style="margin-bottom:0.7rem;">
                <strong>Proactive Intervention Over Reactive Disposal:</strong> By dynamically tracking biological decay windows 48 hours earlier, 
                supermarkets can deploy tiered dynamic discounts, rebalance stock to high-turnover sister locations, or arrange timely donations 
                to local food banks. This aligns directly with the <em>EPA Food Recovery Hierarchy</em>, prioritizing prevention and human consumption 
                before waste is ever generated.
            </p>
            <div style="display:flex; gap:16px; flex-wrap:wrap; font-size:0.86rem; color:#064E3B; font-weight:600; margin-top:0.8rem; border-top:1px solid #A7F3D0; padding-top:0.8rem;">
                <span>✓ Prevention First</span>
                <span>✓ Cold-Chain Preservation</span>
                <span>✓ Elasticity Pricing</span>
                <span>✓ Food Bank Redistribution</span>
                <span>✓ Landfill Methane Avoidance</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

