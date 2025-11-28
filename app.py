import streamlit as st
import openai
import time
import pandas as pd

# Import local modules (Ensure these files are in your GitHub repo!)
from file_handler import extract_text_from_file
from metrics import log_summary, get_metrics_summary, get_recent_summaries
from prompt_versions import get_all_versions, get_prompt_template, get_version_name
from evaluation import (
    calculate_rouge_scores, calculate_basic_metrics, 
    calculate_readability_score, log_prompt_evaluation,
    get_evaluation_summary
)

# Initialize OpenAI Client (Crucial change for Streamlit Cloud deployment)
client = None
try:
    # 1. Prioritize Streamlit Secrets
    if "OPENAI_API_KEY" in st.secrets:
        client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
        # If running locally, you might still want dotenv:
    elif os.getenv("OPENAI_API_KEY"):
        client = openai.OpenAI() # Automatically uses OPENAI_API_KEY environment variable
    else:
        st.error("OpenAI API Key not found. Please set 'OPENAI_API_KEY' in Streamlit Secrets or a local .env file.")
        
except Exception as e:
    st.error(f"Failed to initialize OpenAI client: {e}")
    client = None

# ===== PROFESSIONAL STYLING =====
st.set_page_config(
    page_title="AI Content Summarizer: The A/B Tester",
    page_icon="📝",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for professional look
st.markdown("""
<style>
    /* Main background */
    .main {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
    }
    
    /* Sidebar background */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #667eea 0%, #764ba2 100%);
    }
    
    /* Sidebar text color */
    [data-testid="stSidebar"] > div:first-child {
        color: white !important;
    }
    
    [data-testid="stSidebar"] h1, 
    [data-testid="stSidebar"] h2, 
    [data-testid="stSidebar"] h3 {
        color: white !important;
    }
    
    [data-testid="stSidebar"] .stMetricValue {
        color: #FFD700 !important;
        font-size: 24px !important;
    }
    
    [data-testid="stSidebar"] .stMetricLabel {
        color: #E8E8FF !important;
    }
    
    /* Button styling */
    .stButton > button {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        color: white;
        font-weight: 600;
        padding: 12px 24px;
        border: none;
        border-radius: 8px;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(102, 126, 234, 0.6);
    }
    
    /* Cards/Expanders/Tabs */
    .streamlit-expanderHeader {
        background: linear-gradient(90deg, rgba(102, 126, 234, 0.1) 0%, rgba(118, 75, 162, 0.1) 100%);
        border-left: 4px solid #667eea;
    }
    
    /* Input fields */
    .stTextArea textarea {
        border: 2px solid #667eea !important;
        border-radius: 8px !important;
    }
    
    /* Titles and headers */
    h1 {
        color: #667eea !important;
        font-weight: 700 !important;
        text-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    }
    
    h2 {
        color: #764ba2 !important;
        font-weight: 600 !important;
    }
    
    h3 {
        color: #667eea !important;
    }
    
    /* Tooltip styling */
    .tooltip-text {
        font-size: 12px;
        color: #666;
        font-style: italic;
        background: #f0f4f8;
        padding: 8px 12px;
        border-left: 3px solid #667eea;
        border-radius: 4px;
        margin: 8px 0;
    }
    
    /* Result Container for new tab-based view */
    .result-container {
        background-color: white;
        padding: 15px 20px;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        margin-bottom: 15px;
        border-left: 5px solid #764ba2;
    }
</style>
""", unsafe_allow_html=True)


# ===== HELPER FUNCTIONS FOR USER-FRIENDLY EXPLANATIONS (Updated with Technical Terms) =====

def show_info_box(title, explanation):
    """Show a friendly info box with explanation"""
    st.markdown(f"""
    <div class="tooltip-text">
        <b>{title}</b><br>
        {explanation}
    </div>
    """, unsafe_allow_html=True)


def explain_prompt_version(version_key, all_versions):
    """Get user-friendly explanation for each prompt version, including technical terms"""
    
    explanations = {
        "v1_basic": {
            "name": "📝 Basic (v1_basic)",
            "simple": "Just gives the AI a simple command to summarize. **Good for fast, simple needs.**",
            "analogy": "Like saying: 'Please summarize this for me'",
            "pros": "✓ Fast and simple",
            "cons": "✗ May miss important details"
        },
        "v2_role_based": {
            "name": "👔 Expert Role (v2_role_based)",
            "simple": "Tells the AI to act like an expert summarizer. **This establishes a persona/role.**",
            "analogy": "Like hiring a professional editor to summarize",
            "pros": "✓ Better quality, more organized",
            "cons": "✗ Slightly slower"
        },
        "v3_chain_of_thought": {
            "name": "🧠 Chain-of-Thought (v3_chain_of_thought)",
            "simple": "Makes the AI think through the content step by step before generating. **Increases reasoning quality.**",
            "analogy": "Like asking someone to explain their thinking process",
            "pros": "✓ Very thorough and detailed",
            "cons": "✗ Takes longer, produces longer summaries"
        },
        "v4_structured": {
            "name": "📋 Structured (v4_structured)",
            "simple": "Tells the AI to organize the summary in a specific format (e.g., bullet points). **Focuses on output format control.**",
            "analogy": "Like asking for bullet points instead of paragraphs",
            "pros": "✓ Very organized and easy to read",
            "cons": "✗ Less natural-sounding"
        },
        "v5_context_aware": {
            "name": "💡 Few-Shot/Context-Aware (v5_context_aware)",
            "simple": "Shows the AI examples of what a good summary looks like to 'learn' from. **Improves output based on samples.**",
            "analogy": "Like showing samples before asking for the job",
            "pros": "✓ Learns from examples, higher quality",
            "cons": "✗ Needs more information"
        }
    }
    
    return explanations.get(version_key, {})


def explain_quality_metric(metric_name):
    """Simple explanations for quality metrics"""
    
    explanations = {
        "readability": "How easy it is to read and understand the summary. Higher = easier to read.",
        "compression": "How much shorter the summary is compared to the original. 20% = summary is 1/5 the size.",
        "quality": "How well the summary captures the main ideas. Higher = better quality.",
        "time": "How long it took the AI to create the summary. Faster is better!"
    }
    
    return explanations.get(metric_name, "")


# ===== SIDEBAR: Professional Analytics Dashboard (Simplified) =====
with st.sidebar:
    st.markdown("""
    <div style="text-align: center; padding: 20px 0;">
        <h1 style="color: white; font-size: 28px; margin: 0;">📊 Your Dashboard</h1>
        <p style="color: #E8E8FF; margin-top: 5px;">Track your summaries</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.divider()
    
    metrics = get_metrics_summary()
    
    if metrics and metrics["total_summaries"] > 0:
        # Key metrics with user-friendly labels
        col1, col2 = st.columns(2)
        with col1:
            st.metric("📝 Total Summaries", metrics['total_summaries'])
            st.metric("⏱️ Avg Time (s)", f"{metrics['avg_processing_time']}")
        
        with col2:
            st.metric("💰 Total Cost (USD)", f"${metrics['total_cost_usd']:.3f}")
            st.metric("📉 Avg Compression", f"{metrics['avg_compression_ratio']}%")
        
        st.divider()
        
        # Tone preferences
        st.subheader("🎨 Tone Distribution")
        if "tone_distribution" in metrics and isinstance(metrics["tone_distribution"], dict):
            for tone, count in metrics["tone_distribution"].items():
                st.write(f"**{tone}:** {count} times")
        
        # Length preferences
        st.subheader("📏 Length Preferences")
        if "length_distribution" in metrics and isinstance(metrics["length_distribution"], dict):
            for length, count in metrics["length_distribution"].items():
                st.write(f"**{length}:** {count} times")
        
        st.divider()
        
        # Recent summaries
        st.subheader("🕐 Recent Activity")
        recent = get_recent_summaries(limit=5)
        for idx, row in enumerate(recent, 1):
            st.caption(f"**{idx}.** {row['timestamp'].split()[1]}") # Use time for brevity
            st.caption(f"    Reduced {row['input_length']} chars | Paid ${row['api_cost_estimate']}")
            
        st.divider()
        
    else:
        st.info("👋 **Welcome!** Start summarizing to see your stats here.")


# ===== MAIN CONTENT (Using Tabs for Organization) =====
st.markdown("""
<div style="text-align: center; padding: 30px 0; margin-bottom: 30px;">
    <h1 style="font-size: 42px; margin: 0; background: linear-gradient(90deg, #667eea, #764ba2); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;">
        ✨ Smart Summary Maker
    </h1>
    <p style="font-size: 18px; color: #666; margin-top: 10px;">
        Generate, compare, and analyze summaries with professional precision.
    </p>
</div>
""", unsafe_allow_html=True)

st.divider()

# Main Tabs for the app
main_tab1, main_tab2, main_tab3 = st.tabs(["⚡ Summarize & Compare", "📈 Full Analytics", "📚 A/B Testing History"])


# =================================================================
# TAB 1: SUMMARIZE & COMPARE
# =================================================================
with main_tab1:
    
    # --- SECTION 1: INPUT ---
    st.markdown("### Step 1: 📥 What Do You Want to Summarize?")

    input_method = st.radio(
        "Source:",
        ("📝 Paste Text Here", "📁 Upload a File"),
        horizontal=True,
        label_visibility="collapsed"
    )

    user_input = ""
    input_source = "text"
    file_type = None

    if "Paste" in input_method:
        user_input = st.text_area(
            label="Your content here:",
            placeholder="Copy and paste any text: articles, essays, documents, emails, etc.",
            height=200,
            label_visibility="collapsed"
        )
        input_source = "text"

    else:  # Upload File
        st.write("**You can upload:** 📄 Word Documents · 📕 PDF Files · 🎯 PowerPoint · 📋 Text Files")
        
        uploaded_file = st.file_uploader(
            label="Pick your file",
            type=["pdf", "docx", "pptx", "txt"],
            accept_multiple_files=False,
            label_visibility="collapsed"
        )
        
        if uploaded_file is not None:
            file_type = uploaded_file.name.split(".")[-1].lower()
            user_input = extract_text_from_file(uploaded_file)
            input_source = "file"
            
            if user_input:
                st.success(f"✅ **Got it!** Loaded {uploaded_file.name} ({len(user_input):,} characters)")
            else:
                st.error("❌ Couldn't read that file. Try a different one?")
                user_input = ""


    # ===== SECTION 2: OPTIONS & PROMPT TESTING =====
    if user_input:
        st.divider()
        st.markdown("### Step 2: 🎨 Set Style & Strategies")
        
        col1, col2, col3 = st.columns([1, 1, 2])
        
        # --- Style (Tone/Length) ---
        with col1:
            summary_tone_options = ["Neutral 😐", "Academic 🎓", "Casual 😊"]
            summary_tone = st.selectbox(
                "Pick a **Tone**:",
                summary_tone_options,
                index=0,
                format_func=lambda x: x.split()[0]
            ).split()[0]
            st.caption(f"→ {summary_tone} tone")
        
        with col2:
            summary_length_options = ["Short ⚡", "Medium ⭐", "Long 📖"]
            summary_length = st.selectbox(
                "Pick a **Length**:",
                summary_length_options,
                index=1,
                format_func=lambda x: x.split()[0]
            ).split()[0]
            st.caption(f"→ {summary_length} length")
        
        # --- Prompt Strategies ---
        with col3:
            all_versions = get_all_versions()
            version_keys = list(all_versions.keys())
            
            # Display version descriptions in a friendly way with technical terms
            st.markdown("**🧪 Prompt Versions (Summary Methods):**")
            
            selected_versions = st.multiselect(
                "Which methods should we compare?",
                version_keys,
                default=["v1_basic", "v3_chain_of_thought"], # Default to a good comparison
                format_func=lambda x: explain_prompt_version(x, all_versions).get("name", x)
            )
            
            if selected_versions:
                with st.expander("👁️ See Strategy Details"):
                    for version_key in selected_versions:
                        info = explain_prompt_version(version_key, all_versions)
                        st.write(f"**{info.get('name')}** → {info.get('simple')}")
                        st.caption(f"💡 Analogy: {info.get('analogy')}")

        
        # ===== SECTION 3: REFERENCE SUMMARY (Optional) =====
        st.divider()
        st.markdown("### Optional: Add a Reference Summary")
        
        has_reference = st.toggle(
            "✓ **Enable ROUGE Scoring** (Compare against a known good summary)",
            value=False
        )
        
        reference_summary = None
        if has_reference:
            reference_summary = st.text_area(
                "Paste your example summary here:",
                placeholder="Paste a summary you think is good...",
                height=100
            )
            
            show_info_box(
                "📊 Why ROUGE?",
                "We use **ROUGE** (Recall-Oriented Understudy for Gisting Evaluation) to score how much overlap there is between the generated summary and your **Reference Summary**."
            )
        
        # ===== ACTION BUTTON =====
        st.divider()
        
        if selected_versions:
            col_b1, col_b2, col_b3 = st.columns([1, 2, 1])
            with col_b2:
                run_btn = st.button(
                    "🚀 Generate & Compare Results",
                    type="primary",
                    use_container_width=True
                )
            
            # ===== SECTION 4: CONFLICT CHECK & RESULTS DISPLAY =====
            if run_btn and client:
                st.divider()
                st.markdown("### 📊 Your A/B Test Results")
                
                results_cache = {}
                
                # --- NEW: CONFLICT DETECTION LOGIC ---
                high_conflict_keys = ["v2_role_based", "v3_chain_of_thought", "v5_context_aware"]
                conflict_tone = "Casual"
                conflict_length = "Short"
                
                conflict_detected = False
                conflict_messages = []
                
                for v_key in selected_versions:
                    v_name = explain_prompt_version(v_key, all_versions).get("name", v_key)
                    
                    if v_key in high_conflict_keys:
                        if summary_tone == conflict_tone:
                            conflict_messages.append(f"❌ **{v_name}** is a complex reasoning strategy that fundamentally conflicts with the highly simplified **{conflict_tone}** tone instruction.")
                            conflict_detected = True
                        if summary_length == conflict_length:
                            conflict_messages.append(f"❌ **{v_name}** requires significant reasoning/detail that may be impossible to fit into the **{conflict_length}** length restriction.")
                            conflict_detected = True

                if conflict_detected:
                    st.error("⚠️ **CONFLICT DETECTED** ⚠️")
                    for msg in set(conflict_messages): # Display unique messages
                        st.warning(msg)
                    st.error('This particular tone and length can’t guarantee compliance with this prompt version. Proceeding anyway, but expect sub-optimal results.')
                    st.divider()
                # --- END CONFLICT DETECTION LOGIC ---

                
                # --- NEW: ROBUST CRITICAL INSTRUCTION GENERATION ---
                length_map = {
                    "Short": "The summary length must be extremely concise and minimal. **Do not exceed 3 sentences or 60 words.**",
                    "Medium": "The summary length should be balanced, covering the main points in moderate detail. Aim for 4 to 6 sentences.",
                    "Long": "The summary must be detailed and comprehensive, covering all key aspects. Aim for 7 to 10 sentences."
                }
                
                tone_map = {
                    "Casual": "The writing style MUST be friendly, informal, and conversational. **Use simple, common vocabulary and sentences no longer than 15 words** (8th-grade reading level).",
                    "Neutral": "The writing style must be objective, clear, and professional. **To ensure high readability, the Average Sentence Length must not exceed 18 words.** Maintain a formal yet accessible tone (10th-grade reading level).",
                    "Academic": "The writing style MUST be formal, precise, and sophisticated. Use advanced terminology and complex sentence structures (college-level reading or higher)."
                }
                
                critical_instruction = f"\n\nCRITICAL STYLE INSTRUCTION:\n1. TONE: {tone_map.get(summary_tone, '')}\n2. LENGTH: {length_map.get(summary_length, '')}\n"
                # --- END ROBUST CRITICAL INSTRUCTION GENERATION ---
                
                
                with st.status("Processing Summaries...", expanded=True) as status:
                    
                    for v_key in selected_versions:
                        v_info = explain_prompt_version(v_key, all_versions)
                        v_name = v_info.get("name", "Unknown")
                        
                        status.write(f"🤖 Testing **{v_name}**...")
                        
                        # Get prompt template and combine with critical style instruction
                        start = time.time()
                        prompt_template = get_prompt_template(v_key)
                        
                        # The robust instruction is appended to force compliance
                        full_prompt = prompt_template.format(text=user_input) + critical_instruction

                        try:
                            response = client.chat.completions.create(
                                model="gpt-3.5-turbo",
                                messages=[{"role": "user", "content": full_prompt}],
                                temperature=0.5,
                                max_tokens=700 # Increased max tokens for flexibility
                            )
                            
                            summary_text = response.choices[0].message.content
                            duration = time.time() - start
                            
                            # Calculate Metrics
                            basic = calculate_basic_metrics(user_input, summary_text)
                            readability = calculate_readability_score(summary_text)
                            rouge = {"rougeL": None}
                            
                            if reference_summary:
                                rouge = calculate_rouge_scores(reference_summary, summary_text)
                            
                            # Log metrics
                            log_summary(len(user_input), len(summary_text), basic['compression_ratio'], summary_tone, summary_length, input_source, file_type, duration)
                            
                            if reference_summary:
                                log_prompt_evaluation(v_key, user_input, summary_text, reference_summary, rouge, basic, readability, duration)

                            results_cache[v_key] = {
                                "name": v_name,
                                "text": summary_text,
                                "time": duration,
                                "metrics": basic,
                                "readability": readability,
                                "rouge": rouge
                            }
                            
                        except Exception as e:
                            status.write(f"❌ Error in {v_name}: {e}")
                    
                    status.update(label="✅ Summarization Complete! See Results Below", state="complete", expanded=False)

                
                # --- RESULTS VIEW: Tabs for each Method ---
                if results_cache:
                    st.subheader("📝 Summary Comparison")
                    
                    # Create dynamic tabs
                    tabs = st.tabs([data["name"] for data in results_cache.values()])
                    
                    for tab, (key, data) in zip(tabs, results_cache.items()):
                        with tab:
                            st.markdown(f"<div class='result-container'><h3>📄 {data['name']}</h3></div>", unsafe_allow_html=True)
                            st.text_area("Generated Summary", value=data['text'], height=300, label_visibility="collapsed")
                            
                            # The Statistics Row
                            st.markdown("#### 📊 Performance Metrics")
                            m_col1, m_col2, m_col3, m_col4 = st.columns(4)
                            
                            with m_col1:
                                st.metric("Processing Time", f"{data['time']:.2f}s", help="How long the AI took to respond.")
                            with m_col2:
                                st.metric("Compression Ratio", f"{data['metrics']['compression_ratio']}%", help="Percentage of original text length saved.")
                            with m_col3:
                                st.metric("Readability Score", f"{data['readability']['readability_score']}/100", help="Higher score means easier to read (Flesch-Kincaid scale).")
                            with m_col4:
                                if data['rouge'].get('rougeL'):
                                    st.metric("ROUGE-L Score", f"{data['rouge']['rougeL']:.3f}", help="Linguistic quality match with your reference summary (0-1.0 scale).")
                                else:
                                    st.metric("ROUGE-L Score", "N/A", help="Provide a reference summary to calculate this metric.")
                            
                            # Detailed Metrics
                            with st.expander("🔍 View Technical Details (ROUGE-1, ROUGE-2, etc.)"):
                                st.json({
                                    "Word Count": len(data['text'].split()),
                                    "Character Count": len(data['text']),
                                    "Avg Sentence Length": data['readability']['avg_sentence_length'],
                                    "Full ROUGE Scores": data['rouge']
                                })
                
                else:
                    st.warning("⚠️ Hmm, no results were generated. Check your OpenAI key and input content!")
        
        elif user_input:
            st.warning("⚠️ Pick at least one summary method above to try!")

    else:
        st.info("👆 **Start here:** Paste some text or upload a file to get summaries!")


# =================================================================
# TAB 2: FULL ANALYTICS 
# =================================================================
with main_tab2:
    st.header("📈 Application Analytics")
    st.caption("Overview of all summary generations, regardless of prompt version.")
    metrics_data = get_metrics_summary()
    
    if metrics_data and "rows" in metrics_data and metrics_data["rows"]:
        # Charts Area
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Tone Distribution")
            if "tone_distribution" in metrics_data:
                st.bar_chart(metrics_data["tone_distribution"])
            else:
                st.info("Tone distribution data is missing.")
        with c2:
            st.subheader("Compression Trends")
            df = pd.DataFrame(metrics_data["rows"])
            if not df.empty:
                # Ensure correct type for charting
                df['compression_ratio'] = pd.to_numeric(df['compression_ratio'], errors='coerce') 
                df.dropna(subset=['compression_ratio'], inplace=True)
                if not df.empty:
                    st.line_chart(df["compression_ratio"])
                else:
                    st.info("Not enough valid data points for Compression Trends chart.")
            else:
                st.info("No raw data available for charts.")
        
        st.subheader("Raw Data Logs")
        st.dataframe(metrics_data["rows"], use_container_width=True)
    else:
        st.info("No data available yet. Generate a summary to populate this tab.")

# =================================================================
# TAB 3: A/B TESTING HISTORY 
# =================================================================
with main_tab3:
    st.header("🧪 Prompt Evaluation History")
    st.caption("Historical performance metrics for different Prompt Versions (strategies) when compared with a Reference Summary.")
    eval_data = get_evaluation_summary()
    
    if eval_data:
        st.subheader("Prompt Performance Comparison")
        
        # Clean Table for Version Comparison
        comp_data = []
        if "version_stats" in eval_data:
            for v_key, stats in eval_data["version_stats"].items():
                comp_data.append({
                    "Version": get_version_name(v_key),
                    "Tests Run": stats["count"],
                    "Avg ROUGE-L": f"{stats['avg_rougeL']:.3f}",
                    "Avg Time (s)": f"{stats['avg_time']:.2f}"
                })
            st.dataframe(comp_data, use_container_width=True)
        else:
            st.info("Version statistics are not available.")
        
        if "rows" in eval_data:
            st.subheader("Raw Evaluation Logs")
            st.dataframe(eval_data["rows"], use_container_width=True)
    else:
        st.info("Run comparisons with a reference summary in the 'Summarize & Compare' tab to populate this history.")


# ===== FOOTER =====
st.divider()
st.markdown("""
<div style="text-align: center; padding: 20px; background: linear-gradient(90deg, rgba(102, 126, 234, 0.1), rgba(118, 75, 162, 0.1)); border-radius: 8px; margin-top: 30px;">
    <p style="color: #666; margin: 0;">
        💡 <b>Tips:</b> The new system prioritizes your Tone and Length settings for strict compliance.
    </p>
    <p style="color: #999; font-size: 12px; margin-top: 10px;">
        Made to be simple • Powered by AI • No technical skills needed
    </p>
</div>
""", unsafe_allow_html=True)
