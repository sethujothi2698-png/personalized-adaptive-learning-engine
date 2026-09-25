import streamlit as st
import json
import os
from google import genai
from google.genai import types

st.set_page_config(page_title="Adaptive Learning Engine", page_icon="🎓", layout="wide")

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
    st.error("⚠️ GEMINI_API_KEY not found in Streamlit Secrets! Please configure it in settings.")
    st.stop()

# Initialize Client
client = genai.Client(api_key=api_key.strip())

def generate_question(topic, difficulty, previous_gaps):
    prompt = f"""
    You are an adaptive tutor.
    Topic: {topic}
    Difficulty level: {difficulty}
    Known learner gaps: {', '.join(previous_gaps) if previous_gaps else 'None'}

    Generate a multiple-choice question testing the user's understanding.
    If there are known gaps, tailor the question to test/reinforce those specific concepts.
    
    Return pure JSON with keys:
    - "question": string
    - "options": list of 4 strings
    - "correct_answer": string (exact match to one option)
    - "concept_tested": string
    """
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt,
        config=types.GenerateContentConfig(response_mime_type="application/json")
    )
    return json.loads(response.text)

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
    
    Return pure JSON with keys:
    - "gap_summary": short string summarizing the gap
    - "explanation": string with clear concept clarification
    """
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt,
        config=types.GenerateContentConfig(response_mime_type="application/json")
    )
    return json.loads(response.text)

st.title("🎓 Personalized Adaptive Learning Engine")
st.caption("WO-034: Real-time diagnostic quiz with instant remedial adaptation")

if not st.session_state.initialized:
    if st.button("Start Diagnostic Session", type="primary"):
        with st.spinner("Generating first question..."):
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
                    st.session_state.learning_gaps.append(remediation.get("gap_summary", "Gap identified"))
                    st.session_state.last_feedback = {
                        "is_correct": False,
                        "gap": remediation.get("gap_summary", ""),
                        "explanation": remediation.get("explanation", "")
                    }
            
            with st.spinner("Adapting next question to your learning pace..."):
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
