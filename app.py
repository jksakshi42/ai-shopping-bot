import streamlit as st
import google.generativeai as genai
from duckduckgo_search import DDGS
import json
import pandas as pd

# 1. Setup Gemini API (Free Tier)
# Ab hum key ko code me nahi, Streamlit ke secret locker me rakhenge
import streamlit as st
GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
genai.configure(api_key=GEMINI_API_KEY)

# Define regional fashion footprints to inject into search
REGION_MAP = {
    "🇮🇳 India (Myntra, Ajio, Nykaa Fashion, Tata CLiQ)": "site:myntra.com OR site:ajio.com OR site:nykaafashion.com OR site:tatacliq.com",
    "🇺🇸 US / Global (ASOS, H&M, Zara, Nordstrom)": "site:asos.com OR site:hm.com OR site:zara.com OR site:nordstrom.com",
    "🇪🇺 Europe (Zalando, Yoox, ASOS Europe)": "site:zalando.com OR site:yoox.com OR site:asos.com/es"
}

def search_regional_fashion(query, site_filter):
    """Searches DuckDuckGo targeting specific regional fashion domains."""
    # Forcing terms like 'sale', 'price', or 'buy' improves snippet data quality
    full_query = f"{query} ({site_filter}) price sale buy"
    
    with DDGS() as ddgs:
        results = [r for r in ddgs.text(full_query, max_results=12)]
    return results

def parse_fashion_prices(search_results, item_keywords):
    """Uses Gemini 1.5 Flash to compute and extract final prices from raw text."""
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    prompt = f"""
    You are an expert Fashion E-commerce Data Parser. Analyze the search results for '{item_keywords}'.
    Extract the product name, the store name, the lowest final price, the currency symbol, and the exact source URL.
    
    Fashion sites often list 'MRP' and 'Offer Price'. Always isolate and extract the LOWEST checkout price mentioned.
    If a price is listed as a range (e.g., $20-$40), extract the lower boundary.

    Respond strictly in a valid JSON list of objects matching this exact format:
    [
      {{"product": "Product Name", "store": "Store Name", "price": 1299, "currency": "₹", "link": "URL"}}
    ]

    Raw Search Data:
    {json.dumps(search_results)}
    """
    
    response = model.generate_content(
        prompt,
        generation_config={"response_mime_type": "application/json"}
    )
    
    try:
        return json.loads(response.text)
    except:
        return []

# 2. Streamlit Fashion Interface
st.set_page_config(page_title="AI Regional Fashion Finder", layout="wide")
st.title("👝 Regional AI Fashion Price Comparison Bot")
st.caption("Zero Paid APIs — Powered by Gemini 1.5 Flash & Specialized Search Dorks")

# Sidebar setup for region configurations
st.sidebar.header("Configuration")
selected_region = st.sidebar.selectbox("Choose Target Fashion Market:", list(REGION_MAP.keys()))
target_filter = REGION_MAP[selected_region]

user_query = st.text_input("What fashion accessory or item are you looking for?", placeholder="e.g., Black quilted sling purse")

if st.button("Find Lowest Regional Prices"):
    if not user_query:
        st.warning("Please enter a specific item to cross-reference!")
    elif GEMINI_API_KEY == "YOUR_FREE_GEMINI_API_KEY":
        st.error("Please insert your free Gemini API key to run queries.")
    else:
        with st.spinner("Scouring regional fashion registries for the best price tags..."):
            
            # Step 1: Execute Targeted Search
            raw_data = search_regional_fashion(user_query, target_filter)
            
            if not raw_data:
                st.error("Could not fetch search metadata. Try widening your keywords.")
            else:
                # Step 2: Use AI to handle unstructured text fragments
                structured_data = parse_fashion_prices(raw_data, user_query)
                
                if not structured_data:
                    st.error("AI couldn't extract distinct price nodes from these sites. Try another item.")
                else:
                    # Step 3: Process and Sort Data
                    df = pd.DataFrame(structured_data)
                    df['price'] = pd.to_numeric(df['price'], errors='coerce')
                    df = df.dropna(subset=['price']).sort_values(by='price', ascending=True)
                    
                    # Step 4: Presentation Engine
                    st.success("Targeted price-mapping complete!")
                    
                    cheapest = df.iloc[0]
                    currency = cheapest.get('currency', '$')
                    st.metric(
                        label=f"🏆 Absolute Lowest Price found at {cheapest['store']}", 
                        value=f"{currency}{cheapest['price']:.2f}",
                        help=cheapest['product']
                    )
                    
                    # Generate clickable hyperlink UI elements inside dataframe
                    df['link'] = df['link'].apply(lambda x: f'<a href="{x}" target="_blank">Go To Store</a>')
                    
                    # Rearrange for user readability
                    df = df[['product', 'store', 'price', 'currency', 'link']]
                    st.write(df.to_html(escape=False, index=False), unsafe_allow_html=True)