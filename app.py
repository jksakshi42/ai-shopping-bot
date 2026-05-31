import requests

url = "https://duckduckgo.com/html/"
# This makes your app pretend to be a real Windows computer using Chrome:
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}
# Run the search with the headers attached
response = requests.get(url, headers=headers)
print(response.text)
import streamlit as st
import google.generativeai as genai
from duckduckgo_search import DDGS
import json
import pandas as pd

# 1. Setup Gemini API using Streamlit Secrets
GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
genai.configure(api_key=GEMINI_API_KEY)

REGION_MAP = {
    "🇮🇳 India (Myntra, Ajio, Nykaa Fashion, Tata CLiQ)": "Myntra, Ajio, Nykaa Fashion, Tata CLiQ, Lifestyle",
    "🇺🇸 US / Global (ASOS, H&M, Zara, Nordstrom)": "ASOS, H&M, Zara, Nordstrom, Macy's",
    "🇪🇺 Europe (Zalando, Yoox, ASOS Europe)": "Zalando, Yoox, ASOS Europe, About You"
}

from duckduckgo_search import DDGS

def search_regional_fashion(query):
    try:
        clean_query = f"{query} buy online"

        with DDGS() as ddgs:
            results = list(
                ddgs.text(
                    clean_query,
                    region="in-en",
                    safesearch="off",
                    max_results=10
                )
            )

        return results

    except Exception as e:
        st.error(f"Search Error: {e}")
        return []

def get_product_image_url(product_name):
    """Jugaad Function: Fetches a live image URL from the web based on product name."""
    try:
        with DDGS() as ddgs:
            img_results = list(ddgs.images(product_name, max_results=1))
            if img_results:
                return img_results[0]['image']
    except:
        pass
    # Placeholder image if search fails
    return "https://images.unsplash.com/photo-1483985988355-763728e1935b?w=200&q=80"

def parse_fashion_prices(search_results, item_keywords, allowed_stores):
    """Gemini filters regional stores and structures the data."""
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    prompt = f"""
    You are an expert Fashion E-commerce Data Parser. Analyze the search results for '{item_keywords}'.
    
    CRITICAL FILTER: You must prioritize and only extract results that match or are highly relevant to these targeted stores: [{allowed_stores}].

    Extract the product name, the store name, the lowest final price, the currency symbol, and the exact source URL.
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

# 2. Streamlit UI Interface
st.set_page_config(page_title="AI Regional Fashion Finder", layout="wide")
st.title("👝 Regional AI Fashion Price Comparison Bot")
st.caption("Now with Live Product Preview Images 📸")

# Sidebar setup
st.sidebar.header("Configuration")
selected_region = st.sidebar.selectbox("Choose Target Fashion Market:", list(REGION_MAP.keys()))
allowed_stores = REGION_MAP[selected_region]

user_query = st.text_input("What fashion accessory or item are you looking for?", placeholder="e.g., Black quilted sling purse")

if st.button("Find Lowest Regional Prices"):
    if not user_query:
        st.warning("Please enter a specific item to cross-reference!")
    else:
        with st.spinner("Scouring registries and downloading product visuals..."):
            
            # Step 1: Text Search
            raw_data = search_regional_fashion(user_query)
            
            if not raw_data:
                st.error("DuckDuckGo blocked the cloud request. Try searching again in a few seconds.")
            else:
                # Step 2: AI Parsing
                structured_data = parse_fashion_prices(raw_data, user_query, allowed_stores)
                
                if not structured_data:
                    st.error("AI couldn't find matches for the selected stores. Try broadening your keywords!")
                else:
                    # Step 3: Convert to DataFrame and Sort
                    df = pd.DataFrame(structured_data)
                    df['price'] = pd.to_numeric(df['price'], errors='coerce')
                    df = df.dropna(subset=['price']).sort_values(by='price', ascending=True)
                    
                    # Limiting to top 5 results to keep image fetching fast and prevent lag
                    df = df.head(5)
                    
                    if df.empty:
                        st.error("No valid prices found. Try a different query.")
                    else:
                        st.success("Targeted price-mapping complete!")
                        
                        # Step 4: Fetch Images for the products
                        with st.spinner("Fetching matching product images..."):
                            df['image_url'] = df['product'].apply(get_product_image_url)
                        
                        cheapest = df.iloc[0]
                        currency = cheapest.get('currency', '$')
                        
                        # Displaying the Big Winner with Image
                        col1, col2 = st.columns([1, 2])
                        with col1:
                            st.image(cheapest['image_url'], caption=cheapest['product'], use_container_width=True)
                        with col2:
                            st.subheader(f"🏆 Absolute Lowest Price found at {cheapest['store']}")
                            st.metric(label="Deal Price", value=f"{currency}{cheapest['price']:.2f}")
                            st.write(f"**Item:** {cheapest['product']}")
                            st.markdown(f'<a href="{cheapest["link"]}" target="_blank"><button style="background-color:#FF4B4B; color:white; border:none; padding:10px 20px; border-radius:5px; cursor:pointer;">Grab This Deal 🚀</button></a>', unsafe_allow_html=True)
                        
                        st.write("---")
                        st.subheader("📋 All Matching Offers Found")
                        
                        # Formatting the Table with clickable links and HTML Images
                        df['Preview'] = df['image_url'].apply(lambda x: f'<img src="{x}" width="80" style="border-radius:5px;">')
                        df['Link'] = df['link'].apply(lambda x: f'<a href="{x}" target="_blank">Go To Store 🛒</a>')
                        
                        # Clean up the columns for final display
                        final_df = df[['Preview', 'product', 'store', 'price', 'currency', 'Link']]
                        final_df.columns = ['Preview', 'Product Name', 'Store', 'Price', 'Currency', 'Action']
                        
                        # Render the HTML table in Streamlit
                        st.write(final_df.to_html(escape=False, index=False), unsafe_allow_html=True)
