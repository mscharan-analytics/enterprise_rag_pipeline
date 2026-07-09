import os
import sys
import time
import requests
import pandas as pd
import altair as alt
import streamlit as st

# Page Configuration
st.set_page_config(
    page_title="AWS Document Intelligence Console",
    page_icon="☁️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS mimicking the AWS Management Console Design System (Amazon Ember UI style)
st.markdown("""
<style>
    /* AWS Console Light Theme Background */
    .stApp {
        background-color: #f2f3f3;
        color: #16191f;
        font-family: "Amazon Ember", "Helvetica Neue", Roboto, Arial, sans-serif;
    }
    
    /* AWS Top Navigation Bar */
    .aws-nav-bar {
        background-color: #232f3e;
        color: #ffffff;
        padding: 10px 20px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 20px;
        border-radius: 2px;
        box-shadow: 0 1px 4px 0 rgba(0,0,0,0.1);
    }
    .aws-nav-title {
        font-size: 1.25rem;
        font-weight: 700;
        margin: 0;
        letter-spacing: 0.5px;
    }
    .aws-nav-region {
        font-size: 0.8rem;
        background: #35475e;
        padding: 3px 8px;
        border-radius: 2px;
        color: #d1d5db;
        font-family: monospace;
    }

    /* Console Page Header */
    .console-header {
        margin-bottom: 20px;
    }
    .console-title {
        font-size: 1.6rem;
        font-weight: 600;
        color: #16191f;
        margin: 0 0 4px 0;
    }
    .console-desc {
        font-size: 0.85rem;
        color: #545b64;
        margin: 0;
    }
    
    /* AWS White Container Cards */
    .aws-container {
        background-color: #ffffff;
        border: 1px solid #eaeded;
        border-radius: 2px;
        padding: 24px;
        margin-bottom: 16px;
        box-shadow: 0 1px 1px 0 rgba(0, 0, 0, 0.05);
    }
    .aws-container-title {
        font-size: 1rem;
        font-weight: 600;
        color: #16191f;
        border-bottom: 1px solid #eaeded;
        padding-bottom: 10px;
        margin-bottom: 16px;
        text-transform: capitalize;
    }
    
    /* AWS Action Buttons */
    .stButton > button {
        background-color: #ec7211 !important; /* AWS Orange */
        color: #ffffff !important;
        border: 1px solid #ec7211 !important;
        border-radius: 2px !important;
        font-size: 0.85rem !important;
        font-weight: 600 !important;
        padding: 6px 16px !important;
        transition: background-color 0.1s ease !important;
    }
    .stButton > button:hover {
        background-color: #d05c08 !important;
        border-color: #d05c08 !important;
    }
    
    /* Secondary/Form buttons */
    .stButton.secondary-btn > button {
        background-color: #ffffff !important;
        color: #545b64 !important;
        border: 1px solid #545b64 !important;
    }
    .stButton.secondary-btn > button:hover {
        background-color: #f2f3f3 !important;
    }
    
    /* AWS Console Metric Tiles */
    .aws-metric-tile {
        border-left: 3px solid #0073bb; /* AWS Blue */
        padding-left: 12px;
        margin-bottom: 16px;
    }
    .aws-metric-label {
        font-size: 0.75rem;
        color: #545b64;
        text-transform: uppercase;
        font-weight: 500;
        margin-bottom: 2px;
    }
    .aws-metric-value {
        font-size: 1.4rem;
        font-weight: 700;
        color: #16191f;
    }
    .aws-metric-value-cost {
        color: #1d8102; /* Green for cost */
    }

    /* Executive Memo Block */
    .memo-block {
        background-color: #fafafa;
        border: 1px solid #eaeded;
        border-left: 4px solid #0073bb;
        padding: 16px;
        border-radius: 2px;
        font-size: 0.9rem;
        line-height: 1.5;
        color: #16191f;
        margin-bottom: 20px;
    }
    .memo-header {
        font-size: 0.75rem;
        font-weight: 700;
        color: #545b64;
        text-transform: uppercase;
        margin-bottom: 8px;
        letter-spacing: 0.5px;
    }
    
    /* Simple Monospace Overlap View */
    .chunk-overlap-box {
        background-color: #f8f9fa;
        border: 1px solid #eaeded;
        padding: 8px 12px;
        font-family: monospace;
        font-size: 0.8rem;
        color: #24292e;
        margin-bottom: 8px;
        border-radius: 2px;
    }
    .overlap-tag {
        color: #ec7211;
        font-weight: bold;
        background: #fdf2e9;
        padding: 1px 3px;
        border: 1px solid #fcd3b2;
        border-radius: 2px;
    }

    /* Minimalist Side-by-Side Diagnostic Rows */
    .console-row {
        border-bottom: 1px solid #eaeded;
        padding: 10px 0;
        font-size: 0.8rem;
    }
    .console-row:last-child {
        border-bottom: none;
    }
    
    /* Form Label Styling */
    .stTextInput label, .stSlider label {
        font-size: 0.8rem !important;
        font-weight: 600 !important;
        color: #545b64 !important;
    }
</style>
""", unsafe_allow_html=True)

# 1. AWS Top Navigation Bar
st.markdown("""
<div class="aws-nav-bar">
    <div class="aws-nav-title">Amazon Document Intelligence</div>
    <div class="aws-nav-region">us-east-1 (N. Virginia)</div>
</div>
""", unsafe_allow_html=True)

# 2. Console Page Header
st.markdown("""
<div class="console-header">
    <div class="console-title">Document Indexing & Search Console</div>
    <div class="console-desc">ETL ingestion workflows, hybrid vector retrieval query configurations, and token costing allocations.</div>
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

# Sidebar Configuration Settings
with st.sidebar:
    st.markdown("### System Gateways")
    st.session_state.backend_url = st.text_input("REST Endpoint URL", value=st.session_state.backend_url)
    
    if st.button("Test Gateway Status"):
        with st.spinner("Connecting..."):
            try:
                res = requests.get(f"{st.session_state.backend_url}/health", timeout=5)
                if res.status_code == 200 and res.json().get("status") == "healthy":
                    st.session_state.connected = True
                    st.success("API status: Active")
                else:
                    st.session_state.connected = False
                    st.error("API status: Offline")
            except Exception as e:
                st.session_state.connected = False
                st.error("API status: Offline")
                
    st.markdown("---")
    st.markdown("### S3 Data Source Configuration")
    s3_bucket = st.text_input("AWS S3 Bucket Name", value="enterprise-rag-lakehouse")
    s3_prefix = st.text_input("S3 Directory Prefix", value="documents/")
    
    if st.button("Sync S3 Bucket Objects"):
        if not st.session_state.connected:
            st.warning("API Gateway offline. Establish status first.")
        else:
            with st.spinner("Downloading objects and running distributed PySpark ingestion..."):
                try:
                    payload = {"bucket": s3_bucket, "prefix": s3_prefix}
                    res = requests.post(f"{st.session_state.backend_url}/ingest/s3", json=payload, timeout=120)
                    if res.status_code == 200:
                        chunks = res.json().get("total_chunks")
                        st.success(f"ETL completed: Ingested {chunks} segments to Pinecone.")
                    else:
                        st.error(f"Sync failed: {res.json().get('detail')}")
                except Exception as e:
                    st.error(f"Gateway connection failure: {e}")

# AWS Management Console Tab Navigation (Clean, text-only styling)
tabs = st.tabs([
    "Query Sandbox", 
    "Chunk Segmentation", 
    "Retrieval Diagnostics", 
    "Usage Billing"
])

# ==========================================
# TAB 1: Query Sandbox
# ==========================================
with tabs[0]:
    col_main, col_side = st.columns([13, 6])
    
    with col_side:
        # Document uploading options container
        st.markdown("""
        <div class="aws-container">
            <div class="aws-container-title">Ingest Local Document</div>
        """, unsafe_allow_html=True)
        
        uploaded_file = st.file_uploader("Upload local PDF or TXT file", type=["pdf", "txt"], label_visibility="collapsed")
        if uploaded_file is not None:
            if st.button("Upload & Index Document"):
                if not st.session_state.connected:
                    st.warning("Gateway connection offline.")
                else:
                    with st.spinner("Parsing text and index loaders..."):
                        try:
                            files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                            res = requests.post(f"{st.session_state.backend_url}/upload", files=files, timeout=60)
                            if res.status_code == 200:
                                total_chunks = res.json().get("total_chunks")
                                st.success(f"File uploaded. Created {total_chunks} index vectors.")
                            else:
                                st.error(f"Processing error: {res.json().get('detail')}")
                        except Exception as e:
                            st.error(f"Network error during upload: {e}")
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Batch seeding container
        st.markdown("""
        <div class="aws-container">
            <div class="aws-container-title">Distributed Batch Seed</div>
            <p style="font-size: 0.8rem; color: #545b64; margin-top: 0; margin-bottom: 12px;">
                Triggers a local distributed PySpark job to clean, chunk, and index 1,000 synthetic log records.
            </p>
        """, unsafe_allow_html=True)
        if st.button("Run Batch Ingestion Seed"):
            if not st.session_state.connected:
                st.warning("Gateway connection offline.")
            else:
                with st.spinner("Executing PySpark ingestion job..."):
                    try:
                        res = requests.post(f"{st.session_state.backend_url}/ingest", timeout=120)
                        if res.status_code == 200:
                            st.success(f"PySpark job complete. Created {res.json().get('total_chunks')} segments.")
                        else:
                            st.error(res.json().get("detail"))
                    except Exception as e:
                        st.error(f"Execution error: {e}")
        st.markdown("</div>", unsafe_allow_html=True)

    with col_main:
        # Search panel container
        st.markdown("""
        <div class="aws-container">
            <div class="aws-container-title">Natural Language Queries</div>
        """, unsafe_allow_html=True)
        
        query = st.text_input(
            "Execute retrieval search queries against the document database:",
            placeholder="Type query to retrieve and synthesize..."
        )
        
        if query:
            if not st.session_state.connected:
                st.warning("Gateway offline. Configure connection in the sidebar.")
            else:
                with st.spinner("Retrieving database matches..."):
                    try:
                        payload = {"query": query, "top_k_hybrid": 30, "top_k_rerank": 5}
                        response = requests.post(f"{st.session_state.backend_url}/query", json=payload, timeout=20)
                        
                        if response.status_code == 200:
                            res_data = response.json()
                            
                            # Cache latest queries for Diagnostics
                            st.session_state.last_query = query
                            st.session_state.last_response = res_data
                            
                            st.session_state.results_list = [{
                                "query": query,
                                "answer": res_data["answer"],
                                "results": res_data["results"]
                            }]
                        else:
                            st.error("Retrieval gateway error.")
                    except Exception as e:
                        st.error(f"Network request failed: {e}")
                        
        # Display current query result memo block
        if st.session_state.results_list:
            active = st.session_state.results_list[0]
            
            st.markdown(f"""
            <div class="memo-block">
                <div class="memo-header">Synthesized Response Summary</div>
                <div>{active['answer']}</div>
            </div>
            """, unsafe_allow_html=True)
            
            # Displays retrieved sources in a clean, compact, non-crowded list
            st.markdown("#### Retrieved Database Sources")
            for idx, item in enumerate(active["results"]):
                # Truncate content preview to prevent visual clutter
                preview_text = item["chunk_text"][:240] + "..." if len(item["chunk_text"]) > 240 else item["chunk_text"]
                
                with st.expander(f"Source Document {idx+1} (Doc: {item['doc_id'][:12]}... • Segment: {item['chunk_index']})"):
                    st.markdown(f"""
                    <div style="font-size: 0.85rem; color: #16191f; line-height: 1.5; background: #fafafa; padding: 12px; border: 1px solid #eaeded; border-radius: 2px;">
                        "{item['chunk_text']}"
                    </div>
                    """, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

# ==========================================
# TAB 2: Chunk Segmentation
# ==========================================
with tabs[1]:
    st.markdown("""
    <div class="aws-container">
        <div class="aws-container-title">Interactive Segment Splitting</div>
        <p style="font-size: 0.8rem; color: #545b64; margin-top: 0; margin-bottom: 20px;">
            Configure characters and overlap sliders to visualize document parsing boundaries.
        </p>
    """, unsafe_allow_html=True)
    
    col_args, col_view = st.columns([1, 1])
    
    with col_args:
        text_input = st.text_area(
            "Reference Text Document Content",
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
            height=240
        )
        ch_size = st.slider("Target Segment Length (Chars)", 100, 800, 300, step=50)
        ch_overlap = st.slider("Segment Overlap Length (Chars)", 10, 200, 50, step=10)
        
    with col_view:
        from src.utils.chunker import RecursiveCharacterChunker
        chunker = RecursiveCharacterChunker(chunk_size=ch_size, chunk_overlap=ch_overlap)
        chunks = chunker.chunk_text(text_input)
        
        st.markdown(f"**Total Segments Generated**: `{len(chunks)}` blocks")
        
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
                <div class="chunk-overlap-box">
                    <span class="overlap-tag">Overlap:</span> {overlap_prefix}
                    <span style="color: #545b64;">{body_text}</span>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class="chunk-overlap-box" style="border-left: 3px solid #0073bb;">
                    <span style="color: #545b64;">{body_text}</span>
                </div>
                """, unsafe_allow_html=True)
                
    st.markdown("</div>", unsafe_allow_html=True)

# ==========================================
# TAB 3: Retrieval Diagnostics
# ==========================================
with tabs[2]:
    st.markdown("""
    <div class="aws-container">
        <div class="aws-container-title">Query Processing Diagnostics</div>
    """, unsafe_allow_html=True)
    
    if not st.session_state.last_response:
        st.info("Execute a search query in the Sandbox (Tab 1) to inspect diagnostics.")
    else:
        active_q = st.session_state.last_query
        res_payload = st.session_state.last_response
        
        st.markdown(f"**Selected Search Query**: *'{active_q}'*")
        
        # Diagnostics comparison data list
        comparisons = []
        for idx, item in enumerate(res_payload["results"]):
            comparisons.append({
                "Rank": idx + 1,
                "Document Name": item["doc_id"][:12] + "...",
                "Segment ID": item["chunk_index"],
                "Stage 1 DB Score": f"{item['score']:.4f}",
                "Stage 2 Rerank Score": f"{item['rerank_score']:.4f}",
                "Snippet Excerpt": item["chunk_text"][:95] + "..."
            })
        df_diag = pd.DataFrame(comparisons)
        
        st.dataframe(df_diag, use_container_width=True)
        
        st.markdown("### Stage 1 vs Stage 2 Rank Realignment")
        col_st1, col_st2 = st.columns(2)
        
        with col_st1:
            st.markdown("#### Stage 1: Database Hits (Sorted by RRF Score)")
            st1_ordered = sorted(res_payload["results"], key=lambda x: x["score"], reverse=True)
            for idx, item in enumerate(st1_ordered[:3]):
                st.markdown(f"""
                <div class="console-row">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 2px;">
                        <span style="font-weight: 600;">Match {idx+1} | Segment: {item['chunk_index']}</span>
                        <span class="badge-rrf">Score: {item['score']:.4f}</span>
                    </div>
                    <div style="color: #545b64;">{item['chunk_text'][:120]}...</div>
                </div>
                """, unsafe_allow_html=True)
                
        with col_st2:
            st.markdown("#### Stage 2: Cross-Encoder Rerank (Sorted by Final Score)")
            for idx, item in enumerate(res_payload["results"][:3]):
                st.markdown(f"""
                <div class="console-row">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 2px;">
                        <span style="font-weight: 600;">Rank {idx+1} | Segment: {item['chunk_index']}</span>
                        <span class="badge-rerank">Score: {item['rerank_score']:.4f}</span>
                    </div>
                    <div style="color: #16191f;">{item['chunk_text'][:120]}...</div>
                </div>
                """, unsafe_allow_html=True)
                
    st.markdown("</div>", unsafe_allow_html=True)

# ==========================================
# TAB 4: Usage Billing
# ==========================================
with tabs[3]:
    st.markdown("""
    <div class="aws-container">
        <div class="aws-container-title">Operational Billing Analytics</div>
    """, unsafe_allow_html=True)
    
    if not st.session_state.connected:
        st.warning("Gateway connection offline. Establish gateway status in the sidebar.")
    else:
        try:
            res_an = requests.get(f"{st.session_state.backend_url}/analytics", timeout=5)
            if res_an.status_code == 200:
                an_data = res_an.json()
                
                # Display metric tiles
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.markdown(f"""
                    <div class="aws-metric-tile">
                        <div class="aws-metric-label">Estimated Monthly Bill</div>
                        <div class="aws-metric-value aws-metric-value-cost">${an_data['total_cost']:.6f}</div>
                    </div>
                    """, unsafe_allow_html=True)
                with col2:
                    st.markdown(f"""
                    <div class="aws-metric-tile">
                        <div class="aws-metric-label">Billing Tokens Count</div>
                        <div class="aws-metric-value">{an_data['total_tokens']:,}</div>
                    </div>
                    """, unsafe_allow_html=True)
                with col3:
                    st.markdown(f"""
                    <div class="aws-metric-tile">
                        <div class="aws-metric-label">Queries Executed</div>
                        <div class="aws-metric-value">{an_data['total_queries']}</div>
                    </div>
                    """, unsafe_allow_html=True)
                with col4:
                    st.markdown(f"""
                    <div class="aws-metric-tile">
                        <div class="aws-metric-label">ETL Ingestion Pipelines</div>
                        <div class="aws-metric-value">{an_data['total_ingests']}</div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                st.markdown("### Billing Cost Allocation")
                breakdown = an_data["cost_breakdown"]
                
                df_chart = pd.DataFrame({
                    "Component": ["Embeddings (BGE)", "Reranker Model", "LLM Input Prompt", "LLM Text Generation", "Pinecone DB Writes"],
                    "Cost ($)": [
                        breakdown["embedding"],
                        breakdown["rerank"],
                        breakdown["llm_input"],
                        breakdown["llm_output"],
                        breakdown["db_write"]
                    ]
                })
                
                # Renders AWS styled bar chart
                chart = alt.Chart(df_chart).mark_bar(
                    size=24,
                    cornerRadiusTopLeft=1,
                    cornerRadiusTopRight=1
                ).encode(
                    x=alt.X("Component:N", sort=None, title="Service Layer Component"),
                    y=alt.Y("Cost ($):Q", title="Billing Cost (USD)"),
                    color=alt.value("#0073bb"),  # AWS Blue
                    tooltip=["Component", "Cost ($)"]
                ).properties(
                    height=280
                )
                
                st.altair_chart(chart, use_container_width=True)
                
                with st.expander("Show Detailed Model Rate Pricing Catalog"):
                    st.markdown("""
                    **Model Catalog Rates:**
                    * **BGE-small Embedding**: `$0.00002` / 1,000 tokens
                    * **Cross-Encoder Rerank**: `$0.00010` / 1,000 tokens
                    * **LLM Prompt Input**: `$0.00150` / 1,000 tokens
                    * **LLM Generation Output**: `$0.00200` / 1,000 tokens
                    * **Pinecone Serverless writes**: `$0.00100` / 1,000 vectors
                    """)
            else:
                st.error("Could not load billing details.")
        except Exception as e:
            st.error(f"Analytics connection error: {e}")
            
    st.markdown("</div>", unsafe_allow_html=True)
