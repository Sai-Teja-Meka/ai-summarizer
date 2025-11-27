import streamlit as st
import openai # The new client is imported from the top-level 'openai' module
from dotenv import load_dotenv
import os

# Load environment variables (API key)
load_dotenv()
# 1. Initialize the Client
# The API key is automatically picked up from the environment variable "OPENAI_API_KEY"
# or you can pass it explicitly: client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
client = openai.OpenAI() 

# Page configuration
st.set_page_config(
    page_title="AI Content Summarizer",
    page_icon="📝",
    layout="centered"
)

# Title
st.title("📝 AI Content Summarizer")
st.write("Paste any text below, and AI will create a concise summary for you.")

# Input section
user_input = st.text_area(
    label="Paste your text here:",
    placeholder="Enter the document or article you want summarized...",
    height=200
)

# Summarization options
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

# Summarize button
if st.button("✨ Summarize", type="primary"):
    if not user_input.strip():
        st.error("Please paste some text first!")
    else:
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
                # 2. Updated API Call using the client object
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.5,
                    max_tokens=500
                )
                
                # Extract summary (also slightly different in v1.0.0+)
                summary = response.choices[0].message.content
                
                # Display results
                st.success("✅ Summary complete!")
                st.subheader("Summary:")
                st.write(summary)
                
                # Show metadata
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Original Length", f"{len(user_input)} characters")
                with col2:
                    st.metric("Summary Length", f"{len(summary)} characters")
                
                # Copy button (user can copy summary)
                st.text_area("Copy your summary:", value=summary, height=100)
                
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
                st.write("Make sure your API key is valid and you have remaining API quota.")

# Footer
st.divider()
st.write("**How it works:** This app uses OpenAI's GPT-3.5-turbo to understand and summarize text. All processing happens in real-time.")
st.write("**Cost:** ~$0.001 per summary (very cheap!)")