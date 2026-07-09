import os
import sys
import time
import requests
import pandas as pd
import altair as alt
import streamlit as st

# Page Configuration
st.set_page_config(
    page_title="Enterprise Scale-Ready RAG Control Center",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Shared Styling (Glassmorphism, Slate Dark Theme, Highlights)
st.markdown("""
<style>
    .stApp {
        background-color: #0d1117;
        color: #c9d1d9;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
    }
    
    .main-title {
        font-size: 2.6rem;
        font-weight: 800;
        background: linear-gradient(135deg, #58a6ff 0%, #bc8cff 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.1rem;
    }
    
    .subtitle {
        font-size: 1.05rem;
        color: #8b949e;
        margin-bottom: 1.5rem;
    }
    
    /* Custom card styles */
    .dashboard-card {
        background: rgba(22, 27, 34, 0.75);
        border: 1px solid rgba(48, 54, 61, 0.8);
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 15px;
        backdrop-filter: blur(12px);
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
    }
    
    .card-title {
        font-size: 0.85rem;
        text-transform: uppercase;
        color: #8b949e;
        font-weight: bold;
        margin-bottom: 8px;
    }
    
    .card-value {
        font-size: 1.8rem;
        font-weight: 700;
        color: #58a6ff;
    }
    
    .card-value-cost {
        color: #bc8cff;
    }

    /* Highlighted overlap text */
    .overlap-box {
        background: rgba(188, 140, 255, 0.1);
        border-left: 4px solid #bc8cff;
        padding: 12px;
        border-radius: 6px;
        margin-bottom: 12px;
        font-family: monospace;
        font-size: 0.9rem;
        line-height: 1.5;
    }
    
    .overlap-prefix {
        color: #bc8cff;
        font-weight: bold;
        background: rgba(188, 140, 255, 0.15);
        padding: 2px 4px;
        border-radius: 3px;
        margin-right: 4px;
    }
    
    /* Diagnostic visual shapes */
    .dia-box {
        background: #161b22;
        border: 1px solid #30363d;
        border-radius: 8px;
        padding: 12px;
        margin-bottom: 8px;
    }
    
    .badge-rrf {
        background-color: #1f6feb;
        color: white;
        padding: 2px 8px;
        border-radius: 10px;
        font-size: 0.75rem;
        font-weight: bold;
    }
    
    .badge-rerank {
        background-color: #8957e5;
        color: white;
        padding: 2px 8px;
        border-radius: 10px;
        font-size: 0.75rem;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# Main Titles
st.markdown('<div class="main-title">Scale-Ready RAG Platform</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">FastAPI REST Server • Distributed Spark Pipelines • AWS S3 Integration • Cost-Optimized Token Billing</div>', unsafe_allow_html=True)

# Session state checks
if "backend_url" not in st.session_state:
    st.session_state.backend_url = "http://localhost:8000/api/v1"
if "connected" not in st.session_state:
    st.session_state.connected = False
if "last_query" not in st.session_state:
    st.session_state.last_query = None
if "last_response" not in st.session_state:
    st.session_state.last_response = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# Sidebar API Connection Manager
with st.sidebar:
    st.markdown("### 🔌 Microservice Configuration")
    st.session_state.backend_url = st.text_input("FastAPI Base Endpoint", value=st.session_state.backend_url)
    
    if st.button("🔌 Verify Connection"):
        with st.spinner("Connecting to REST server..."):
            try:
                res = requests.get(f"{st.session_state.backend_url}/health", timeout=5)
                if res.status_code == 200 and res.json().get("status") == "healthy":
                    st.session_state.connected = True
                    st.success("Connected to RAG API Backend!")
                else:
                    st.session_state.connected = False
                    st.error("API unhealthy.")
            except Exception as e:
                st.session_state.connected = False
                st.error(f"Connection failed: {e}")
                
    st.markdown("---")
    st.markdown("### 🗄️ Connect Data Lakehouse")
    s3_bucket = st.text_input("AWS S3 Bucket", value="enterprise-rag-lakehouse")
    s3_prefix = st.text_input("S3 Ingest Prefix", value="documents/")
    
    if st.button("🚀 Synchronize S3 Lakehouse"):
        if not st.session_state.connected:
            st.warning("Connect to the REST API backend first.")
        else:
            with st.spinner("Syncing AWS S3 and running Spark ingestion..."):
                try:
                    payload = {"bucket": s3_bucket, "prefix": s3_prefix}
                    res = requests.post(f"{st.session_state.backend_url}/ingest/s3", json=payload, timeout=120)
                    if res.status_code == 200:
                        chunks = res.json().get("total_chunks")
                        st.success(f"Synced! Distributed Spark loaded {chunks} chunks to Pinecone.")
                    else:
                        st.error(f"S3 ingestion failed: {res.json().get('detail')}")
                except Exception as e:
                    st.error(f"Network error: {e}")

# Create tabs for Multi-Tab UI dashboard
tabs = st.tabs([
    "💬 Conversational Hub", 
    "✂️ Interactive Chunking", 
    "🔍 Retrieval & Rerank Diagnostics", 
    "📊 Usage & Cost Analytics"
])

# ==========================================
# TAB 1: Conversational Hub
# ==========================================
with tabs[0]:
    col_chat, col_upload = st.columns([2, 1])
    
    with col_upload:
        st.subheader("Ingest Documents")
        st.info("Directly drop files or PDFs to clean, chunk, and load them into Pinecone immediately.")
        
        uploaded_file = st.file_uploader("Upload PDF or TXT", type=["pdf", "txt"])
        if uploaded_file is not None:
            if st.button("⚡ Ingest Uploaded File"):
                if not st.session_state.connected:
                    st.warning("Please connect to the REST API backend first.")
                else:
                    with st.spinner("Uploading and indexing file..."):
                        try:
                            # Post as multipart form
                            files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                            res = requests.post(f"{st.session_state.backend_url}/upload", files=files, timeout=60)
                            if res.status_code == 200:
                                total_chunks = res.json().get("total_chunks")
                                st.success(f"Indexed file successfully into {total_chunks} chunks.")
                            else:
                                st.error(f"Ingestion failed: {res.json().get('detail')}")
                        except Exception as e:
                            st.error(f"Network upload error: {e}")
                            
        st.markdown("---")
        st.subheader("Spark Batch Seed")
        if st.button("⚡ Run PySpark Local Ingestion"):
            if not st.session_state.connected:
                st.warning("Please connect to backend first.")
            else:
                with st.spinner("Seeding 1,000 corporate documents..."):
                    try:
                        res = requests.post(f"{st.session_state.backend_url}/ingest", timeout=120)
                        if res.status_code == 200:
                            st.success(f"Ingested {res.json().get('total_chunks')} chunks successfully.")
                        else:
                            st.error(res.json().get("detail"))
                    except Exception as e:
                        st.error(f"Error seeding: {e}")

    with col_chat:
        st.subheader("RAG Sandbox Chat")
        
        # Display history
        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
                
        # Chat input
        query = st.chat_input("Ask a question about policy limits, incident reports, or patient logs:")
        if query:
            # Display user query
            with st.chat_message("user"):
                st.markdown(query)
            st.session_state.chat_history.append({"role": "user", "content": query})
            
            if not st.session_state.connected:
                with st.chat_message("assistant"):
                    st.warning("Backend is not connected. Connect in the sidebar to retrieve real context.")
            else:
                with st.spinner("Querying vector database..."):
                    try:
                        payload = {"query": query, "top_k_hybrid": 30, "top_k_rerank": 5}
                        response = requests.post(f"{st.session_state.backend_url}/query", json=payload, timeout=20)
                        
                        if response.status_code == 200:
                            res_data = response.json()
                            
                            # Cache last response for Diagnostics
                            st.session_state.last_query = query
                            st.session_state.last_response = res_data
                            
                            # Display answer
                            with st.chat_message("assistant"):
                                st.markdown(res_data["answer"])
                                # Print small sources list
                                with st.expander("📚 Matched Source Doc References"):
                                    for idx, context in enumerate(res_data["results"][:2]):
                                        st.markdown(f"**Doc ID**: `{context['doc_id']}` (Chunk {context['chunk_index']})")
                                        st.markdown(f"*'{context['chunk_text']}'*")
                                        st.markdown("---")
                                        
                            st.session_state.chat_history.append({"role": "assistant", "content": res_data["answer"]})
                        else:
                            st.error("Error querying backend REST API.")
                    except Exception as e:
                        st.error(f"Query error: {e}")

# ==========================================
# TAB 2: Interactive Chunking Visualizer
# ==========================================
with tabs[1]:
    st.subheader("✂️ Recursive Chunker Visualizer")
    st.markdown("Inspect how the sliding recursive chunker cuts input text and overlays prefixes between adjacent chunks.")
    
    col_inp, col_vis = st.columns([1, 1])
    
    with col_inp:
        sample_text = st.text_area(
            "Target Ingestion Content",
            value=(
                "CLINICAL HEALTH REPORT - REGION 5\n"
                "Patient Bob Jones (age 45) was admitted to St. Jude Clinical Unit on 2026-06-15. "
                "The patient presented with elevated blood pressure and dry throat symptoms. "
                "Diagnosis: acute contact dermatitis. "
                "Treatment plan: Apply topical hydrocortisone twice daily and follow up in one week.\n\n"
                "STANDARD OPERATING PROCEDURE: SOP-2831\n"
                "Subject: Corporate Travel Reimbursement Policy. "
                "Purpose: To define allowable expense limits for standard business travel. "
                "Standard: Employees are permitted up to $75.00 daily for meals and incidentals. "
                "All items above $25.00 require a digital receipt upload.\n\n"
                "INCIDENT REPORT #4092\n"
                "Category: Infrastructure Outage. "
                "Description: Gateway Database session connection timeouts were observed at 14:02 UTC. "
                "Resolution: Restarted database endpoint pool, cleared transaction locks. Service restored."
            ),
            height=250
        )
        chunk_size = st.slider("Chunk Size Limit (Characters)", 100, 800, 300, step=50)
        chunk_overlap = st.slider("Chunk Overlap (Characters)", 10, 200, 50, step=10)
        
    with col_vis:
        # Run chunker
        from src.utils.chunker import RecursiveCharacterChunker
        chunker = RecursiveCharacterChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        chunks = chunker.chunk_text(sample_text)
        
        st.markdown(f"**Generated Chunks**: `{len(chunks)}` Chunks")
        
        for idx, chunk in enumerate(chunks):
            # Check overlap prefix from previous chunk (if any)
            overlap_prefix = ""
            main_body = chunk
            
            if idx > 0 and chunk_overlap > 0:
                # Find matching overlap prefix at the start of the current chunk
                # We can calculate the expected overlap characters by looking at the end of the previous chunk
                prev = chunks[idx - 1]
                expected_overlap = prev[-chunk_overlap:]
                
                # Highlight what matches
                # If current chunk starts with overlap prefix, separate it
                if chunk.startswith(expected_overlap):
                    overlap_prefix = expected_overlap
                    main_body = chunk[len(expected_overlap):]
                else:
                    # Fallback slice
                    overlap_prefix = chunk[:chunk_overlap]
                    main_body = chunk[chunk_overlap:]
            
            st.markdown(f"**Chunk {idx+1}** (Length: `{len(chunk)}` chars):")
            if overlap_prefix:
                st.markdown(f"""
                <div class="overlap-box">
                    <span class="overlap-prefix">Overlap:</span>{overlap_prefix}
                    <span style="color: #c9d1d9;">{main_body}</span>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class="overlap-box" style="border-left-color: #58a6ff;">
                    <span style="color: #c9d1d9;">{main_body}</span>
                </div>
                """, unsafe_allow_html=True)

# ==========================================
# TAB 3: Retrieval & Rerank Diagnostics
# ==========================================
with tabs[2]:
    st.subheader("🔍 Two-Stage Search Diagnostics")
    st.markdown("Inspect how Stage 1 hybrid retrieval (Pinecone RRF) candidates were re-ranked by the Stage 2 Cross-Encoder.")
    
    if not st.session_state.last_response:
        st.info("Submit a query in the Chat interface (Tab 1) to inspect diagnostics.")
    else:
        last_q = st.session_state.last_query
        res_data = st.session_state.last_response
        
        st.markdown(f"**Last Query**: *'{last_q}'*")
        
        # Build comparison dataframe
        records = []
        for idx, item in enumerate(res_data["results"]):
            records.append({
                "Rank": idx + 1,
                "Doc ID": item["doc_id"][:12] + "...",
                "Chunk Index": item["chunk_index"],
                "Stage 1 RRF Score": item["score"],
                "Stage 2 Rerank Score": item["rerank_score"],
                "Snippet": item["chunk_text"][:100] + "..."
            })
        df_diag = pd.DataFrame(records)
        
        st.dataframe(df_diag, use_container_width=True)
        
        # Side by side visual flow
        st.markdown("### Top Context Rerank Flow")
        col_s1, col_s2 = st.columns(2)
        
        with col_s1:
            st.markdown("#### Stage 1: Pinecone Query Hits")
            # Show hits sorted by Pinecone RRF score
            s1_sorted = sorted(res_data["results"], key=lambda x: x["score"], reverse=True)
            for idx, item in enumerate(s1_sorted[:3]):
                st.markdown(f"""
                <div class="dia-box" style="border-left: 4px solid #1f6feb;">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 6px;">
                        <span>Rank {idx+1} | Index: {item['chunk_index']}</span>
                        <span class="badge-rrf">RRF: {item['score']:.4f}</span>
                    </div>
                    <p style="margin: 0; font-size: 0.85rem; color: #8b949e;">{item['chunk_text'][:120]}...</p>
                </div>
                """, unsafe_allow_html=True)
                
        with col_s2:
            st.markdown("#### Stage 2: Cross-Encoder Reranked Context")
            # Show final reranked order
            for idx, item in enumerate(res_data["results"][:3]):
                st.markdown(f"""
                <div class="dia-box" style="border-left: 4px solid #8957e5;">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 6px;">
                        <span>Final Rank {idx+1}</span>
                        <span class="badge-rerank">Rerank Score: {item['rerank_score']:.4f}</span>
                    </div>
                    <p style="margin: 0; font-size: 0.85rem; color: #e6edf3;">{item['chunk_text'][:120]}...</p>
                </div>
                """, unsafe_allow_html=True)

# ==========================================
# TAB 4: Usage & Cost Analytics Dashboard
# ==========================================
with tabs[3]:
    st.subheader("📊 Token Billing & Cost Breakdown")
    st.markdown("Monitor resource billing rates and token counts accumulated by the microservice.")
    
    if not st.session_state.connected:
        st.warning("Connect to the backend in the sidebar to fetch live usage statistics.")
    else:
        # Fetch analytics
        try:
            res_an = requests.get(f"{st.session_state.backend_url}/analytics", timeout=5)
            if res_an.status_code == 200:
                an_data = res_an.json()
                
                # Render Metric Cards
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.markdown(f"""
                    <div class="dashboard-card">
                        <div class="card-title">Accumulated Cost</div>
                        <div class="card-value card-value-cost">${an_data['total_cost']:.6f}</div>
                    </div>
                    """, unsafe_allow_html=True)
                with col2:
                    st.markdown(f"""
                    <div class="dashboard-card">
                        <div class="card-title">Total Tokens</div>
                        <div class="card-value">{an_data['total_tokens']:,}</div>
                    </div>
                    """, unsafe_allow_html=True)
                with col3:
                    st.markdown(f"""
                    <div class="dashboard-card">
                        <div class="card-title">Queries Run</div>
                        <div class="card-value" style="color: #58a6ff;">{an_data['total_queries']}</div>
                    </div>
                    """, unsafe_allow_html=True)
                with col4:
                    st.markdown(f"""
                    <div class="dashboard-card">
                        <div class="card-title">Ingest pipelines</div>
                        <div class="card-value" style="color: #bc8cff;">{an_data['total_ingests']}</div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                # Charting Cost Allocation
                st.markdown("### Cost Allocation Breakdown")
                breakdown = an_data["cost_breakdown"]
                
                df_chart = pd.DataFrame({
                    "Phase": ["Dense Embedding", "Reranker Model", "LLM Prompt Input", "LLM Text Generation", "Pinecone Writes"],
                    "Cost ($)": [
                        breakdown["embedding"],
                        breakdown["rerank"],
                        breakdown["llm_input"],
                        breakdown["llm_output"],
                        breakdown["db_write"]
                    ]
                })
                
                # Render Bar Chart using Altair
                chart = alt.Chart(df_chart).mark_bar(
                    cornerRadiusTopLeft=4,
                    cornerRadiusTopRight=4
                ).encode(
                    x=alt.X("Phase:N", sort=None, title="Operational Phase"),
                    y=alt.Y("Cost ($):Q", title="Cost in USD"),
                    color=alt.Color("Phase:N", legend=None, scale=alt.Scale(scheme="purpleblue")),
                    tooltip=["Phase", "Cost ($)"]
                ).properties(
                    height=300
                )
                
                st.altair_chart(chart, use_container_width=True)
                
                # Model Catalog Pricing
                with st.expander("📝 Pipeline Pricing Catalog Rate Table"):
                    st.markdown("""
                    The RAG pipeline calculates operational billing costs using standard API tokenization rates:
                    - **Embedding Encoder (BGE-small)**: `$0.00002` per 1K tokens
                    - **Reranker Engine (Cross-Encoder)**: `$0.00010` per 1K tokens
                    - **LLM Prompt Input (Llama-3/Sonnet)**: `$0.00150` per 1K tokens
                    - **LLM Response Generation**: `$0.00200` per 1K tokens
                    - **Pinecone Serverless Index Updates**: `$0.00100` per 1K vectors upserted
                    """)
            else:
                st.error("Could not retrieve analytics data.")
        except Exception as e:
            st.error(f"Error connecting to analytics endpoint: {e}")
