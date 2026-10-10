"""
Plotly Chart Visualizations for Zero-Waste Grocery
Engineered with premium sustainability-tech aesthetic (Forest, Emerald, Lime, Coral, Purple).
"""
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from typing import Dict, Any

# Shared Plotly theme styling
PLOTLY_FONT = dict(family="Plus Jakarta Sans, sans-serif", size=12, color="#334155")
PLOTLY_BG = "rgba(0,0,0,0)"

def plot_freshness_breakdown(inventory_df: pd.DataFrame) -> go.Figure:
    """
    Donut chart of inventory segmentation by remaining shelf life.
    """
    def categorize_dte(d):
        if d is None or pd.isna(d):
            return "Unspecified Expiry"
        elif d <= 1:
            return "Critical (≤ 24h)"
        elif d <= 2:
            return "Urgent (24-48h)"
        elif d <= 4:
            return "Moderate (3-4d)"
        else:
            return "Fresh (> 4d)"
            
    df_copy = inventory_df.copy()
    df_copy["Shelf Status"] = df_copy["days_to_expiry"].apply(categorize_dte)
    counts = df_copy.groupby("Shelf Status")["current_stock"].sum().reset_index()
    
    color_map = {
        "Critical (≤ 24h)": "#EA580C", # Coral alert
        "Urgent (24-48h)": "#F59E0B",  # Amber warn
        "Moderate (3-4d)": "#10B981",  # Emerald
        "Fresh (> 4d)": "#059669",      # Deep Green
        "Unspecified Expiry": "#94A3B8" # Slate neutral
    }
    
    fig = px.pie(
        counts,
        names="Shelf Status",
        values="current_stock",
        hole=0.62,
        color="Shelf Status",
        color_discrete_map=color_map
    )
    
    fig.update_traces(
        textposition='inside',
        textinfo='percent',
        hoverinfo='label+value+percent',
        marker=dict(line=dict(color='#FFFFFF', width=2))
    )
    
    fig.update_layout(
        font=PLOTLY_FONT,
        paper_bgcolor=PLOTLY_BG,
        plot_bgcolor=PLOTLY_BG,
        margin=dict(t=20, b=20, l=20, r=20),
        height=270,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.25,
            xanchor="center",
            x=0.5
        ),
        annotations=[dict(
            text="Shelf-Life<br>Health",
            x=0.5, y=0.5,
            font_size=13,
            font_family="Space Grotesk",
            font_color="#062E1E",
            showarrow=False
        )]
    )
    return fig

def plot_category_risk_bar(inventory_df: pd.DataFrame) -> go.Figure:
    """
    Stacked bar chart showing inventory units across categories broken down by days left.
    """
    df = inventory_df.copy()
    df["Urgency Group"] = df["days_to_expiry"].apply(
        lambda d: "Unspecified" if (d is None or pd.isna(d)) else ("Critical (≤1d)" if d <= 1 else ("At-Risk (2-3d)" if d <= 3 else "Safe (4d+)"))
    )
    
    grouped = df.groupby(["category", "Urgency Group"])["current_stock"].sum().reset_index()
    
    color_map = {
        "Critical (≤1d)": "#EA580C",
        "At-Risk (2-3d)": "#F59E0B",
        "Safe (4d+)": "#10B981",
        "Unspecified": "#94A3B8"
    }

    
    fig = px.bar(
        grouped,
        x="current_stock",
        y="category",
        color="Urgency Group",
        orientation="h",
        color_discrete_map=color_map,
        labels={"current_stock": "Active Inventory (Units)", "category": "Perishable Category"}
    )
    
    fig.update_layout(
        font=PLOTLY_FONT,
        paper_bgcolor=PLOTLY_BG,
        plot_bgcolor=PLOTLY_BG,
        margin=dict(t=20, b=20, l=10, r=20),
        height=300,
        barmode="stack",
        xaxis=dict(showgrid=True, gridcolor="#F1F5F9"),
        yaxis=dict(categoryorder="total ascending"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    return fig

def plot_forecast_trajectory(forecast_df: pd.DataFrame, current_stock: int, product_name: str) -> go.Figure:
    """
    Line chart with P10-P90 probabilistic uncertainty band and inventory threshold.
    """
    fig = go.Figure()
    
    # Upper confidence band (P90)
    fig.add_trace(go.Scatter(
        x=forecast_df["day_name"],
        y=forecast_df["forecast_p90"],
        mode='lines',
        line=dict(width=0),
        showlegend=False,
        name='P90 Upper'
    ))
    
    # Shaded band fill to P10
    fig.add_trace(go.Scatter(
        x=forecast_df["day_name"],
        y=forecast_df["forecast_p10"],
        mode='lines',
        line=dict(width=0),
        fill='tonexty',
        fillcolor='rgba(16, 185, 129, 0.18)',
        name='80% Confidence Band (P10-P90)'
    ))
    
    # Median Forecast line (P50)
    fig.add_trace(go.Scatter(
        x=forecast_df["day_name"],
        y=forecast_df["forecast_p50"],
        mode='lines+markers',
        line=dict(color='#059669', width=3),
        marker=dict(size=7, color='#047857'),
        name='Expected Sales (P50)'
    ))
    
    fig.update_layout(
        title=dict(
            text=f"7-Day Demand Horizon & Confidence: {product_name}",
            font=dict(family="Space Grotesk", size=14, color="#062E1E")
        ),
        font=PLOTLY_FONT,
        paper_bgcolor=PLOTLY_BG,
        plot_bgcolor=PLOTLY_BG,
        margin=dict(t=40, b=30, l=20, r=20),
        height=320,
        xaxis=dict(showgrid=True, gridcolor="#F1F5F9"),
        yaxis=dict(showgrid=True, gridcolor="#F1F5F9", title="Daily Velocity (Units)"),
        legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5)
    )
    return fig

def plot_biological_decay(nominal_days: int) -> go.Figure:
    """
    Renders non-linear shelf-life decay curve showing quality depletion over time.
    """
    days = np.linspace(0, nominal_days + 1, 40)
    # Weibull degradation curve
    scale = nominal_days * 0.95
    shape = 2.4
    quality = np.exp(-((days / scale) ** shape)) * 100.0
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=days,
        y=quality,
        mode='lines',
        line=dict(color='#EA580C', width=3),
        name='Bio-Quality Index'
    ))
    
    # Thresholds
    fig.add_hline(y=50, line_dash="dot", line_color="#F59E0B", annotation_text="Markdown Threshold (50%)")
    fig.add_hline(y=20, line_dash="dash", line_color="#EF4444", annotation_text="Spoilage Threshold (20%)")
    
    fig.update_layout(
        font=PLOTLY_FONT,
        paper_bgcolor=PLOTLY_BG,
        plot_bgcolor=PLOTLY_BG,
        margin=dict(t=30, b=20, l=20, r=20),
        height=260,
        xaxis=dict(title="Batch Age (Days on Shelf)", showgrid=True, gridcolor="#F1F5F9"),
        yaxis=dict(title="Perceived Freshness (%)", range=[0, 105], showgrid=True, gridcolor="#F1F5F9")
    )
    return fig

def plot_baseline_comparison(benchmarks_df: pd.DataFrame) -> go.Figure:
    """
    Grouped bar chart comparing Static Min/Max vs Naive Expiry vs Multi-Agent AI System.
    """
    fig = go.Figure()
    
    strategies = benchmarks_df["Strategy"].tolist()
    
    fig.add_trace(go.Bar(
        x=strategies,
        y=benchmarks_df["Waste Diverted (kg)"],
        name="Food Waste Diverted (kg)",
        marker_color="#10B981"
    ))
    
    fig.add_trace(go.Bar(
        x=strategies,
        y=benchmarks_df["Gross Margin Saved ($)"],
        name="Gross Margin Saved ($)",
        marker_color="#7C3AED"
    ))
    
    fig.add_trace(go.Bar(
        x=strategies,
        y=benchmarks_df["CO2e Averted (kg)"],
        name="Carbon Footprint Averted (kg CO2e)",
        marker_color="#84CC16"
    ))
    
    fig.update_layout(
        font=PLOTLY_FONT,
        paper_bgcolor=PLOTLY_BG,
        plot_bgcolor=PLOTLY_BG,
        barmode='group',
        margin=dict(t=30, b=30, l=20, r=20),
        height=350,
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=True, gridcolor="#F1F5F9", title="Impact Magnitude"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    return fig

def plot_action_distribution(actions_summary: Dict[str, int]) -> go.Figure:
    """
    Pie chart showing the distribution of reconciled agent decisions.
    """
    labels = list(actions_summary.keys())
    values = list(actions_summary.values())
    
    colors = {
        "MARKDOWN": "#F97316",
        "TRANSFER": "#8B5CF6",
        "REORDER": "#3B82F6",
        "DONATE": "#FBBF24",
        "MAINTAIN": "#10B981"
    }
    palette = [colors.get(l, "#94A3B8") for l in labels]
    
    fig = px.pie(
        names=labels,
        values=values,
        hole=0.55,
        color=labels,
        color_discrete_sequence=palette
    )
    
    fig.update_traces(
        textposition='inside',
        textinfo='label+percent',
        hoverinfo='label+value+percent',
        marker=dict(line=dict(color='#FFFFFF', width=2))
    )
    
    fig.update_layout(
        font=PLOTLY_FONT,
        paper_bgcolor=PLOTLY_BG,
        plot_bgcolor=PLOTLY_BG,
        margin=dict(t=10, b=10, l=10, r=10),
        height=260,
        showlegend=False,
        annotations=[dict(
            text="Agent<br>Proposals",
            x=0.5, y=0.5,
            font_size=12,
            font_family="Space Grotesk",
            font_color="#062E1E",
            showarrow=False
        )]
    )
    return fig
