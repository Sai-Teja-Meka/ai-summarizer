"""
Prompt Versions Module
Contains different summarization prompt strategies for A/B testing
"""

# ===== VERSION 1: BASIC (Baseline) =====
PROMPT_V1_BASIC = """Summarize the following text concisely:

Text:
{text}

Summary:"""


# ===== VERSION 2: ROLE-BASED (Improved) =====
PROMPT_V2_ROLE_BASED = """You are an expert summarizer. Your task is to create a clear, 
concise summary that captures the main ideas and key facts.

Focus on:
- Main points
- Key findings
- Important details
- Facts over opinions

Text:
{text}

Summary:"""


# ===== VERSION 3: CHAIN-OF-THOUGHT (Advanced) =====
PROMPT_V3_CHAIN_OF_THOUGHT = """You are an expert summarizer. Let's think step by step.

Step 1: Identify the main topic and purpose of the text
Step 2: Find the key arguments or findings
Step 3: Note important statistics or evidence
Step 4: Identify conclusions or recommendations
Step 5: Write a concise summary combining these elements

Text:
{text}

Let's think through this:
1. Main topic: 
2. Key arguments:
3. Important evidence:
4. Conclusions:

Summary:"""


# ===== VERSION 4: STRUCTURED (With constraints) =====
PROMPT_V4_STRUCTURED = """Create a summary with the following structure:

Key Findings (1-2 sentences):
Details (2-3 sentences):
Implications (1-2 sentences):

Text:
{text}

Summary:
Key Findings: [Your response]
Details: [Your response]
Implications: [Your response]"""


# ===== VERSION 5: CONTEXT-AWARE (With examples) =====
PROMPT_V5_CONTEXT_AWARE = """You are an expert summarizer. Create a summary following these examples:

Example Input: "Machine learning is a subset of artificial intelligence..."
Example Summary: "Machine learning, a key AI technology, focuses on algorithms that learn from data."

Now summarize this text in a similar concise style:

Text:
{text}

Summary:"""


# ===== PROMPT REGISTRY =====
PROMPT_VERSIONS = {
    "v1_basic": {
        "name": "Basic Prompt",
        "description": "Simple instruction-based prompt",
        "template": PROMPT_V1_BASIC,
        "version": "v1"
    },
    "v2_role_based": {
        "name": "Role-Based Prompt",
        "description": "Defines expertise role with focus areas",
        "template": PROMPT_V2_ROLE_BASED,
        "version": "v2"
    },
    "v3_chain_of_thought": {
        "name": "Chain-of-Thought Prompt",
        "description": "Step-by-step reasoning approach",
        "template": PROMPT_V3_CHAIN_OF_THOUGHT,
        "version": "v3"
    },
    "v4_structured": {
        "name": "Structured Prompt",
        "description": "Enforces output structure",
        "template": PROMPT_V4_STRUCTURED,
        "version": "v4"
    },
    "v5_context_aware": {
        "name": "Context-Aware Prompt",
        "description": "Provides examples for better alignment",
        "template": PROMPT_V5_CONTEXT_AWARE,
        "version": "v5"
    }
}


def get_prompt_template(version_key):
    """Get prompt template by version key"""
    if version_key in PROMPT_VERSIONS:
        return PROMPT_VERSIONS[version_key]["template"]
    else:
        raise ValueError(f"Unknown prompt version: {version_key}")


def get_all_versions():
    """Get all available prompt versions"""
    return PROMPT_VERSIONS


def get_version_name(version_key):
    """Get display name for version"""
    if version_key in PROMPT_VERSIONS:
        return PROMPT_VERSIONS[version_key]["name"]
    return version_key
