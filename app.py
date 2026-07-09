import os
import sys
import time
import streamlit as st

os.environ["JAVA_HOME"] = "/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home"
os.environ["PATH"] = f"/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home/bin:{os.environ.get('PATH', '')}"

# Add project root to python path to resolve imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Page Config
st.set_page_config(
    page_title="Enterprise Scale-Ready RAG Prototype",
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
    .chat-user {
        background-color: #1f6feb22;
        border: 1px solid #1f6feb44;
        text-align: right;
    }
    .chat-assistant {
        background-color: #161b22;
        border: 1px solid #30363d;
    }
</style>
""", unsafe_allow_html=True)

# Application Heading
st.markdown('<div class="main-title">Scale-Ready RAG Control Center</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Distributed PySpark Ingestion • Custom Stable Sparse Term Hashing • Two-Stage RRF Hybrid Vector Search</div>', unsafe_allow_html=True)

# Initialize Session States
if "search_engine" not in st.session_state:
    st.session_state.search_engine = None

# Sidebar Controls
with st.sidebar:
    st.image("https://qdrant.tech/images/qdrant_logo.png", width=120)
    st.markdown("### Configuration & Engine")
    
    # Embedded vs Docker Qdrant toggle
    use_embedded = st.checkbox("Run in Embedded Mode (Local File)", value=True, 
                               help="Enable this to run Qdrant in-process via local storage without Docker.")
    
    # Save selection to config / environment
    os.environ["USE_EMBEDDED_QDRANT"] = str(use_embedded)
    
    # Instantiate Search Engine Button
    if st.button("🔌 Connect/Load Search Engine"):
        with st.spinner("Initializing models and Vector DB client..."):
            try:
                # Dynamically write back config selection
                from src import config
                config.USE_EMBEDDED_QDRANT = use_embedded
                
                from src.retrieval.search import RAGSearchEngine
                st.session_state.search_engine = RAGSearchEngine()
                st.success("Search Engine initialized successfully!")
            except Exception as e:
                st.error(f"Failed to load search engine: {e}")
                
    st.markdown("---")
    st.markdown("### LLM Generator Settings")
    llm_provider = st.selectbox("LLM Provider", ["Local Smart Mock Generator", "Groq Cloud API", "OpenAI API"])
    api_key = st.text_input("API Key", type="password", help=f"Enter API Key for {llm_provider} if selected.")
    
    st.markdown("---")
    st.markdown("### Retrieval Tuning")
    top_k_hybrid = st.slider("Stage 1 (Hybrid Matches)", 10, 100, 30)
    top_k_rerank = st.slider("Stage 2 (Reranked Contexts)", 2, 10, 5)
    
    st.markdown("---")
    st.markdown("### Database Initializer (Ingestion)")
    st.info("Generates 1,000 synthetic files and runs PySpark local ingestion. Requires Java 17 and dependencies installed.")
    
    if st.button("🚀 Ingest / Seed Database"):
        status_box = st.empty()
        with st.spinner("Seeding database..."):
            try:
                status_box.text("Phase 1/2: Generating data...")
                from data import generate_data
                generate_data.main()
                
                status_box.text("Phase 2/2: Launching PySpark ingestion...")
                from src.ingestion import pipeline
                # Make sure ingestion environment knows mode
                pipeline.USE_EMBEDDED_QDRANT = use_embedded
                pipeline.run_pipeline()
                
                status_box.success("Database seeded and index compiled!")
            except Exception as e:
                st.error(f"Ingestion failed: {e}")
                import traceback
                st.code(traceback.format_exc())

# Main Screen Layout
col_query, col_metrics = st.columns([2, 1])

# Mock LLM generation function
def get_mock_response(query: str, contexts: list) -> str:
    if not contexts:
        return "I apologize, but no relevant document chunks were found in the database. Please verify ingestion is complete."
        
    query_lower = query.lower()
    
    # Synthesize answers based on keywords
    if "clinical" in query_lower or "patient" in query_lower or "medical" in query_lower or "prescrib" in query_lower:
        base = "### 🩺 Clinical Case Synthesis\nBased on patient records matching the inquiry, we synthesized the following details:\n\n"
        for i, c in enumerate(contexts[:2]):
            base += f"- **Patient Context {i+1}**: {c['chunk_text']}\n"
        base += "\n**Recommendation**: Follow-up treatment plans should align with clinical history."
        return base
        
    elif "ticket" in query_lower or "error" in query_lower or "fail" in query_lower or "service" in query_lower:
        base = "### 💻 Infrastructure Incident Report\nAn analysis of the server log reports indicates:\n\n"
        for i, c in enumerate(contexts[:2]):
            base += f"- **Incident Note {i+1}**: {c['chunk_text']}\n"
        base += "\n**Status**: Issue escalated or resolved based on the standard engineering runbook."
        return base
        
    elif "policy" in query_lower or "sop" in query_lower or "employee" in query_lower:
        base = "### 📋 Corporate Operations Policy Summary\nAccording to the corporate guidelines retrieved from the HR directory:\n\n"
        for i, c in enumerate(contexts[:2]):
            base += f"- **Policy excerpt {i+1}**: {c['chunk_text']}\n"
        base += "\n**Verification**: Ensure manager approval is logged via standard request workflow."
        return base
        
    else:
        # Default smart summary
        base = "### 🔍 Synthesized Document Context\nThe query matched multiple corporate documents. Summarizing relevant entries:\n\n"
        for i, c in enumerate(contexts[:3]):
            base += f"- **Entry {i+1}** (Doc ID: `{c['doc_id'][:12]}...`): {c['chunk_text']}\n"
        return base

# Live LLM Generator function
def get_live_response(query: str, contexts: list, provider: str, api_key: str) -> str:
    context_str = "\n\n".join([f"Document Chunk (Doc ID: {c['doc_id']}):\n{c['chunk_text']}" for c in contexts])
    prompt = f"""You are a professional RAG assistant representing an enterprise knowledge base. 
Answer the user's question accurately using only the provided context. Do not make up information.
If the answer is not in the context, say "I cannot find the answer in the retrieved knowledge base."

Context:
{context_str}

Question: {query}
Answer:"""

    try:
        if provider == "Groq Cloud API":
            import groq
            client = groq.Groq(api_key=api_key)
            completion = client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama3-8b-8192",
            )
            return completion.choices[0].message.content
        elif provider == "OpenAI API":
            import openai
            client = openai.OpenAI(api_key=api_key)
            completion = client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="gpt-3.5-turbo",
            )
            return completion.choices[0].message.content
    except Exception as e:
        return f"⚠️ LLM API Error: {e}. Please check your API key and connection."

with col_query:
    st.subheader("Query Sandbox")
    
    if st.session_state.search_engine is None:
        st.warning("⚠️ Please connect to the Search Engine using the sidebar button before querying.")
        query_input = st.text_input("Enter query", disabled=True)
    else:
        query_input = st.text_input("Ask a question to the retrieved knowledge base:", 
                                    placeholder="e.g. Find clinical log with prescription details, or policy standard")
        
        if query_input:
            # Execute Search
            with st.spinner("Retrieving from index..."):
                search_results = st.session_state.search_engine.search(
                    query_input, 
                    top_k_hybrid=top_k_hybrid, 
                    top_k_rerank=top_k_rerank
                )
                
            # Store search results in session state for metrics/diagnostics
            st.session_state.search_results = search_results
            
            # Synthesize Answer
            st.markdown("### Answer")
            if llm_provider == "Local Smart Mock Generator":
                answer = get_mock_response(query_input, search_results["results"])
            else:
                if not api_key:
                    st.error("Please supply an API Key in the sidebar to generate response.")
                    answer = "Missing API Key."
                else:
                    answer = get_live_response(query_input, search_results["results"], llm_provider, api_key)
                    
            st.markdown(f'<div class="chat-bubble chat-assistant">{answer}</div>', unsafe_allow_html=True)
            
            # --- DIAGNOSTICS ---
            st.markdown("### 🛠️ Diagnostics & Pipeline Walkthrough")
            
            # 1. Stage 2 Reranked output
            with st.expander("Stage 2: Reranked Context Chunks (Top Match Results)", expanded=True):
                for idx, item in enumerate(search_results["results"]):
                    st.markdown(f"""
                    <div class="chunk-container">
                        <div class="chunk-header">
                            <span><b>Rank {idx+1}</b> | Doc: <span style="font-family: monospace;">{item['doc_id']}</span> | Chunk {item['chunk_index']}</span>
                            <span class="rerank-badge">Rerank Score: {item['rerank_score']:.4f}</span>
                        </div>
                        <p style="margin: 0; font-size: 0.95rem; line-height: 1.4; color: #e6edf3;">{item['chunk_text']}</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
            # 2. Stage 1 Raw retrieved output
            with st.expander(f"Stage 1: Raw Hybrid Search Candidates (Reciprocal Rank Fusion - Top {top_k_hybrid})"):
                for idx, item in enumerate(search_results["raw_hits"]):
                    st.markdown(f"""
                    <div class="chunk-container">
                        <div class="chunk-header">
                            <span><b>Candidate {idx+1}</b> | Doc: <span style="font-family: monospace;">{item['doc_id']}</span> | Chunk {item['chunk_index']}</span>
                            <span class="score-badge">RRF Score: {item['score']:.4f}</span>
                        </div>
                        <p style="margin: 0; font-size: 0.9rem; line-height: 1.4; color: #8b949e;">{item['chunk_text']}</p>
                    </div>
                    """, unsafe_allow_html=True)

# Latency sidebar / metrics panel
with col_metrics:
    st.subheader("Performance Latency")
    
    if "search_results" in st.session_state:
        metrics = st.session_state.search_results["metrics"]
        
        # Grid layout for metrics
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
        st.info("Submit a search query to inspect real-time performance breakdown.")
