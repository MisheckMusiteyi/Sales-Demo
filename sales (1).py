# -*- coding: utf-8 -*-
"""Investment Portfolio Dashboard - Real Estate & Mining"""

import streamlit as st
import pandas as pd
import json
import numpy as np
from google.oauth2 import service_account
from googleapiclient.discovery import build
from datetime import datetime

# ---------- Page Configuration ----------
st.set_page_config(
    page_title="Investment Portfolio Dashboard",
    layout="wide",
    page_icon="📊"
)

# ---------- Custom CSS for Dark Theme with Red Accents ----------
st.markdown("""
<style>
    /* Main background */
    .stApp {
        background-color: #0e1117;
    }
    
    /* KPI Card styling */
    .kpi-card {
        background-color: #1e1e1e;
        border-radius: 10px;
        padding: 20px;
        border-left: 5px solid #ff4b4b;
        box-shadow: 0 2px 4px rgba(0,0,0,0.3);
        margin-bottom: 15px;
    }
    
    .kpi-card-red {
        background-color: #2a1a1a;
        border-radius: 10px;
        padding: 20px;
        border-left: 5px solid #ff0000;
        box-shadow: 0 2px 4px rgba(0,0,0,0.3);
        margin-bottom: 15px;
    }
    
    .kpi-label {
        color: #888888;
        font-size: 14px;
        font-weight: 500;
        margin-bottom: 8px;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    .kpi-value {
        color: #ffffff;
        font-size: 32px;
        font-weight: 700;
        margin-bottom: 5px;
    }
    
    .kpi-value-red {
        color: #ff4b4b;
        font-size: 32px;
        font-weight: 700;
        margin-bottom: 5px;
    }
    
    .kpi-sub {
        color: #666666;
        font-size: 12px;
    }
    
    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: #1e1e1e;
        padding: 10px;
        border-radius: 10px;
    }
    
    .stTabs [data-baseweb="tab"] {
        background-color: #2d2d2d;
        border-radius: 8px;
        padding: 8px 20px;
        color: #ffffff;
    }
    
    .stTabs [aria-selected="true"] {
        background-color: #ff4b4b;
        color: #ffffff;
    }
    
    /* Dataframe styling */
    .stDataFrame {
        background-color: #1e1e1e;
        border-radius: 10px;
        padding: 10px;
    }
    
    /* Headers */
    h1, h2, h3 {
        color: #ffffff !important;
    }
    
    /* Metric styling */
    div[data-testid="stMetricValue"] {
        color: #ffffff !important;
    }
    
    hr {
        border-color: #ff4b4b;
    }
</style>
""", unsafe_allow_html=True)

# ---------- Configuration ----------
SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']
SPREADSHEET_ID = '1TTlOg7SbjIv1yWJksGxWODDNHrrV7S1NSFfHzxfmYlE'  # Your spreadsheet ID

# Define all sheet names and their ranges
SHEETS_CONFIG = {
    'RealEstate_Rental_Income': 'RealEstate_Rental_Income!A:C',
    'RealEstate_Rental_Expenses': 'RealEstate_Rental_Expenses!A:D',
    'RealEstate_Sales': 'RealEstate_Sales!A:I',
    'Mining_Capital_Invested': 'Mining_Capital_Invested!A:B',
    'Mining_Expenses': 'Mining_Expenses!A:C',
    'Mining_Equipment_Purchase': 'Mining_Equipment_Purchase!A:C',
    'Mining_Revenue': 'Mining_Revenue!A:C'
}

def get_sheet_data(sheet_range):
    """Fetch data from a specific Google Sheets range."""
    try:
        creds_dict = json.loads(st.secrets["google_credentials"])
        creds = service_account.Credentials.from_service_account_info(
            creds_dict, scopes=SCOPES
        )
        service = build('sheets', 'v4', credentials=creds)
        sheet = service.spreadsheets()
        result = sheet.values().get(
            spreadsheetId=SPREADSHEET_ID,
            range=sheet_range
        ).execute()
        values = result.get('values', [])
        if not values or len(values) <= 1:
            return pd.DataFrame()
        header = values[0]
        data = values[1:]
        df = pd.DataFrame(data, columns=header)
        return df
    except Exception as e:
        st.error(f"Error loading {sheet_range}: {str(e)}")
        return pd.DataFrame()

@st.cache_data(ttl=600)
def load_all_data():
    """Load all sheets data."""
    data = {}
    for sheet_name, sheet_range in SHEETS_CONFIG.items():
        data[sheet_name] = get_sheet_data(sheet_range)
    return data

# ---------- Helper Functions for KPIs ----------
def display_kpi_card(label, value, is_red=False, sub_text=""):
    """Display a KPI card with custom styling."""
    card_class = "kpi-card-red" if is_red else "kpi-card"
    value_class = "kpi-value-red" if is_red else "kpi-value"
    
    st.markdown(f"""
    <div class="{card_class}">
        <div class="kpi-label">{label}</div>
        <div class="{value_class}">{value}</div>
        <div class="kpi-sub">{sub_text}</div>
    </div>
    """, unsafe_allow_html=True)

def find_column(df, possible_names):
    """Find a column in dataframe by trying multiple possible names."""
    if df.empty:
        return None
    
    # Clean column names: strip whitespace and convert to lowercase for matching
    df.columns = [str(col).strip() for col in df.columns]
    
    for name in possible_names:
        # Try exact match first
        if name in df.columns:
            return name
        # Try case-insensitive match
        for col in df.columns:
            if col.lower() == name.lower():
                return col
    return None

def safe_numeric_convert(series):
    """Safely convert a series to numeric, handling empty strings and errors."""
    if series is None or len(series) == 0:
        return pd.Series([0])
    
    # Convert to string first, then clean
    cleaned = series.astype(str).str.strip()
    # Replace empty strings and 'nan' with 0
    cleaned = cleaned.replace(['', 'nan', 'NaN', 'None'], '0')
    # Remove commas and dollar signs
    cleaned = cleaned.str.replace(',', '', regex=False)
    cleaned = cleaned.str.replace('$', '', regex=False)
    # Convert to numeric, coercing errors to NaN
    numeric = pd.to_numeric(cleaned, errors='coerce')
    # Fill NaN with 0
    numeric = numeric.fillna(0)
    return numeric

def format_currency(value):
    """Format number as currency."""
    try:
        val = float(value)
        return f"${val:,.0f}"
    except:
        return "$0"

def format_percentage(value):
    """Format as percentage."""
    try:
        val = float(value)
        return f"{val:,.1f}%"
    except:
        return "0%"

# ---------- Real Estate Analysis ----------
def analyze_real_estate(data):
    """Calculate Real Estate KPIs."""
    rental_income = data.get('RealEstate_Rental_Income', pd.DataFrame())
    rental_expenses = data.get('RealEstate_Rental_Expenses', pd.DataFrame())
    sales = data.get('RealEstate_Sales', pd.DataFrame())
    
    # Convert to numeric safely
    total_rental_income = 0
    total_rental_expenses = 0
    total_sales_profit = 0
    total_sales_revenue = 0
    units_sold = 0
    
    # Find Rental Income column
    if not rental_income.empty:
        income_col = find_column(rental_income, ['Total Rental Income', 'Rental Income', 'Income', 'Amount'])
        if income_col:
            total_rental_income = safe_numeric_convert(rental_income[income_col]).sum()
    
    # Find Rental Expenses column
    if not rental_expenses.empty:
        expense_col = find_column(rental_expenses, ['Expense Amount', 'Amount', 'Expense', 'Cost'])
        if expense_col:
            total_rental_expenses = safe_numeric_convert(rental_expenses[expense_col]).sum()
    
    net_rental_income = total_rental_income - total_rental_expenses
    
    # Find Sales columns
    if not sales.empty:
        profit_col = find_column(sales, ['Gross Profit', 'Profit', 'Total Profit'])
        if profit_col:
            total_sales_profit = safe_numeric_convert(sales[profit_col]).sum()
        
        revenue_col = find_column(sales, ['Total Sales Revenue', 'Sales Revenue', 'Revenue', 'Total Sales'])
        if revenue_col:
            total_sales_revenue = safe_numeric_convert(sales[revenue_col]).sum()
        
        units_col = find_column(sales, ['Units Sold', 'Units', 'Quantity', 'Qty'])
        if units_col:
            units_sold = safe_numeric_convert(sales[units_col]).sum()
    
    total_real_estate_profit = net_rental_income + total_sales_profit
    
    return {
        'total_rental_income': total_rental_income,
        'total_rental_expenses': total_rental_expenses,
        'net_rental_income': net_rental_income,
        'total_sales_revenue': total_sales_revenue,
        'total_sales_profit': total_sales_profit,
        'units_sold': units_sold,
        'total_real_estate_profit': total_real_estate_profit
    }

# ---------- Mining Analysis ----------
def analyze_mining(data):
    """Calculate Mining KPIs."""
    capital = data.get('Mining_Capital_Invested', pd.DataFrame())
    expenses = data.get('Mining_Expenses', pd.DataFrame())
    equipment = data.get('Mining_Equipment_Purchase', pd.DataFrame())
    revenue = data.get('Mining_Revenue', pd.DataFrame())
    
    # Convert to numeric safely
    total_capital = 0
    total_expenses = 0
    total_equipment = 0
    total_revenue = 0
    
    # Find Amount column in each sheet
    if not capital.empty:
        amount_col = find_column(capital, ['Amount', 'Capital', 'Investment', 'Amount Invested'])
        if amount_col:
            total_capital = safe_numeric_convert(capital[amount_col]).sum()
    
    if not expenses.empty:
        amount_col = find_column(expenses, ['Amount', 'Expense Amount', 'Cost'])
        if amount_col:
            total_expenses = safe_numeric_convert(expenses[amount_col]).sum()
    
    if not equipment.empty:
        amount_col = find_column(equipment, ['Amount', 'Purchase Amount', 'Cost'])
        if amount_col:
            total_equipment = safe_numeric_convert(equipment[amount_col]).sum()
    
    if not revenue.empty:
        amount_col = find_column(revenue, ['Amount', 'Revenue', 'Income'])
        if amount_col:
            total_revenue = safe_numeric_convert(revenue[amount_col]).sum()
    
    total_costs = total_expenses + total_equipment
    net_profit = total_revenue - total_costs
    roi = (net_profit / total_capital * 100) if total_capital > 0 else 0
    
    return {
        'total_capital': total_capital,
        'total_expenses': total_expenses,
        'total_equipment': total_equipment,
        'total_revenue': total_revenue,
        'total_costs': total_costs,
        'net_profit': net_profit,
        'roi': roi
    }

# ---------- Overall Analysis ----------
def analyze_overall(real_estate_kpis, mining_kpis):
    """Calculate overall portfolio KPIs."""
    total_revenue = real_estate_kpis['total_rental_income'] + real_estate_kpis['total_sales_revenue'] + mining_kpis['total_revenue']
    total_profit = real_estate_kpis['total_real_estate_profit'] + mining_kpis['net_profit']
    total_capital = mining_kpis['total_capital']  # Real estate capital not tracked yet
    
    overall_roi = (total_profit / total_capital * 100) if total_capital > 0 else 0
    
    return {
        'total_revenue': total_revenue,
        'total_profit': total_profit,
        'total_capital': total_capital,
        'overall_roi': overall_roi
    }

# ---------- Main Dashboard UI ----------
st.title("🏢 Investment Portfolio Dashboard")
st.markdown("---")

# Load all data
with st.spinner("Loading portfolio data..."):
    data = load_all_data()

# Manual refresh button
col1, col2, col3 = st.columns([1, 1, 4])
with col1:
    if st.button('🔄 Refresh Data'):
        st.cache_data.clear()
        st.rerun()

# Calculate KPIs
real_estate_kpis = analyze_real_estate(data)
mining_kpis = analyze_mining(data)
overall_kpis = analyze_overall(real_estate_kpis, mining_kpis)

# Create Tabs
tab1, tab2, tab3 = st.tabs(["🏠 Real Estate", "⛏️ Mining", "📈 Overall Portfolio"])

# ---------- TAB 1: REAL ESTATE ----------
with tab1:
    st.markdown("### Real Estate Portfolio Performance")
    st.markdown("---")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        display_kpi_card("Rental Income", format_currency(real_estate_kpis['total_rental_income']))
    with col2:
        display_kpi_card("Rental Expenses", format_currency(real_estate_kpis['total_rental_expenses']), is_red=True)
    with col3:
        display_kpi_card("Net Rental Income", format_currency(real_estate_kpis['net_rental_income']))
    with col4:
        display_kpi_card("Sales Profit", format_currency(real_estate_kpis['total_sales_profit']))
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        display_kpi_card("Units Sold", f"{real_estate_kpis['units_sold']:,.0f}")
    with col2:
        display_kpi_card("Sales Revenue", format_currency(real_estate_kpis['total_sales_revenue']))
    with col3:
        display_kpi_card("Total Real Estate Profit", format_currency(real_estate_kpis['total_real_estate_profit']), is_red=True)
    with col4:
        pass
    
    # Show data tables
    with st.expander("📋 View Detailed Data"):
        if not data.get('RealEstate_Rental_Income', pd.DataFrame()).empty:
            st.subheader("Rental Income")
            st.dataframe(data['RealEstate_Rental_Income'])
        
        if not data.get('RealEstate_Rental_Expenses', pd.DataFrame()).empty:
            st.subheader("Rental Expenses")
            st.dataframe(data['RealEstate_Rental_Expenses'])
        
        if not data.get('RealEstate_Sales', pd.DataFrame()).empty:
            st.subheader("Property Sales")
            st.dataframe(data['RealEstate_Sales'])

# ---------- TAB 2: MINING ----------
with tab2:
    st.markdown("### Mining Portfolio Performance")
    st.markdown("---")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        display_kpi_card("Capital Invested", format_currency(mining_kpis['total_capital']), is_red=True)
    with col2:
        display_kpi_card("Total Revenue", format_currency(mining_kpis['total_revenue']))
    with col3:
        display_kpi_card("Total Costs", format_currency(mining_kpis['total_costs']), is_red=True)
    with col4:
        display_kpi_card("Net Profit", format_currency(mining_kpis['net_profit']))
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        display_kpi_card("ROI", format_percentage(mining_kpis['roi']))
    with col2:
        display_kpi_card("Operating Expenses", format_currency(mining_kpis['total_expenses']))
    with col3:
        display_kpi_card("Equipment Purchases", format_currency(mining_kpis['total_equipment']))
    with col4:
        pass
    
    # Show data tables
    with st.expander("📋 View Detailed Data"):
        if not data.get('Mining_Capital_Invested', pd.DataFrame()).empty:
            st.subheader("Capital Invested")
            st.dataframe(data['Mining_Capital_Invested'])
        
        if not data.get('Mining_Expenses', pd.DataFrame()).empty:
            st.subheader("Operating Expenses")
            st.dataframe(data['Mining_Expenses'])
        
        if not data.get('Mining_Equipment_Purchase', pd.DataFrame()).empty:
            st.subheader("Equipment Purchases")
            st.dataframe(data['Mining_Equipment_Purchase'])
        
        if not data.get('Mining_Revenue', pd.DataFrame()).empty:
            st.subheader("Revenue")
            st.dataframe(data['Mining_Revenue'])

# ---------- TAB 3: OVERALL PORTFOLIO ----------
with tab3:
    st.markdown("### Overall Portfolio Performance")
    st.markdown("---")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        display_kpi_card("Total Revenue (All Portfolios)", format_currency(overall_kpis['total_revenue']))
    with col2:
        display_kpi_card("Total Profit", format_currency(overall_kpis['total_profit']), is_red=True)
    with col3:
        display_kpi_card("Overall ROI", format_percentage(overall_kpis['overall_roi']))
    
    st.markdown("---")
    st.markdown("### Portfolio Breakdown")
    
    # Simple breakdown using columns
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Real Estate")
        st.markdown(f"""
        - Rental Income: {format_currency(real_estate_kpis['total_rental_income'])}
        - Sales Profit: {format_currency(real_estate_kpis['total_sales_profit'])}
        - **Total: {format_currency(real_estate_kpis['total_real_estate_profit'])}**
        """)
    
    with col2:
        st.markdown("#### Mining")
        st.markdown(f"""
        - Revenue: {format_currency(mining_kpis['total_revenue'])}
        - Costs: {format_currency(mining_kpis['total_costs'])}
        - **Net Profit: {format_currency(mining_kpis['net_profit'])}**
        - ROI: {format_percentage(mining_kpis['roi'])}
        """)
    
    st.markdown("---")
    
    # Simple performance summary
    st.info(f"""
    **Portfolio Summary:**
    - Total capital deployed across all portfolios: {format_currency(overall_kpis['total_capital'])}
    - Total return (profit): {format_currency(overall_kpis['total_profit'])}
    - Overall ROI: {format_percentage(overall_kpis['overall_roi'])}
    """)
