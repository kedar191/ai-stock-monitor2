import streamlit as st
import pandas as pd
import plotly.express as px
import yfinance as yf
import requests
import openai

st.set_page_config(page_title="AI Stock Monitor & Shadow Portfolio", layout="wide", initial_sidebar_state="expanded")

@st.cache_data
def load_portfolio():
    return pd.read_csv("portfolio.csv")

@st.cache_data
def load_universe():
    return pd.read_csv("ai_universe.csv")

def fetch_price(ticker):
    try:
        data = yf.Ticker(ticker)
        price = data.history(period="1d")["Close"].values[-1]
        if price <= 0:
            raise ValueError("Invalid price fetched")
        return price
    except Exception:
        return None

def format_ticker(ticker):
    if ticker.endswith(".HK") or ticker.endswith(".SZ") or ticker.endswith(".SS"):
        return ticker
    if ticker.isalpha():
        return ticker
    return ticker

def fetch_ai_news():
    NEWS_API_KEY = st.secrets["NEWS_API_KEY"]
    NEWS_ENDPOINT = "https://newsapi.org/v2/everything"
    QUERY = "artificial intelligence OR AI OR machine learning OR generative AI"
    params = {
        "q": QUERY,
        "sortBy": "publishedAt",
        "language": "en",
        "pageSize": 5,
        "apiKey": NEWS_API_KEY,
    }
    response = requests.get(NEWS_ENDPOINT, params=params)
    data = response.json()
    return data.get("articles", [])

portfolio = load_portfolio()
ai_universe = load_universe()

st.title("🧠 AI Stock Monitor & Shadow Portfolio")
st.markdown("Track, analyze, and research the best AI investment opportunities (US + China).")

tab1, tab2, tab3 = st.tabs(["📊 Portfolio", "👀 AI Stock Monitor", "📝 Research & Insights"])

USDINR = 83.5  # Update this as needed

with tab1:
    st.header("Your Shadow AI Portfolio")
    kpi1, kpi2, kpi3 = st.columns(3)
    total_invested = portfolio['Investment (INR)'].sum()
    kpi1.metric("Total Invested (₹)", f"{total_invested:,.0f}")
    total_value = 0
    current_prices = []

    for i, row in portfolio.iterrows():
        ticker = format_ticker(row['Ticker'])
        price = fetch_price(ticker)

        if ticker == "PLTR":
            live_price_inr = 1670  # Adjust this to the correct INR price for Palantir if you want
        else:
            if price is None or price <= 0:
                live_price_inr = row['Buy Price (INR)']
            else:
                if ticker.endswith(".HK") or ticker.endswith(".SZ") or ticker.endswith(".SS"):
                    live_price_inr = price
                else:
                    live_price_inr = price * USDINR

        current_prices.append(live_price_inr)
        total_value += live_price_inr * row['Units']

    kpi2.metric("Current Value (est, ₹)", f"{int(total_value):,}")
    gain = total_value - total_invested
    gain_pct = (gain / total_invested * 100) if total_invested else 0
    kpi3.metric("Total Return", f"{gain:,.0f} ({gain_pct:+.2f}%)", delta_color="normal")

    portfolio['Current Price (INR)'] = current_prices
    portfolio['Current Value'] = (portfolio['Current Price (INR)'] * portfolio['Units']).round(2)
    portfolio['Gain/Loss (₹)'] = (portfolio['Current Value'] - portfolio['Investment (INR)']).round(2)
    portfolio['Gain/Loss (%)'] = ((portfolio['Gain/Loss (₹)'] / portfolio['Investment (INR)']) * 100).round(2)
    st.dataframe(portfolio, use_container_width=True)

    pie = px.pie(portfolio, names='Barbell Type', values='Investment (INR)', title="Allocation by Barbell Type")
    st.plotly_chart(pie, use_container_width=True)

    bar = px.bar(portfolio, x='Stock', y='Gain/Loss (₹)', color='Barbell Type', title="Gain/Loss by Stock", color_discrete_sequence=px.colors.qualitative.Dark24)
    st.plotly_chart(bar, use_container_width=True)

with tab2:
    st.header("AI Stock Universe: Watch & Screen")
    search = st.text_input("🔎 Search stocks (name or ticker)")
    filtered = ai_universe
    if search:
        search = search.lower()
        filtered = ai_universe[ai_universe.apply(lambda row: search in str(row['Stock']).lower() or search in str(row['Ticker']).lower(), axis=1)]

    def undervalued(row):
        try:
            return float(row['P/E']) < 20
        except:
            return False
    filtered['Undervalued'] = filtered.apply(undervalued, axis=1)
    filtered['High Momentum'] = filtered['YTD %'] > 30
    st.dataframe(filtered, use_container_width=True)

    pie2 = px.pie(filtered, names='Region', title="Universe by Region")
    st.plotly_chart(pie2, use_container_width=True)

with tab3:
    st.header("Research & Insights")

    articles = fetch_ai_news()
    st.subheader("Latest AI News")
    for article in articles:
        st.markdown(f"### [{article['title']}]({article['url']})")
        st.write(article.get("description", "No description available."))

        if st.button(f"Summarize: {article['title']}", key=article['url']):
            openai.api_key = st.secrets["OPENAI_API_KEY"]
            prompt = f"Summarize this news article:\n\nTitle: {article['title']}\nDescription: {article.get('description','')}"
            with st.spinner("Generating summary..."):
                try:
                    response = openai.ChatCompletion.create(
                        model="gpt-4o-mini",
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0.7,
                        max_tokens=200,
                    )
                    summary = response.choices[0].message.content
                    st.write(summary)
                except Exception as e:
                    st.error(f"OpenAI API error: {e}")

    st.markdown("---")
    st.subheader("Your Research Notes")
    note = st.text_area("Write notes or paste research here")

    if st.button("Save Note"):
        st.session_state['research_note'] = note
        st.success("Note saved (session only)")

st.markdown("---")
st.caption("Built by Kedar + ChatGPT | v1.0")
