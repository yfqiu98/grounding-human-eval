import os
import json
import random
import streamlit as st
import pandas as pd
from datetime import datetime

# ========== CONFIG ==========
MODELS = ["pixinstruct", "got", "chameleon-sft", "chameleon-unsup-sft"]
OUTPUT_DIR = "outputs"
EVAL_INDICES = [0, 1, 2, 3, 50, 51, 52, 53, 54, 55, 100, 101, 102, 103, 104, 105, 106, 200, 201, 202, 203, 204, 350, 351, 352, 353, 354]
# EVAL_INDICES = [0, 1, 2]

TEST_JSON = "test.json"
OUTPUT_PATH = "results"

# ========== LOAD DATA ==========
with open(TEST_JSON, "r") as f:
    test_data = json.load(f)

# ========== SESSION STATE INIT ==========
if "user_id" not in st.session_state:
    st.session_state.user_id = ""
if "annotations" not in st.session_state:
    st.session_state.annotations = []
if "index" not in st.session_state:
    st.session_state.index = 0
if "shuffle_orders" not in st.session_state:
    st.session_state.shuffle_orders = {}

# ========== UI: USER ID ==========
st.title("Anonymous Human Evaluation for Image Editing Models")
st.session_state.user_id = st.text_input("Enter your user ID:", value=st.session_state.user_id)

if not st.session_state.user_id:
    st.warning("Please enter a user ID to begin.")
    st.stop()

# ========== EVALUATION FLOW ==========
i = st.session_state.index
if i >= len(EVAL_INDICES):
    st.success("You have completed all evaluations. Thank you!")
    df = pd.DataFrame(st.session_state.annotations)
    os.makedirs(OUTPUT_PATH, exist_ok=True)
    filename = f"{OUTPUT_PATH}/annotations_{st.session_state.user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    df.to_csv(filename, index=False)
    st.write("Your annotations have been saved as:", filename)
    st.stop()

# ========== DISPLAY SAMPLE ==========
sample_index = EVAL_INDICES[i]
sample = test_data[sample_index]

# Shuffle display order but store it to ensure correct mapping
if sample_index not in st.session_state.shuffle_orders:
    shuffled_models = MODELS.copy()
    random.shuffle(shuffled_models)
    st.session_state.shuffle_orders[sample_index] = shuffled_models
else:
    shuffled_models = st.session_state.shuffle_orders[sample_index]

# ========== DISPLAY ==========
st.markdown(f"#### Image ID: `{sample_index}`")
st.markdown(f"<h3 style='color:#333'>Instruction for Editing: {sample['instruction']}</h3>", unsafe_allow_html=True)

st.markdown("**Input Image**")
st.image(sample['input'], width=300)

st.markdown("#### Anonymous Model Outputs")
image_filename = f"{sample_index}.png"
model_display_info = []

for idx, model in enumerate(shuffled_models):
    tag = f"Model {idx+1}"
    img_path = os.path.join(OUTPUT_DIR, model, image_filename)
    model_display_info.append((tag, model, img_path))

output_cols = st.columns(len(model_display_info))
for col, (tag, _, img_path) in zip(output_cols, model_display_info):
    with col:
        st.image(img_path, caption=tag, use_container_width=True)

# ========== ANNOTATION FORM ==========
st.markdown("### Evaluate each model on a 1–5 scale (1 = Poor, 5 = Excellent)")

def likert_input(question, sample_index):
    st.markdown(f"**{question}**")
    scores = {}
    for tag, model, _ in model_display_info:
        # include sample_index in the key
        widget_key = f"{question}-{tag}-sample{sample_index}"
        score = st.selectbox(
            tag,
            [1, 2, 3, 4, 5],
            index=2,           # default to 3
            key=widget_key
        )
        scores[model] = score
    return scores

def best_worst_input(question, sample_index):
    st.markdown(f"**{question}**")

    # Display tags (anonymous model labels)
    tags = [tag for tag, _, _ in model_display_info]
    tag_to_model = {tag: model for tag, model, _ in model_display_info}

    best_options = ["None of them is the best"] + tags
    # worst_options = ["None of them is the worst"] + tags
    worst_options = tags

    best_key = f"{question}-best-sample{sample_index}"
    worst_key = f"{question}-worst-sample{sample_index}"

    best = st.radio(f"Select the BEST model - {question}", best_options, index=0, key=best_key, horizontal=True)
    worst = st.radio(f"Select the WORST model - {question}", worst_options, index=0, key=worst_key, horizontal=True)

    scores = {}
    for tag, model, _ in model_display_info:
        if best == "None of them is the best" and worst == "None of them is the worst":
            scores[model] = 0
        elif tag == best:
            scores[model] = 1
        elif tag == worst:
            scores[model] = -1
        else:
            scores[model] = 0
    return scores

# edit_scores    = likert_input("1. Did the model correctly perform the editing?", sample_index)
# over_scores    = likert_input("2. Is the image over-edited?",               sample_index)
# realism_scores = likert_input("3. How realistic is the result?",           sample_index)

edit_scores    = best_worst_input("1. Did the model correctly perform the editing?", sample_index)
# over_scores    = best_worst_input("2. Is the image over-edited?",               sample_index)
# realism_scores = best_worst_input("3. How realistic is the result?",           sample_index)

# ========== SUBMIT ==========
if st.button("Submit Evaluation"):
    for model in MODELS:
        record = {
            "user_id": st.session_state.user_id,
            "sample_index": sample_index,
            "model": model,
            "edit_score": edit_scores[model],
            # "overedit_score": over_scores[model],
            # "realism_score": realism_scores[model],
        }
        st.session_state.annotations.append(record)

    st.session_state.index += 1
    st.experimental_set_query_params()
    st.rerun()

# ========== RETURN TO PREVIOUS ==========
if st.session_state.index > 0:
    if st.button("← Return to Previous Sample"):
        prev_index = st.session_state.index - 1
        st.session_state.index = prev_index
        st.session_state.annotations = [
            r for r in st.session_state.annotations if r["sample_index"] != EVAL_INDICES[prev_index]
        ]
        st.experimental_set_query_params()
        st.rerun()