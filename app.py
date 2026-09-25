import streamlit as st
import json
import os
import google.generativeai as genai

st.set_page_config(page_title="Adaptive Learning Engine", page_icon="🎓", layout="wide")

# API Key config
api_key = st.secrets.get("GEMINI_API_KEY", os.environ.get("GEMINI_API_KEY", None))

st.sidebar.title("⚙️ Configuration")
topic = st.sidebar.text_input("Topic", value="Python Data Structures")
difficulty = st.sidebar.selectbox("Difficulty", ["Beginner", "Intermediate", "Advanced"])

if st.sidebar.button("Restart / Reset Session"):
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

if "initialized" not in st.session_state:
    st.session_state.initialized = False
    st.session_state.current_question = None
    st.session_state.learning_gaps = []
    st.session_state.score = 0
    st.session_state.total = 0
    st.session_state.last_feedback = None

if not api_key:
    st.error("⚠️ GEMINI_API_KEY not found in Streamlit Secrets! Please add it in App Settings.")
    st.stop()

# Configure API
genai.configure(api_key=api_key.strip())

@st.cache_resource
def get_available_model():
    """Auto-detect available model for this API key to avoid NotFound error."""
    preferred_models = [
        "models/gemini-1.5-flash",
        "models/gemini-1.5-flash-latest",
        "models/gemini-pro",
        "gemini-1.5-flash",
        "gemini-pro"
    ]
    try:
        available = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        for pref in preferred_models:
            if pref in available:
                return pref
        if available:
            return available[0]
    except Exception:
        pass
    return "gemini-1.5-flash"

selected_model_name = get_available_model()
model = genai.GenerativeModel(model_name=selected_model_name)

def clean_json_response(raw_text):
    text = raw_text.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return json.loads(text.strip())

def generate_question(topic, difficulty, previous_gaps):
    prompt = f"""
    You are an adaptive tutor.
    Topic: {topic}
    Difficulty level: {difficulty}
    Known learner gaps: {', '.join(previous_gaps) if previous_gaps else 'None'}

    Generate a multiple-choice question testing the user's understanding.
    If there are known gaps, tailor the question to test/reinforce those specific concepts.
    
    Return ONLY a valid JSON object (no markdown, no extra explanation) with keys:
    - "question": string
    - "options": list of 4 strings
    - "correct_answer": string (exact match to one option)
    - "concept_tested": string
    """
    response = model.generate_content(prompt)
    return clean_json_response(response.text)

def generate_remediation(question_obj, user_answer):
    prompt = f"""
    The learner got this question wrong:
    Question: {question_obj['question']}
    Correct Answer: {question_obj['correct_answer']}
    Learner Answer: {user_answer}
    Concept Tested: {question_obj['concept_tested']}

    Provide:
    1. A precise diagnosis of the conceptual misunderstanding / gap.
    2. A short, crystal-clear remedial explanation to correct the misunderstanding.
    
    Return ONLY a valid JSON object (no markdown, no extra text) with keys:
    - "gap_summary": short string summarizing the gap
    - "explanation": string with clear concept clarification
    """
    response = model.generate_content(prompt)
    return clean_json_response(response.text)

# Main Screen
st.title("🎓 Personalized Adaptive Learning Engine")
st.caption("WO-034: Real-time diagnostic quiz with instant remedial adaptation")

if not st.session_state.initialized:
    if st.button("Start Diagnostic Session", type="primary"):
        with st.spinner("Generating first diagnostic question..."):
            st.session_state.current_question = generate_question(topic, difficulty, [])
            st.session_state.initialized = True
            st.rerun()
    st.stop()

col_quiz, col_analytics = st.columns([3, 2])

with col_quiz:
    st.subheader("Quiz Arena")
    q = st.session_state.current_question
    if q:
        st.write(f"**Target Concept:** `{q.get('concept_tested', 'General')}`")
        st.write(f"### {q.get('question', '')}")
        
        options = q.get("options", [])
        selected_option = st.radio("Choose your answer:", options, key=f"q_{st.session_state.total}")
        
        if st.button("Submit Answer"):
            st.session_state.total += 1
            if selected_option == q.get("correct_answer"):
                st.session_state.score += 1
                st.session_state.last_feedback = {
                    "is_correct": True,
                    "msg": "🎉 Correct! Moving to the next challenge."
                }
            else:
                with st.spinner("Analyzing learning gap..."):
                    remediation = generate_remediation(q, selected_option)
                    st.session_state.learning_gaps.append(remediation.get("gap_summary", "Concept Gap"))
                    st.session_state.last_feedback = {
                        "is_correct": False,
                        "gap": remediation.get("gap_summary", ""),
                        "explanation": remediation.get("explanation", "")
                    }
            
            with st.spinner("Adapting next question to your pace..."):
                st.session_state.current_question = generate_question(
                    topic, difficulty, st.session_state.learning_gaps
                )
            st.rerun()

    if st.session_state.last_feedback:
        fb = st.session_state.last_feedback
        if fb["is_correct"]:
            st.success(fb["msg"])
        else:
            st.error(f"**Identified Gap:** {fb['gap']}")
            st.warning(f"**Remedial Explanation:** {fb['explanation']}")

with col_analytics:
    st.subheader("Learner Analytics")
    st.metric("Score", f"{st.session_state.score} / {st.session_state.total}")
    
    st.write("#### 🎯 Identified Learning Gaps")
    if st.session_state.learning_gaps:
        for i, gap in enumerate(st.session_state.learning_gaps, 1):
            st.write(f"{i}. ⚠️ {gap}")
    else:
        st.write("No gaps detected yet. Great job!")
