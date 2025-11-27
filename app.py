import streamlit as st
import openai # The new client is imported from the top-level 'openai' module

# 1. Initialize the Client
# The API key is automatically picked up from the environment variable "OPENAI_API_KEY"
# or you can pass it explicitly: client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# Page configuration
st.set_page_config(
    page_title="AI Content Summarizer",
    page_icon="📝",
    layout="centered"
)

# Title
st.title("📝 AI Content Summarizer")
st.write("Paste text, upload a file, or provide a URL to summarize with AI.")

# ===== INPUT SOURCE SELECTION =====
st.subheader("📥 Choose Your Input Method")

input_method = st.radio(
    "How do you want to provide content?",
    ("Paste Text", "Upload File"),
    horizontal=True
)

# Initialize user_input
user_input = ""
uploaded_file = None

# ===== PASTE TEXT METHOD =====
if input_method == "Paste Text":
    user_input = st.text_area(
        label="Paste your text here:",
        placeholder="Enter the document or article you want summarized...",
        height=200
    )

# ===== FILE UPLOAD METHOD =====
else:  # input_method == "Upload File"
    st.write("**Supported formats:** PDF, DOCX (Word), PPTX (PowerPoint), TXT (Text) --- (Maximum Size: 5MB)")
    
    uploaded_file = st.file_uploader(
        label="Upload a file to summarize",
        type=["pdf", "docx", "pptx", "txt"],
        accept_multiple_files=False  # One file at a time
    )
    
    if uploaded_file is not None:
        # Check file size (limit to 5MB)
        max_size_mb = 5
        file_size_mb = uploaded_file.size / (1024 * 1024)
        
        if file_size_mb > max_size_mb:
            st.error(f"❌ File too large! Max size: {max_size_mb}MB, your file: {file_size_mb:.1f}MB")
            user_input = ""
        else:
            # Extract text from uploaded file (Only proceeds if size check passed)
            user_input = extract_text_from_file(uploaded_file)
            
            if user_input:
                st.success(f"✅ Successfully extracted text from {uploaded_file.name}")
                st.write(f"**File size:** {len(user_input)} characters")
            else:
                st.error("Failed to extract text. Please check the file.")
                user_input = ""

# ===== SUMMARIZATION OPTIONS =====
if user_input and client:  # Only show options if there's content and client is initialized
    st.divider()
    st.subheader("⚙️ Summarization Settings")
    
    col1, col2 = st.columns(2)
    with col1:
        summary_length = st.radio(
            "Summary length:",
            ("Short (1-2 sentences)", "Medium (3-5 sentences)", "Long (detailed)")
        )

    with col2:
        tone = st.radio(
            "Tone:",
            ("Neutral", "Academic", "Casual")
        )

    # ===== SUMMARIZE BUTTON =====
    if st.button("✨ Summarize", type="primary", use_container_width=True):
        
        # Create prompt based on user selections
        length_guide = {
            "Short (1-2 sentences)": "Summarize in 1-2 sentences",
            "Medium (3-5 sentences)": "Summarize in 3-5 sentences",
            "Long (detailed)": "Provide a detailed summary (5-10 sentences)"
        }
        
        tone_guide = {
            "Neutral": "Use neutral, objective tone",
            "Academic": "Use academic, formal language",
            "Casual": "Use casual, friendly language"
        }
        
        prompt = f"""You are a helpful summarizer. 
{length_guide[summary_length]}.
{tone_guide[tone]}.

Text to summarize:
{user_input}

Summary:"""
        
        # Show loading indicator
        with st.spinner("🤖 AI is summarizing... please wait"):
            try:
                # Call OpenAI API
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.5,
                    max_tokens=500
                )
                
                # Extract summary
                summary = response.choices[0].message.content
                
                # Display results
                st.success("✅ Summary complete!")
                st.subheader("Summary:")
                st.write(summary)
                
                # Show metadata
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Original Length", f"{len(user_input)} chars")
                with col2:
                    st.metric("Summary Length", f"{len(summary)} chars")
                
                # Copy button (user can copy summary)
                st.text_area("📋 Copy your summary:", value=summary, height=100)
                
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
                st.write("Make sure your API key is valid and you have remaining API quota.")

else:
    if input_method == "Upload File" and uploaded_file is None:
        st.info("👆 Upload a file above to get started")
    elif input_method == "Paste Text":
        st.info("👆 Paste some text above to get started")

# Footer
st.divider()
st.write("**How it works:** Upload or paste content → AI creates a summary → Copy it with one click!")
