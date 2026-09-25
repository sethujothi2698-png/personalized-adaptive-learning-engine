import streamlit as st
import json
from google import genai
from google.genai import types

st.set_page_config(page_title="Adaptive Learning Engine", page_icon="🎓", layout="wide")

# Sidebar Configuration
st.sidebar.title("⚙️ Configuration")
api_key = st.sidebar.text_input("Enter Gemini API Key", type="password")
topic = st.sidebar.text_input("Topic", value="Python Data Structures")
difficulty = st.sidebar.selectbox("Difficulty", ["Beginner", "Intermediate", "Advanced"])

if st.sidebar.button("Restart / Reset Session"):
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

# State initialization
if "initialized" not in st.session_state:
    st.session_state.initialized = False
    st.session_state.current_question = None
    st.session_state.history = []
    st.session_state.learning_gaps = []
    st.session_state.score = 0
    st.session_state.total = 0
    st.session_state.last_feedback = None

def get_client():
    if not api_key:
        st.error("Please provide a Gemini API Key in the sidebar.")
        return None
    return genai.Client(api_key=api_key)

def generate_question(client, topic, difficulty, previous_gaps):
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
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(response_mime_type="application/json")
    )
    return json.loads(response.text)

def generate_remediation(client, question_obj, user_answer):
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
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(response_mime_type="application/json")
    )
    return json.loads(response.text)

# Main UI
st.title("🎓 Personalized Adaptive Learning Engine")
st.caption("WO-034: Real-time diagnostic quiz with instant remedial adaptation")

if not api_key:
    st.info("👈 Enter your Gemini API key in the sidebar to get started.")
    st.stop()

client = get_client()

# Start session
if not st.session_state.initialized:
    if st.button("Start Diagnostic Session"):
        with st.spinner("Generating first question..."):
            st.session_state.current_question = generate_question(client, topic, difficulty, [])
            st.session_state.initialized = True
            st.rerun()
    st.stop()

# Layout: Split into Question & Dashboard
col_quiz, col_analytics = st.columns([3, 2])

with col_quiz:
    st.subheader("Quiz Arena")
    q = st.session_state.current_question
    if q:
        st.write(f"**Target Concept:** `{q['concept_tested']}`")
        st.write(f"### {q['question']}")
        
        selected_option = st.radio("Choose your answer:", q["options"], key=f"q_{st.session_state.total}")
        
        if st.button("Submit Answer"):
            st.session_state.total += 1
            if selected_option == q["correct_answer"]:
                st.session_state.score += 1
                st.session_state.last_feedback = {
                    "is_correct": True,
                    "msg": "🎉 Correct! Moving to the next challenge."
                }
            else:
                with st.spinner("Analyzing learning gap..."):
                    remediation = generate_remediation(client, q, selected_option)
                    st.session_state.learning_gaps.append(remediation["gap_summary"])
                    st.session_state.last_feedback = {
                        "is_correct": False,
                        "gap": remediation["gap_summary"],
                        "explanation": remediation["explanation"]
                    }
            
            # Generate next adaptive question based on updated gaps
            with st.spinner("Adapting next question to your learning pace..."):
                st.session_state.current_question = generate_question(
                    client, topic, difficulty, st.session_state.learning_gaps
                )
            st.rerun()

    # Display real-time feedback
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
