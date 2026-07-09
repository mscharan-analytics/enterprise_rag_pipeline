import os
import sys
import time
import socket
import subprocess
import requests
import pandas as pd
import altair as alt
import streamlit as st

# Page Configuration
st.set_page_config(
    page_title="Document Intelligence Hub",
    page_icon="📂",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Shared Styling (Indigo theme, clean typography)
st.markdown("""
<style>
    /* Global Background and Typography */
    .stApp {
        background-color: #fafbfc;
        color: #1e293b;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", sans-serif;
    }
    
    /* Top Navigation Header */
    .hub-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 16px 32px;
        background-color: #ffffff;
        border-bottom: 1px solid #f1f5f9;
        margin-bottom: 30px;
        box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.03);
    }
    .hub-logo {
        font-size: 1.3rem;
        font-weight: 800;
        color: #4f46e5;
        letter-spacing: -0.5px;
    }
    .hub-status {
        font-size: 0.8rem;
        font-weight: 500;
        color: #64748b;
        background: #f1f5f9;
        padding: 4px 12px;
        border-radius: 9999px;
        border: 1px solid #e2e8f0;
    }

    /* Hero Headline Section */
    .hero-section {
        text-align: center;
        max-width: 750px;
        margin: 0 auto 35px auto;
        padding: 10px;
    }
    .hero-title {
        font-size: 2.4rem;
        font-weight: 800;
        color: #0f172a;
        letter-spacing: -1px;
        line-height: 1.2;
        margin-bottom: 12px;
    }
    .hero-subtitle {
        font-size: 1.05rem;
        color: #64748b;
        line-height: 1.5;
    }

    /* Cards */
    .hub-card {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 24px;
        margin-bottom: 20px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -2px rgba(0, 0, 0, 0.05);
    }
    .hub-card-title {
        font-size: 0.95rem;
        font-weight: 700;
        color: #0f172a;
        margin-bottom: 14px;
        border-bottom: 1px solid #f1f5f9;
        padding-bottom: 10px;
    }
    
    .search-container {
        max-width: 680px;
        margin: 0 auto 30px auto;
        text-align: center;
    }

    /* Report Memo style */
    .report-memo {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-left: 4px solid #4f46e5;
        border-radius: 8px;
        padding: 20px 24px;
        margin-bottom: 25px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.03);
    }
    .report-memo-header {
        font-size: 0.75rem;
        font-weight: 700;
        color: #475569;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 10px;
        border-bottom: 1px solid #f1f5f9;
        padding-bottom: 6px;
    }
    
    /* Reference Segment Cards */
    .segment-card {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 16px;
        margin-bottom: 10px;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.02);
    }
    .segment-card-header {
        display: flex;
        justify-content: space-between;
        font-size: 0.8rem;
        font-weight: 600;
        color: #64748b;
        border-bottom: 1px solid #f1f5f9;
        padding-bottom: 6px;
        margin-bottom: 10px;
    }
    
    /* Indigo Buttons */
    .stButton > button {
        background-color: #4f46e5 !important;
        color: #ffffff !important;
        border: 1px solid #4f46e5 !important;
        border-radius: 6px !important;
        font-size: 0.85rem !important;
        font-weight: 600 !important;
        padding: 8px 18px !important;
        transition: background-color 0.15s ease, transform 0.1s ease !important;
    }
    .stButton > button:hover {
        background-color: #4338ca !important;
        border-color: #4338ca !important;
        transform: translateY(-0.5px);
    }
    
    /* Analytic Tiles */
    .analytic-tile {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 16px;
        text-align: center;
        box-shadow: 0 1px 3px rgba(0,0,0,0.02);
    }
    .analytic-label {
        font-size: 0.75rem;
        color: #64748b;
        font-weight: 600;
        text-transform: uppercase;
        margin-bottom: 4px;
        letter-spacing: 0.5px;
    }
    .analytic-val {
        font-size: 1.5rem;
        font-weight: 800;
        color: #0f172a;
    }
    .analytic-val-cost {
        color: #0f766e;
    }

    /* Monospace Chunks */
    .monobox {
        background-color: #fafbfc;
        border: 1px solid #e2e8f0;
        border-radius: 6px;
        padding: 10px 14px;
        font-family: Menlo, Monaco, Consolas, monospace;
        font-size: 0.8rem;
        line-height: 1.4;
        color: #334155;
    }
    .tag-overlap {
        color: #4f46e5;
        font-weight: bold;
        background: #e0e7ff;
        padding: 1px 4px;
        border-radius: 3px;
        margin-right: 4px;
    }

    /* Diagnostics */
    .diag-item {
        border-bottom: 1px solid #f1f5f9;
        padding: 8px 0;
        font-size: 0.8rem;
    }
    .diag-item:last-child {
        border-bottom: none;
    }
    .badge-blue {
        background-color: #e0f2fe;
        color: #0369a1;
        padding: 1px 6px;
        border-radius: 4px;
        font-weight: 600;
    }
    .badge-purple {
        background-color: #f3e8ff;
        color: #6b21a8;
        padding: 1px 6px;
        border-radius: 4px;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# Programmatically launch FastAPI service on port 8000 if not running
@st.cache_resource
def launch_background_api():
    """
    Check if FastAPI server is already running on port 8000.
    If not, launch it programmatically in a separate subprocess.
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    port_in_use = False
    try:
        s.bind(("127.0.0.1", 8000))
    except socket.error:
        port_in_use = True
    finally:
        s.close()
        
    if not port_in_use:
        # Launch using the current python interpreter running streamlit
        subprocess.Popen([sys.executable, "-m", "uvicorn", "src.api.main:app", "--host", "127.0.0.1", "--port", "8000"])
        # Wait a moment for application startup
        time.sleep(3)

# Initialize background API
launch_background_api()

# 1. Premium Header Navigation
st.markdown("""
<div class="hub-header">
    <div class="hub-logo">DocHub</div>
    <div class="hub-status">Enterprise Intelligence Hub • Active</div>
</div>
""", unsafe_allow_html=True)

# Initialize Session States
if "backend_url" not in st.session_state:
    st.session_state.backend_url = "http://localhost:8000/api/v1"
if "connected" not in st.session_state:
    st.session_state.connected = False
if "last_query" not in st.session_state:
    st.session_state.last_query = None
if "last_response" not in st.session_state:
    st.session_state.last_response = None
if "results_list" not in st.session_state:
    st.session_state.results_list = []

# Verify localhost connection automatically on first load
if not st.session_state.connected:
    try:
        res = requests.get(f"{st.session_state.backend_url}/health", timeout=3)
        if res.status_code == 200 and res.json().get("status") == "healthy":
            st.session_state.connected = True
    except Exception:
        pass

# Sidebar Config
with st.sidebar:
    st.markdown("### Settings")
    st.session_state.backend_url = st.text_input("Endpoint Gateway", value=st.session_state.backend_url)
    
    if st.button("🔌 Verify Gateway"):
        with st.spinner("Pinging gateway..."):
            try:
                res = requests.get(f"{st.session_state.backend_url}/health", timeout=5)
                if res.status_code == 200 and res.json().get("status") == "healthy":
                    st.session_state.connected = True
                    st.success("API Status: Connected")
                else:
                    st.session_state.connected = False
                    st.error("API Status: Offline")
            except Exception as e:
                st.session_state.connected = False
                st.error("API Status: Offline")
                
    st.markdown("---")
    st.markdown("### Lakehouse Configuration")
    s3_bucket = st.text_input("S3 Bucket", value="enterprise-rag-lakehouse")
    s3_prefix = st.text_input("S3 Directory Prefix", value="documents/")
    
    if st.button("🚀 Ingest from Lakehouse"):
        if not st.session_state.connected:
            st.warning("Connect to the API gateway first.")
        else:
            with st.spinner("Synchronizing bucket and executing PySpark ingestion..."):
                try:
                    payload = {"bucket": s3_bucket, "prefix": s3_prefix}
                    res = requests.post(f"{st.session_state.backend_url}/ingest/s3", json=payload, timeout=120)
                    if res.status_code == 200:
                        chunks = res.json().get("total_chunks")
                        st.success(f"Ingested {chunks} segments to Pinecone.")
                    else:
                        st.error(f"Sync failed: {res.json().get('detail')}")
                except Exception as e:
                    st.error(f"Gateway connection failure: {e}")

# Multi-Tab Workspaces (Modern Lovable styling)
tabs = st.tabs([
    "Document Search", 
    "Chunk Visualizer", 
    "Retrieval Diagnostics", 
    "Cost Analytics"
])

# ==========================================
# TAB 1: Document Search Hub
# ==========================================
with tabs[0]:
    # Modern Centered Search Header
    st.markdown("""
    <div class="hero-section">
        <div class="hero-title">Docs & Knowledge Hub</div>
        <div class="hero-subtitle">Ingest, analyze, and query corporate resources in a secure, unified workspace powered by Spark and Pinecone.</div>
    </div>
    """, unsafe_allow_html=True)
    
    col_portal, col_uploads = st.columns([12, 6])
    
    with col_uploads:
        # File uploads card
        st.markdown('<div class="hub-card">', unsafe_allow_html=True)
        st.markdown('<div class="hub-card-title">Upload Documents</div>', unsafe_allow_html=True)
        
        uploaded_file = st.file_uploader("Upload local PDF or TXT file", type=["pdf", "txt"], label_visibility="collapsed")
        if uploaded_file is not None:
            if st.button("Process Document"):
                if not st.session_state.connected:
                    st.warning("Establish Gateway connection in the sidebar settings first.")
                else:
                    with st.spinner("Extracting and loading document..."):
                        try:
                            files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                            res = requests.post(f"{st.session_state.backend_url}/upload", files=files, timeout=60)
                            if res.status_code == 200:
                                total_chunks = res.json().get("total_chunks")
                                st.success(f"Indexed document into {total_chunks} segments.")
                            else:
                                st.error(f"Processing error: {res.json().get('detail')}")
                        except Exception as e:
                            st.error(f"Network upload error: {e}")
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Batch seeding card
        st.markdown('<div class="hub-card">', unsafe_allow_html=True)
        st.markdown('<div class="hub-card-title">PySpark Batch ETL</div>', unsafe_allow_html=True)
        st.markdown("<p style='font-size:0.8rem; color:#64748b; margin-top:0;'>Run distributed Spark cleanup and embedding nodes to seed the vector database.</p>", unsafe_allow_html=True)
        if st.button("Run Spark Seeding Pipeline"):
            if not st.session_state.connected:
                st.warning("Establish Gateway connection first.")
            else:
                with st.spinner("Executing PySpark ETL job..."):
                    try:
                        res = requests.post(f"{st.session_state.backend_url}/ingest", timeout=120)
                        if res.status_code == 200:
                            st.success(f"Spark loaded {res.json().get('total_chunks')} segments successfully.")
                        else:
                            st.error(res.json().get("detail"))
                    except Exception as e:
                        st.error(f"ETL pipeline failure: {e}")
        st.markdown("</div>", unsafe_allow_html=True)

    with col_portal:
        st.markdown('<div class="hub-card">', unsafe_allow_html=True)
        st.markdown('<div class="hub-card-title">Search Sandbox</div>', unsafe_allow_html=True)
        
        # Modern Search Input Box
        st.markdown('<div class="search-container">', unsafe_allow_html=True)
        query = st.text_input(
            "Ask a question to retrieve matched knowledge:",
            placeholder="Type query to retrieve...",
            label_visibility="collapsed"
        )
        st.markdown('</div>', unsafe_allow_html=True)
        
        if query:
            if not st.session_state.connected:
                st.warning("API Gateway offline. Verify connection in the sidebar.")
            else:
                with st.spinner("Querying indexes..."):
                    try:
                        payload = {"query": query, "top_k_hybrid": 30, "top_k_rerank": 5}
                        response = requests.post(f"{st.session_state.backend_url}/query", json=payload, timeout=20)
                        
                        if response.status_code == 200:
                            res_data = response.json()
                            
                            # Cache search queries for Diagnostics
                            st.session_state.last_query = query
                            st.session_state.last_response = res_data
                            
                            st.session_state.results_list = [{
                                "query": query,
                                "answer": res_data["answer"],
                                "results": res_data["results"]
                            }]
                        else:
                            st.error("Error executing query against gateway.")
                    except Exception as e:
                        st.error(f"Network error: {e}")
                        
        # Displays the Query output as a clean executive memorandum
        if st.session_state.results_list:
            active = st.session_state.results_list[0]
            
            st.markdown(f"""
            <div class="report-memo">
                <div class="report-memo-header">Executive Summary Report</div>
                <div>{active['answer']}</div>
            </div>
            """, unsafe_allow_html=True)
            
            # Displays retrieved source documents cleanly without cluttering the screen
            st.markdown("#### Matched Reference Documents")
            for idx, item in enumerate(active["results"]):
                with st.expander(f"Reference Segment {idx+1} (Doc: {item['doc_id'][:12]}... • Index: {item['chunk_index']})"):
                    st.markdown(f"""
                    <div style="font-size: 0.85rem; color: #334155; line-height: 1.5; background: #fafafa; padding: 12px; border: 1px solid #e2e8f0; border-radius: 4px;">
                        "{item['chunk_text']}"
                    </div>
                    """, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

# ==========================================
# TAB 2: Chunk Visualizer
# ==========================================
with tabs[1]:
    st.markdown('<div class="hub-card">', unsafe_allow_html=True)
    st.markdown('<div class="hub-card-title">Interactive Segmentation Visualizer</div>', unsafe_allow_html=True)
    
    col_arg, col_txt = st.columns([1, 1])
    
    with col_arg:
        text_input = st.text_area(
            "Target Parsing Document Block",
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
            height=230
        )
        ch_size = st.slider("Target Segment size (Chars)", 100, 800, 300, step=50)
        ch_overlap = st.slider("Target Overlap Size (Chars)", 10, 200, 50, step=10)
        
    with col_txt:
        from src.utils.chunker import RecursiveCharacterChunker
        chunker = RecursiveCharacterChunker(chunk_size=ch_size, chunk_overlap=ch_overlap)
        chunks = chunker.chunk_text(text_input)
        
        st.markdown(f"**Total Segments Formed**: `{len(chunks)}` blocks")
        
        for idx, chunk in enumerate(chunks):
            overlap_prefix = ""
            body_text = chunk
            
            if idx > 0 and ch_overlap > 0:
                prev_ch = chunks[idx - 1]
                target_prefix = prev_ch[-ch_overlap:]
                
                if chunk.startswith(target_prefix):
                    overlap_prefix = target_prefix
                    body_text = chunk[len(target_prefix):]
                else:
                    overlap_prefix = chunk[:ch_overlap]
                    body_text = chunk[ch_overlap:]
            
            st.markdown(f"**Segment {idx+1}** ({len(chunk)} chars):")
            if overlap_prefix:
                st.markdown(f"""
                <div class="monobox">
                    <span class="tag-overlap">Overlap:</span>{overlap_prefix}
                    <span style="color: #64748b;">{body_text}</span>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class="monobox" style="border-left: 3px solid #4f46e5;">
                    <span style="color: #64748b;">{body_text}</span>
                </div>
                """, unsafe_allow_html=True)
                
    st.markdown("</div>", unsafe_allow_html=True)

# ==========================================
# TAB 3: Retrieval Diagnostics
# ==========================================
with tabs[2]:
    st.markdown('<div class="hub-card">', unsafe_allow_html=True)
    st.markdown('<div class="hub-card-title">Two-Stage Retrieval Diagnostic Flow</div>', unsafe_allow_html=True)
    
    if not st.session_state.last_response:
        st.info("Execute a search query in the Sandbox (Tab 1) to inspect diagnostics.")
    else:
        active_q = st.session_state.last_query
        res_payload = st.session_state.last_response
        
        st.markdown(f"**Search Query**: *'{active_q}'*")
        
        comparisons = []
        for idx, item in enumerate(res_payload["results"]):
            comparisons.append({
                "Rank": idx + 1,
                "Doc ID": item["doc_id"][:12] + "...",
                "Segment ID": item["chunk_index"],
                "Stage 1 DB Score": f"{item['score']:.4f}",
                "Stage 2 Rerank Score": f"{item['rerank_score']:.4f}",
                "Excerpt": item["chunk_text"][:95] + "..."
            })
        df_diag = pd.DataFrame(comparisons)
        
        st.dataframe(df_diag, use_container_width=True)
        
        st.markdown("### Top Candidate Re-ranking Alignment")
        col_st1, col_st2 = st.columns(2)
        
        with col_st1:
            st.markdown("#### Stage 1: Raw Pinecone Hits (RRF Score)")
            st1_ordered = sorted(res_payload["results"], key=lambda x: x["score"], reverse=True)
            for idx, item in enumerate(st1_ordered[:3]):
                st.markdown(f"""
                <div class="diag-item">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 2px; font-weight: 600;">
                        <span>Match {idx+1} | Segment: {item['chunk_index']}</span>
                        <span class="badge-blue">DB: {item['score']:.4f}</span>
                    </div>
                    <div style="color: #64748b;">{item['chunk_text'][:120]}...</div>
                </div>
                """, unsafe_allow_html=True)
                
        with col_st2:
            st.markdown("#### Stage 2: Reranked Matches (Relevance Score)")
            for idx, item in enumerate(res_payload["results"][:3]):
                st.markdown(f"""
                <div class="diag-item">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 2px; font-weight: 600;">
                        <span>Rank {idx+1} | Segment: {item['chunk_index']}</span>
                        <span class="badge-purple">Rerank: {item['rerank_score']:.4f}</span>
                    </div>
                    <div style="color: #1e293b;">{item['chunk_text'][:120]}...</div>
                </div>
                """, unsafe_allow_html=True)
                
    st.markdown("</div>", unsafe_allow_html=True)

# ==========================================
# TAB 4: Cost Analytics
# ==========================================
with tabs[3]:
    st.markdown('<div class="hub-card">', unsafe_allow_html=True)
    st.markdown('<div class="hub-card-title">Token Billing & Operational Analytics</div>', unsafe_allow_html=True)
    
    if not st.session_state.connected:
        st.warning("Gateway connection offline. Establish connection settings in the sidebar.")
    else:
        try:
            res_an = requests.get(f"{st.session_state.backend_url}/analytics", timeout=5)
            if res_an.status_code == 200:
                an_data = res_an.json()
                
                # Display metric tiles
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.markdown(f"""
                    <div class="analytic-tile">
                        <div class="analytic-label">Accumulated Cost</div>
                        <div class="analytic-val analytic-val-cost">${an_data['total_cost']:.6f}</div>
                    </div>
                    """, unsafe_allow_html=True)
                with col2:
                    st.markdown(f"""
                    <div class="analytic-tile">
                        <div class="analytic-label">Billing Tokens Count</div>
                        <div class="analytic-val">{an_data['total_tokens']:,}</div>
                    </div>
                    """, unsafe_allow_html=True)
                with col3:
                    st.markdown(f"""
                    <div class="analytic-tile">
                        <div class="analytic-label">Queries Run</div>
                        <div class="analytic-val" style="color: #4f46e5;">{an_data['total_queries']}</div>
                    </div>
                    """, unsafe_allow_html=True)
                with col4:
                    st.markdown(f"""
                    <div class="analytic-tile">
                        <div class="analytic-label">Pipelines Executed</div>
                        <div class="analytic-val" style="color: #0f766e;">{an_data['total_ingests']}</div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                st.markdown("### Resource Billing Breakdown")
                breakdown = an_data["cost_breakdown"]
                
                df_chart = pd.DataFrame({
                    "Component": ["Embeddings (BGE)", "Reranker Model", "LLM Prompt Input", "LLM Text Generation", "Pinecone DB Writes"],
                    "Cost ($)": [
                        breakdown["embedding"],
                        breakdown["rerank"],
                        breakdown["llm_input"],
                        breakdown["llm_output"],
                        breakdown["db_write"]
                    ]
                })
                
                # Altair bar chart styled in modern indigo
                chart = alt.Chart(df_chart).mark_bar(
                    size=26,
                    cornerRadiusTopLeft=4,
                    cornerRadiusTopRight=4
                ).encode(
                    x=alt.X("Component:N", sort=None, title="ETL / Query Service Layer"),
                    y=alt.Y("Cost ($):Q", title="Cost (USD)"),
                    color=alt.value("#4f46e5"),  # Indigo
                    tooltip=["Component", "Cost ($)"]
                ).properties(
                    height=290
                )
                
                st.altair_chart(chart, use_container_width=True)
                
                with st.expander("Rate Table Catalog Rate"):
                    st.markdown("""
                    Operational pricing parameters utilized for billing calculations:
                    - **Embedding (BGE-small)**: `$0.00002` / 1,000 tokens
                    - **Reranker (Cross-Encoder)**: `$0.00010` / 1,000 tokens
                    - **LLM Input Context**: `$0.00150` / 1,000 tokens
                    - **LLM Output Completion**: `$0.00200` / 1,000 tokens
                    - **Pinecone Serverless updates**: `$0.00100` / 1,000 vectors
                    """)
            else:
                st.error("Could not fetch billing details.")
        except Exception as e:
            st.error(f"Analytics gateway connection error: {e}")
            
    st.markdown("</div>", unsafe_allow_html=True)
