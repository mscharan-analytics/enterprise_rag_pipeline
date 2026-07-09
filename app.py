import os
import sys
import time
import requests
import pandas as pd
import altair as alt
import streamlit as st

# Page Configuration
st.set_page_config(
    page_title="Enterprise Document Intelligence Portal",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Enterprise-Grade Styling (Clean, light-themed SaaS dashboard layout)
st.markdown("""
<style>
    /* Main Background & Typography */
    .stApp {
        background-color: #f8fafc;
        color: #0f172a;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }
    
    /* Global Headings */
    .main-title {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1e293b;
        margin-bottom: 0.1rem;
        border-bottom: 1px solid #e2e8f0;
        padding-bottom: 8px;
    }
    
    .subtitle {
        font-size: 0.95rem;
        color: #64748b;
        margin-bottom: 1.5rem;
    }
    
    /* Clean Enterprise Cards (Snowflake/AWS styled) */
    .dashboard-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 16px 20px;
        margin-bottom: 12px;
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.05);
    }
    
    .card-title {
        font-size: 0.75rem;
        text-transform: uppercase;
        color: #64748b;
        font-weight: 600;
        margin-bottom: 6px;
        letter-spacing: 0.5px;
    }
    
    .card-value {
        font-size: 1.5rem;
        font-weight: 700;
        color: #2563eb;
    }
    
    .card-value-cost {
        color: #0f766e;
    }

    /* Structured Response Box (Memo style) */
    .response-container {
        background: #ffffff;
        border: 1px solid #cbd5e1;
        border-left: 4px solid #2563eb;
        border-radius: 6px;
        padding: 18px;
        margin-top: 15px;
        margin-bottom: 20px;
        box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
    }
    
    .response-header {
        font-size: 0.85rem;
        font-weight: 600;
        color: #475569;
        text-transform: uppercase;
        border-bottom: 1px solid #e2e8f0;
        padding-bottom: 6px;
        margin-bottom: 12px;
    }

    /* Segmented Chunk List Box */
    .chunk-container {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 6px;
        padding: 12px 16px;
        margin-bottom: 8px;
    }
    
    .chunk-header {
        display: flex;
        justify-content: space-between;
        font-size: 0.8rem;
        font-weight: 600;
        color: #64748b;
        border-bottom: 1px dashed #e2e8f0;
        padding-bottom: 4px;
        margin-bottom: 6px;
    }
    
    .overlap-box {
        background: #f1f5f9;
        border-left: 4px solid #64748b;
        padding: 10px;
        border-radius: 4px;
        font-family: monospace;
        font-size: 0.85rem;
        line-height: 1.4;
        color: #334155;
    }
    
    .overlap-prefix {
        color: #2563eb;
        font-weight: bold;
        background: #dbeafe;
        padding: 1px 3px;
        border-radius: 2px;
        margin-right: 4px;
    }
    
    /* Diagnostics Tab Styles */
    .dia-row {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 6px;
        padding: 10px 14px;
        margin-bottom: 6px;
        font-size: 0.85rem;
    }
    
    .badge-rrf {
        background-color: #eff6ff;
        color: #1e40af;
        border: 1px solid #bfdbfe;
        padding: 1px 6px;
        border-radius: 4px;
        font-weight: 600;
    }
    
    .badge-rerank {
        background-color: #faf5ff;
        color: #6b21a8;
        border: 1px solid #e9d5ff;
        padding: 1px 6px;
        border-radius: 4px;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# Main Dashboard Title
st.markdown('<div class="main-title">Enterprise Document Intelligence Portal</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Secure Document Retrieval • PySpark ETL pipelines • AWS S3 Integration • Billing Cost Analytics</div>', unsafe_allow_html=True)

# Initialize Session States
if "backend_url" not in st.session_state:
    st.session_state.backend_url = "http://localhost:8000/api/v1"
if "connected" not in st.session_state:
    st.session_state.connected = False
if "last_query" not in st.session_state:
    st.session_state.last_query = None
if "last_response" not in st.session_state:
    st.session_state.last_response = None
if "search_history" not in st.session_state:
    st.session_state.search_history = []

# Sidebar Administration Panel
with st.sidebar:
    st.markdown("### ⚙️ System Connections")
    st.session_state.backend_url = st.text_input("API Base Endpoint", value=st.session_state.backend_url)
    
    if st.button("🔌 Verify API Gateway"):
        with st.spinner("Pinging API gateway..."):
            try:
                res = requests.get(f"{st.session_state.backend_url}/health", timeout=5)
                if res.status_code == 200 and res.json().get("status") == "healthy":
                    st.session_state.connected = True
                    st.success("Successfully authenticated with API Gateway.")
                else:
                    st.session_state.connected = False
                    st.error("API Gateway returned an unhealthy status.")
            except Exception as e:
                st.session_state.connected = False
                st.error(f"Cannot establish connection: {e}")
                
    st.markdown("---")
    st.markdown("### 🗄️ Cloud Lakehouse Loader")
    s3_bucket = st.text_input("AWS S3 Bucket", value="enterprise-rag-lakehouse")
    s3_prefix = st.text_input("S3 Ingest Prefix", value="documents/")
    
    if st.button("🚀 Synchronize S3 Lakehouse"):
        if not st.session_state.connected:
            st.warning("Establish connection to API Gateway first.")
        else:
            with st.spinner("Downloading from S3 and launching PySpark ingestion..."):
                try:
                    payload = {"bucket": s3_bucket, "prefix": s3_prefix}
                    res = requests.post(f"{st.session_state.backend_url}/ingest/s3", json=payload, timeout=120)
                    if res.status_code == 200:
                        chunks = res.json().get("total_chunks")
                        st.success(f"ETL Complete: Indexed {chunks} document segments to Pinecone.")
                    else:
                        st.error(f"ETL Ingestion failed: {res.json().get('detail')}")
                except Exception as e:
                    st.error(f"ETL Gateway error: {e}")

# Multi-Tab Layout for Professional Workspace
tabs = st.tabs([
    "📂 Natural Language Query Portal", 
    "📐 Segment & Chunk Visualizer", 
    "🔧 Retrieval Rerank Diagnostics", 
    "📈 Operational Cost Analytics"
])

# ==========================================
# TAB 1: Natural Language Query Portal
# ==========================================
with tabs[0]:
    col_search, col_upload = st.columns([13, 6])
    
    with col_upload:
        st.markdown("### Document Upload Interface")
        st.info("Directly upload text-based PDF or TXT files. The file will be segmented, embedded, and indexed immediately in Pinecone.")
        
        uploaded_file = st.file_uploader("Upload File (PDF / TXT)", type=["pdf", "txt"], label_visibility="collapsed")
        if uploaded_file is not None:
            if st.button("⚡ Process and Index File"):
                if not st.session_state.connected:
                    st.warning("Gateway connection required. Verify connection in the sidebar.")
                else:
                    with st.spinner("Processing uploaded document..."):
                        try:
                            files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                            res = requests.post(f"{st.session_state.backend_url}/upload", files=files, timeout=60)
                            if res.status_code == 200:
                                total_chunks = res.json().get("total_chunks")
                                st.success(f"Ingested document. Indexed {total_chunks} segments.")
                            else:
                                st.error(f"Upload failed: {res.json().get('detail')}")
                        except Exception as e:
                            st.error(f"Network upload error: {e}")
                            
        st.markdown("---")
        st.markdown("### PySpark Batch Seeding")
        st.markdown("Run the distributed Spark ingestion engine on local synthetic data (1,000 corporate records).")
        if st.button("⚡ Run Spark Batch Seeding"):
            if not st.session_state.connected:
                st.warning("Gateway connection required.")
            else:
                with st.spinner("Running distributed Spark pipeline..."):
                    try:
                        res = requests.post(f"{st.session_state.backend_url}/ingest", timeout=120)
                        if res.status_code == 200:
                            st.success(f"Spark job complete. Ingested {res.json().get('total_chunks')} segments.")
                        else:
                            st.error(res.json().get("detail"))
                    except Exception as e:
                        st.error(f"ETL pipeline failure: {e}")

    with col_search:
        st.markdown("### Document Search & Synthesis Portal")
        
        # Search Box
        query = st.text_input(
            "Enter your corporate query (e.g. travel reimbursement, medical symptoms, incident reports):",
            placeholder="Search query..."
        )
        
        if query:
            if not st.session_state.connected:
                st.warning("Please establish API Gateway connection in the sidebar.")
            else:
                with st.spinner("Executing retrieval and synthesis..."):
                    try:
                        payload = {"query": query, "top_k_hybrid": 30, "top_k_rerank": 5}
                        response = requests.post(f"{st.session_state.backend_url}/query", json=payload, timeout=20)
                        
                        if response.status_code == 200:
                            res_data = response.json()
                            
                            # Cache latest lookup
                            st.session_state.last_query = query
                            st.session_state.last_response = res_data
                            
                            # Add query history record
                            st.session_state.search_history.insert(0, {
                                "query": query,
                                "answer": res_data["answer"],
                                "results": res_data["results"]
                            })
                        else:
                            st.error("Error executing query against REST endpoint.")
                    except Exception as e:
                        st.error(f"Network query error: {e}")
                        
        # Display Search Output (as a clean report memo rather than a chatbot conversation)
        if st.session_state.search_history:
            latest = st.session_state.search_history[0]
            
            st.markdown(f"""
            <div class="response-container">
                <div class="response-header">Document Intelligence Report - Query: "{latest['query']}"</div>
                <div>{latest['answer']}</div>
            </div>
            """, unsafe_allow_html=True)
            
            # Display matching documents as a structured tabular summary
            st.markdown("### Matched Reference Segments")
            for idx, item in enumerate(latest["results"]):
                st.markdown(f"""
                <div class="chunk-container">
                    <div class="chunk-header">
                        <span>Segment {idx+1} | Source Document ID: <code>{item['doc_id']}</code></span>
                        <span>Offset Index: {item['chunk_index']}</span>
                    </div>
                    <div style="font-size: 0.9rem; line-height: 1.4; color: #334155; margin-top: 4px;">
                        "{item['chunk_text']}"
                    </div>
                </div>
                """, unsafe_allow_html=True)

# ==========================================
# TAB 2: Segment & Chunk Visualizer
# ==========================================
with tabs[1]:
    st.subheader("📐 Recursive Segmenter & Chunking Visualizer")
    st.markdown("Review how text boundaries are parsed recursively, and how overlapping character slices are prepended between adjacent segments.")
    
    col_inp, col_vis = st.columns([9, 10])
    
    with col_inp:
        sample_text = st.text_area(
            "Reference Text Block",
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
            height=260
        )
        chunk_size = st.slider("Target Segment Size (Characters)", 100, 800, 300, step=50)
        chunk_overlap = st.slider("Boundary Overlap Allowance (Characters)", 10, 200, 50, step=10)
        
    with col_vis:
        from src.utils.chunker import RecursiveCharacterChunker
        chunker = RecursiveCharacterChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        chunks = chunker.chunk_text(sample_text)
        
        st.markdown(f"**Segments Formed**: `{len(chunks)}` blocks")
        
        for idx, chunk in enumerate(chunks):
            overlap_prefix = ""
            main_body = chunk
            
            if idx > 0 and chunk_overlap > 0:
                prev = chunks[idx - 1]
                expected_overlap = prev[-chunk_overlap:]
                
                if chunk.startswith(expected_overlap):
                    overlap_prefix = expected_overlap
                    main_body = chunk[len(expected_overlap):]
                else:
                    overlap_prefix = chunk[:chunk_overlap]
                    main_body = chunk[chunk_overlap:]
            
            st.markdown(f"**Segment {idx+1}** (Size: `{len(chunk)}` characters):")
            if overlap_prefix:
                st.markdown(f"""
                <div class="overlap-box">
                    <span class="overlap-prefix">Overlap:</span>{overlap_prefix}
                    <span>{main_body}</span>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class="overlap-box" style="border-left-color: #2563eb; background: #f8fafc;">
                    <span>{main_body}</span>
                </div>
                """, unsafe_allow_html=True)

# ==========================================
# TAB 3: Retrieval Rerank Diagnostics
# ==========================================
with tabs[2]:
    st.subheader("🔧 Two-Stage Retrieval Diagnostics")
    st.markdown("Analyze how the Stage 1 vector search candidates (Pinecone dotproduct) were reordered by the Stage 2 Cross-Encoder model.")
    
    if not st.session_state.last_response:
        st.info("Submit a search query in Tab 1 to load diagnostics.")
    else:
        last_q = st.session_state.last_query
        res_data = st.session_state.last_response
        
        st.markdown(f"**Active Query**: *'{last_q}'*")
        
        # Build comparison table
        records = []
        for idx, item in enumerate(res_data["results"]):
            records.append({
                "Final Rank": idx + 1,
                "Document Reference": item["doc_id"][:16] + "...",
                "Segment ID": item["chunk_index"],
                "Stage 1 DB Score": f"{item['score']:.4f}",
                "Stage 2 Rerank Score": f"{item['rerank_score']:.4f}",
                "Content Snippet": item["chunk_text"][:90] + "..."
            })
        df_diag = pd.DataFrame(records)
        
        st.dataframe(df_diag, use_container_width=True)
        
        st.markdown("### Top Candidate Alignment Report")
        col_s1, col_s2 = st.columns(2)
        
        with col_s1:
            st.markdown("#### Stage 1: Raw Pinecone Hits (Sorted by DB Score)")
            s1_sorted = sorted(res_data["results"], key=lambda x: x["score"], reverse=True)
            for idx, item in enumerate(s1_sorted[:3]):
                st.markdown(f"""
                <div class="dia-row" style="border-left: 4px solid #2563eb;">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 4px; font-weight: 600;">
                        <span>Lookup Match {idx+1}</span>
                        <span class="badge-rrf">DB Score: {item['score']:.4f}</span>
                    </div>
                    <div style="color: #64748b; font-size: 0.8rem;">{item['chunk_text'][:120]}...</div>
                </div>
                """, unsafe_allow_html=True)
                
        with col_s2:
            st.markdown("#### Stage 2: Final Re-ranked Output (Sorted by Relevance)")
            for idx, item in enumerate(res_data["results"][:3]):
                st.markdown(f"""
                <div class="dia-row" style="border-left: 4px solid #7c3aed;">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 4px; font-weight: 600;">
                        <span>Rerank Rank {idx+1}</span>
                        <span class="badge-rerank">Rerank Score: {item['rerank_score']:.4f}</span>
                    </div>
                    <div style="color: #334155; font-size: 0.8rem;">{item['chunk_text'][:120]}...</div>
                </div>
                """, unsafe_allow_html=True)

# ==========================================
# TAB 4: Operational Cost Analytics
# ==========================================
with tabs[3]:
    st.subheader("📈 System Cost & Token Consumption Report")
    st.markdown("Operational cost tracking dashboard calculating token billing rates based on pricing schemas.")
    
    if not st.session_state.connected:
        st.warning("Verify connection to API Gateway in the sidebar to load billing data.")
    else:
        try:
            res_an = requests.get(f"{st.session_state.backend_url}/analytics", timeout=5)
            if res_an.status_code == 200:
                an_data = res_an.json()
                
                # Display metric cards
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.markdown(f"""
                    <div class="dashboard-card">
                        <div class="card-title">Accumulated Billing</div>
                        <div class="card-value card-value-cost">${an_data['total_cost']:.6f}</div>
                    </div>
                    """, unsafe_allow_html=True)
                with col2:
                    st.markdown(f"""
                    <div class="dashboard-card">
                        <div class="card-title">Cumulative Tokens</div>
                        <div class="card-value">{an_data['total_tokens']:,}</div>
                    </div>
                    """, unsafe_allow_html=True)
                with col3:
                    st.markdown(f"""
                    <div class="dashboard-card">
                        <div class="card-title">Total Queries Executed</div>
                        <div class="card-value" style="color: #1e293b;">{an_data['total_queries']}</div>
                    </div>
                    """, unsafe_allow_html=True)
                with col4:
                    st.markdown(f"""
                    <div class="dashboard-card">
                        <div class="card-title">Ingestion Pipelines Run</div>
                        <div class="card-value" style="color: #0f766e;">{an_data['total_ingests']}</div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                st.markdown("### Operational Cost Breakdown")
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
                
                # Renders corporate-styled Altair chart
                chart = alt.Chart(df_chart).mark_bar(
                    size=30,
                    cornerRadiusTopLeft=2,
                    cornerRadiusTopRight=2
                ).encode(
                    x=alt.X("Phase:N", sort=None, title="ETL / Query Phase"),
                    y=alt.Y("Cost ($):Q", title="Cost in USD ($)"),
                    color=alt.value("#2563eb"),  # Corporate Standard Blue
                    tooltip=["Phase", "Cost ($)"]
                ).properties(
                    height=320
                )
                
                st.altair_chart(chart, use_container_width=True)
                
                with st.expander("Pricing Catalog Rates Table"):
                    st.markdown("""
                    Standardized model rates utilized for API cost calculations:
                    - **BGE-small Embedding**: `$0.00002` / 1K tokens
                    - **Cross-Encoder Rerank**: `$0.00010` / 1K tokens
                    - **LLM Input Context**: `$0.00150` / 1K tokens
                    - **LLM Output Generation**: `$0.00200` / 1K tokens
                    - **Pinecone Serverless writes**: `$0.00100` / 1K vectors
                    """)
            else:
                st.error("Analytics endpoint returned an invalid response.")
        except Exception as e:
            st.error(f"Error fetching analytics data: {e}")
