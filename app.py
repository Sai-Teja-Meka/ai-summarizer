import streamlit as st
import openai # The new client is imported from the top-level 'openai' module

# 1. Initialize the Client
# The API key is automatically picked up from the environment variable "OPENAI_API_KEY"
# or you can pass it explicitly: client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# ===== PAGE CONFIG & CSS =====
st.set_page_config(
    page_title="AI Summarizer Pro",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Professional CSS (Integrated from app_pro_advanced.py)
st.markdown("""
<style>
    /* Main Layout Background */
    .main { background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%); }
    
    /* Headings */
    h1, h2, h3 { color: #2c3e50 !important; font-family: 'Helvetica Neue', sans-serif; }
    
    /* Button Styling */
    .stButton > button {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        color: white;
        font-weight: 600;
        border: none;
        padding: 10px 24px;
        border-radius: 8px;
        transition: all 0.3s ease;
        width: 100%;
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.5);
    }

    /* Result Cards */
    .result-container {
        background-color: white;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        margin-bottom: 15px;
        border-left: 5px solid #667eea;
    }

    /* Text Area Styling */
    .stTextArea textarea {
        background-color: #f8f9fa;
        border: 1px solid #e9ecef;
        border-radius: 8px;
        font-size: 16px;
        line-height: 1.6;
    }
</style>
""", unsafe_allow_html=True)

# ===== SIDEBAR: ANALYTICS =====
with st.sidebar:
    st.markdown("### 📊 Dashboard")
    metrics = get_metrics_summary()
    
    if metrics and metrics["total_summaries"] > 0:
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total", metrics["total_summaries"])
            st.metric("Time", f"{metrics['avg_processing_time']}s")
        with col2:
            st.metric("Cost", f"${metrics['total_cost_usd']:.3f}")
            st.metric("Ratio", f"{metrics['avg_compression_ratio']:.0f}%")
        
        st.divider()
        st.caption("Recent Activity")
        recent = get_recent_summaries(limit=3)
        for row in recent:
            st.markdown(f"**{row['timestamp'].split()[1]}**: {row['input_length']} chars")
            
    else:
        st.info("Start summarizing to generate analytics.")

# ===== MAIN APP STRUCTURE =====
st.title("✨ AI Content Summarizer")
st.markdown("Generate, compare, and analyze summaries with professional precision.")

# Tabs for Main Navigation
main_tab1, main_tab2, main_tab3 = st.tabs(["⚡ Summarize & Compare", "📈 Deep Analytics", "📚 Evaluation History"])

# =================================================================
# TAB 1: SUMMARIZE (Refactored for Cleanliness)
# =================================================================
with main_tab1:
    
    # --- SECTION 1: INPUT & CONFIGURATION ---
    # Using columns to create a "Dashboard" feel for inputs
    col_input, col_settings = st.columns([3, 2], gap="large")
    
    with col_input:
        st.subheader("1. Input Content")
        input_type = st.radio("Source:", ["📝 Paste Text", "📁 Upload File"], horizontal=True, label_visibility="collapsed")
        
        user_input = ""
        input_source = "text"
        file_type = "txt"

        if "Paste" in input_type:
            user_input = st.text_area("Content:", height=250, placeholder="Paste your text here...", label_visibility="collapsed")
        else:
            uploaded_file = st.file_uploader("Upload", type=["pdf", "docx", "pptx", "txt"], label_visibility="collapsed")
            if uploaded_file:
                user_input = extract_text_from_file(uploaded_file)
                input_source = "file"
                file_type = uploaded_file.name.split(".")[-1]
                if user_input:
                    st.success(f"Loaded: {uploaded_file.name}")

    with col_settings:
        st.subheader("2. Configuration")
        with st.container(border=True):
            s_tone = st.select_slider("Tone", options=["Neutral", "Academic", "Casual"], value="Neutral")
            s_len = st.select_slider("Length", options=["Short", "Medium", "Long"], value="Medium")
            
            st.divider()
            
            st.markdown("**Prompt Strategy:**")
            all_versions = get_all_versions()
            # Default to Basic and Chain of Thought for comparison
            selected_prompts = st.multiselect(
                "Select strategies to compare:",
                options=list(all_versions.keys()),
                default=["v1_basic", "v3_chain_of_thought"],
                format_func=lambda x: get_version_name(x)
            )
            
            has_ref = st.toggle("Add Reference Summary (for ROUGE scoring)")
            ref_summary = ""
            if has_ref:
                ref_summary = st.text_area("Reference:", height=100, label_visibility="collapsed")

    # --- SECTION 2: ACTION ---
    st.divider()
    run_btn = st.button("🚀 Generate & Compare Results", type="primary")

    # --- SECTION 3: RESULTS DISPLAY ---
    if run_btn and user_input and client:
        
        results_cache = {}
        
        # Modern Status Indicator
        with st.status("Processing Summaries...", expanded=True) as status:
            
            for v_key in selected_prompts:
                v_name = get_version_name(v_key)
                status.write(f"Generating **{v_name}**...")
                
                # Logic from app.py
                start = time.time()
                prompt_template = get_prompt_template(v_key)
                full_prompt = f"{prompt_template.format(text=user_input)}\nTone: {s_tone}\nLength: {s_len}"
                
                try:
                    response = client.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=[{"role": "user", "content": full_prompt}],
                        temperature=0.5
                    )
                    summary_text = response.choices[0].message.content
                    duration = time.time() - start
                    
                    # Calculate Metrics
                    basic = calculate_basic_metrics(user_input, summary_text)
                    readability = calculate_readability_score(summary_text)
                    rouge = {"rougeL": None}
                    if ref_summary:
                        rouge = calculate_rouge_scores(ref_summary, summary_text)
                    
                    # Log Metrics
                    log_summary(len(user_input), len(summary_text), basic['compression_ratio'], s_tone, s_len, input_source, file_type, duration)
                    if ref_summary:
                        log_prompt_evaluation(v_key, user_input, summary_text, ref_summary, rouge, basic, readability, duration)

                    results_cache[v_key] = {
                        "name": v_name,
                        "text": summary_text,
                        "time": duration,
                        "metrics": basic,
                        "readability": readability,
                        "rouge": rouge
                    }
                    
                except Exception as e:
                    st.error(f"Error in {v_name}: {e}")
            
            status.update(label="✅ Summarization Complete!", state="complete", expanded=False)

        # --- REFACTORED RESULT VIEW: Tabs instead of long scroll ---
        st.subheader("📝 Results Analysis")
        
        if results_cache:
            # Create dynamic tabs for each result version
            tabs = st.tabs([data["name"] for data in results_cache.values()])
            
            for tab, (key, data) in zip(tabs, results_cache.items()):
                with tab:
                    # 1. THE SUMMARY (Hero Content)
                    st.markdown(f"<div class='result-container'><h3>📄 {data['name']}</h3></div>", unsafe_allow_html=True)
                    st.text_area("Generated Summary", value=data['text'], height=300, label_visibility="collapsed")
                    
                    # 2. THE STATISTICS (Clean Row)
                    st.markdown("#### 📊 Performance Metrics")
                    m_col1, m_col2, m_col3, m_col4 = st.columns(4)
                    
                    with m_col1:
                        st.metric("Processing Time", f"{data['time']:.2f}s")
                    with m_col2:
                        st.metric("Compression", f"{data['metrics']['compression_ratio']}%")
                    with m_col3:
                        st.metric("Readability Score", f"{data['readability']['readability_score']}/100")
                    with m_col4:
                        if data['rouge'].get('rougeL'):
                            st.metric("ROUGE-L Accuracy", f"{data['rouge']['rougeL']:.3f}")
                        else:
                            st.metric("ROUGE-L", "N/A", help="Provide reference summary to calculate")
                    
                    # 3. DETAILS (Collapsed)
                    with st.expander("🔍 View Technical Details"):
                        st.json({
                            "Word Count": len(data['text'].split()),
                            "Character Count": len(data['text']),
                            "Avg Sentence Length": data['readability']['avg_sentence_length'],
                            "Full ROUGE Scores": data['rouge']
                        })

# =================================================================
# TAB 2 & 3: ANALYTICS (Preserved features)
# =================================================================
with main_tab2:
    st.header("📈 Application Analytics")
    metrics_data = get_metrics_summary()
    
    if metrics_data and metrics_data["rows"]:
        # Charts Area
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Tone Distribution")
            st.bar_chart(metrics_data["tone_distribution"])
        with c2:
            st.subheader("Compression Trends")
            df = pd.DataFrame(metrics_data["rows"])
            if not df.empty:
                st.line_chart(df["compression_ratio"].astype(float))
        
        st.subheader("Raw Data Logs")
        st.dataframe(metrics_data["rows"], use_container_width=True)
    else:
        st.info("No data available yet.")

with main_tab3:
    st.header("🧪 A/B Testing History")
    eval_data = get_evaluation_summary()
    
    if eval_data:
        st.subheader("Prompt Performance Comparison")
        
        # Clean Table for Version Comparison
        comp_data = []
        for v_key, stats in eval_data["version_stats"].items():
            comp_data.append({
                "Version": get_version_name(v_key),
                "Tests Run": stats["count"],
                "Avg ROUGE-L": f"{stats['avg_rougeL']:.3f}",
                "Avg Time": f"{stats['avg_time']:.2f}s"
            })
        st.dataframe(comp_data, use_container_width=True)
    else:
        st.info("Run comparisons with a reference summary to populate this tab.")
