import os
import sys
import time
import requests
import streamlit as st

# Page Config
st.set_page_config(
    page_title="Enterprise RAG Control Center",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling (Slate/Neo-Dark Theme, Glassmorphism, Micro-animations)
st.markdown("""
<style>
    /* Main Background & Fonts */
    .stApp {
        background-color: #0d1117;
        color: #c9d1d9;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
    }
    
    /* Header styling */
    .main-title {
        font-size: 2.8rem;
        font-weight: 800;
        background: linear-gradient(135deg, #58a6ff 0%, #bc8cff 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }
    
    .subtitle {
        font-size: 1.1rem;
        color: #8b949e;
        margin-bottom: 2rem;
    }
    
    /* Glassmorphism Metric Cards */
    .metric-card {
        background: rgba(22, 27, 34, 0.7);
        border: 1px solid rgba(48, 54, 61, 0.8);
        border-radius: 12px;
        padding: 15px;
        text-align: center;
        backdrop-filter: blur(10px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        border-color: #58a6ff;
    }
    .metric-title {
        font-size: 0.8rem;
        text-transform: uppercase;
        color: #8b949e;
        margin-bottom: 5px;
        font-weight: 600;
    }
    .metric-value {
        font-size: 1.6rem;
        font-weight: 700;
        color: #58a6ff;
    }
    .metric-value-total {
        color: #bc8cff;
    }
    
    /* Diagnostic Container Styling */
    .chunk-container {
        background: #161b22;
        border: 1px solid #30363d;
        border-radius: 8px;
        padding: 12px;
        margin-bottom: 10px;
    }
    .chunk-header {
        display: flex;
        justify-content: space-between;
        font-size: 0.85rem;
        color: #8b949e;
        border-bottom: 1px dashed #30363d;
        padding-bottom: 6px;
        margin-bottom: 8px;
    }
    .score-badge {
        background-color: #1f6feb;
        color: #ffffff;
        padding: 2px 8px;
        border-radius: 20px;
        font-weight: bold;
    }
    .rerank-badge {
        background-color: #8957e5;
        color: #ffffff;
        padding: 2px 8px;
        border-radius: 20px;
        font-weight: bold;
    }
    
    /* Custom chatbot dialog bubble */
    .chat-bubble {
        padding: 15px;
        border-radius: 10px;
        margin-bottom: 15px;
        line-height: 1.5;
    }
    .chat-assistant {
        background-color: #161b22;
        border: 1px solid #30363d;
    }
</style>
""", unsafe_allow_html=True)

# Application Heading
st.markdown('<div class="main-title">Scale-Ready RAG Control Center</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Decoupled REST API Controller • Distributed PySpark Ingestion • Two-Stage RRF Hybrid Vector Search</div>', unsafe_allow_html=True)

# Initialize Session States
if "backend_connected" not in st.session_state:
    st.session_state.backend_connected = False

# Sidebar Controls
with st.sidebar:
    st.image("https://qdrant.tech/images/qdrant_logo.png", width=120)
    st.markdown("### REST Backend Configuration")
    
    api_url = st.text_input("FastAPI Base Endpoint", value="http://localhost:8000/api/v1")
    
    # Connection Check
    if st.button("🔌 Check REST Backend Connection"):
        with st.spinner("Connecting to REST API backend..."):
            try:
                response = requests.get(f"{api_url}/health", timeout=5)
                if response.status_code == 200 and response.json().get("status") == "healthy":
                    st.session_state.backend_connected = True
                    st.success("Successfully connected to RAG Microservice API!")
                else:
                    st.session_state.backend_connected = False
                    st.error("API returned unhealthy status.")
            except Exception as e:
                st.session_state.backend_connected = False
                st.error(f"Cannot connect to API: {e}")
                
    st.markdown("---")
    st.markdown("### Retrieval Parameters")
    top_k_hybrid = st.slider("Stage 1 (Hybrid Matches)", 10, 100, 30)
    top_k_rerank = st.slider("Stage 2 (Reranked Contexts)", 2, 10, 5)
    
    st.markdown("---")
    st.markdown("### Ingestion Dashboard")
    st.info("Triggers the remote Spark ingestion job to clean, chunk, and index files.")
    
    if st.button("🚀 Trigger Ingestion Job"):
        if not st.session_state.backend_connected:
            st.warning("Please connect to the REST API backend first.")
        else:
            with st.spinner("Triggering distributed Spark job..."):
                try:
                    res = requests.post(f"{api_url}/ingest", timeout=120)
                    if res.status_code == 200:
                        total_chunks = res.json().get("total_chunks")
                        st.success(f"Ingestion succeeded! Indexed {total_chunks} chunks.")
                    else:
                        st.error(f"Ingest job failed: {res.json().get('detail')}")
                except Exception as e:
                    st.error(f"Network error triggering job: {e}")

# Main Screen Layout
col_query, col_metrics = st.columns([2, 1])

with col_query:
    st.subheader("Query Sandbox")
    
    if not st.session_state.backend_connected:
        st.warning("⚠️ Please configure and connect to the REST API backend using the sidebar before querying.")
        query_input = st.text_input("Enter query", disabled=True)
    else:
        query_input = st.text_input("Ask a question to the retrieved knowledge base:", 
                                    placeholder="e.g. Find clinical log with prescription details, or policy standard")
        
        if query_input:
            # Execute REST query
            with st.spinner("Retrieving response from API..."):
                try:
                    payload = {
                        "query": query_input,
                        "top_k_hybrid": top_k_hybrid,
                        "top_k_rerank": top_k_rerank
                    }
                    response = requests.post(f"{api_url}/query", json=payload, timeout=30)
                    if response.status_code == 200:
                        search_results = response.json()
                        st.session_state.search_results = search_results
                        
                        # Print Synthesized Answer
                        st.markdown("### Answer")
                        st.markdown(f'<div class="chat-bubble chat-assistant">{search_results["answer"]}</div>', unsafe_allow_html=True)
                        
                        # --- DIAGNOSTICS ---
                        st.markdown("### 🛠️ Diagnostics & Pipeline Walkthrough")
                        
                        # 1. Stage 2 Reranked output
                        with st.expander("Stage 2: Reranked Context Chunks (Top Match Results)", expanded=True):
                            for idx, item in enumerate(search_results["results"][:top_k_rerank]):
                                st.markdown(f"""
                                <div class="chunk-container">
                                    <div class="chunk-header">
                                        <span><b>Rank {idx+1}</b> | Doc: <span style="font-family: monospace;">{item['doc_id'][:12]}...</span> | Chunk {item['chunk_index']}</span>
                                        <span class="rerank-badge">Rerank Score: {item['rerank_score']:.4f}</span>
                                    </div>
                                    <p style="margin: 0; font-size: 0.95rem; line-height: 1.4; color: #e6edf3;">{item['chunk_text']}</p>
                                </div>
                                """, unsafe_allow_html=True)
                                
                    else:
                        st.error(f"Search failed: {response.json().get('detail')}")
                except Exception as e:
                    st.error(f"Connection failure during query: {e}")

# Latency metrics panel
with col_metrics:
    st.subheader("Performance Latency")
    
    if "search_results" in st.session_state and st.session_state.search_results:
        metrics = st.session_state.search_results["metrics"]
        
        st.markdown(f"""
        <div style="display: grid; grid-template-columns: 1fr; gap: 15px; margin-top: 10px;">
            <div class="metric-card">
                <div class="metric-title">1a. Dense Embedding (BGE)</div>
                <div class="metric-value">{metrics['dense_embedding_ms']:.2f} ms</div>
            </div>
            <div class="metric-card">
                <div class="metric-title">1b. Sparse Hashing (FNV-1a)</div>
                <div class="metric-value">{metrics['sparse_embedding_ms']:.2f} ms</div>
            </div>
            <div class="metric-card">
                <div class="metric-title">1c. Qdrant Hybrid Search (RRF)</div>
                <div class="metric-value">{metrics['db_hybrid_search_ms']:.2f} ms</div>
            </div>
            <div class="metric-card" style="border-color: rgba(31, 111, 235, 0.4)">
                <div class="metric-title" style="color: #58a6ff;">Total Retrieval (Stage 1)</div>
                <div class="metric-value" style="color: #58a6ff;">{metrics['retrieval_total_ms']:.2f} ms</div>
            </div>
            <div class="metric-card">
                <div class="metric-title">2. Reranker (Cross-Encoder)</div>
                <div class="metric-value">{metrics['reranking_ms']:.2f} ms</div>
            </div>
            <div class="metric-card" style="background: rgba(188, 140, 255, 0.1); border-color: rgba(188, 140, 255, 0.4);">
                <div class="metric-title" style="color: #bc8cff;">End-to-End Latency</div>
                <div class="metric-value metric-value-total">{metrics['pipeline_total_ms']:.2f} ms</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.info("Connect to backend and submit query to show live performance latency cards.")
