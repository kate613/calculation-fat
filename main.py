import streamlit as st
from PIL import Image
import torch
import cv2
import numpy as np
from ultralytics import YOLO

# --- Model and Nutrition Info ---
CUSTOM_MODEL_PATH = "yolo26n.pt"  # Replace with your trained model

FOOD_NUTRITION = {
    "samosa": {"calories": 262, "protein": 4.5, "fat": 17, "carbs": 24, "serving_size": "1 piece (approx. 50g)"},
    "dosa": {"calories": 168, "protein": 3.9, "fat": 6, "carbs": 26, "serving_size": "1 medium plain dosa"},
    "banana": {"calories": 105, "protein": 1.3, "fat": 0.4, "carbs": 27, "serving_size": "1 medium"},
    "pizza": {"calories": 285, "protein": 12, "fat": 10, "carbs": 36, "serving_size": "1 slice"},
    # Add more food items if needed
}

# --- Streamlit Page Setup ---
st.set_page_config(page_title="🖼️ Image Calorie Estimator", layout="centered")
st.title("🖼️ Image-Based Food Calorie Estimator")
st.markdown("**Upload a food image. The model will detect and estimate calories.**")

# --- Load YOLO Model ---
@st.cache_resource
def load_model(path):
    try:
        model = YOLO(path)
        _ = model.predict(Image.new('RGB', (640, 480)))
        return model
    except Exception as e:
        st.error(f"Failed to load YOLO model: {e}")
        return None

model = load_model(CUSTOM_MODEL_PATH)

# --- Image Upload ---
uploaded_file = st.file_uploader("Upload a food image", type=["jpg", "jpeg", "png"])

# --- Frame Analysis and Drawing ---
def analyze_frame(pil_image):
    return model(pil_image)

def draw_boxes(image, results):
    boxes = results[0].boxes
    labels = []
    if boxes and model.names:
        for box in boxes:
            cls_id = int(box.cls.item())
            label = model.names[cls_id].lower().replace(" ", "")
            conf = box.conf.item()
            if label in FOOD_NUTRITION:
                labels.append(label)
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                cv2.rectangle(image, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(image, f"{label} ({conf:.2f})", (x1, y1 - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
    return image, list(set(labels))

# --- Main Logic ---
if model and uploaded_file:
    pil_image = Image.open(uploaded_file).convert("RGB")
    image_np = np.array(pil_image)
    frame_bgr = cv2.cvtColor(image_np, cv2.COLOR_RGB2BGR)

    results = analyze_frame(pil_image)
    annotated_image, detected_items = draw_boxes(frame_bgr.copy(), results)
    frame_rgb = cv2.cvtColor(annotated_image, cv2.COLOR_BGR2RGB)

    st.image(frame_rgb, caption="Detected Image", use_column_width=True)

    if detected_items:
        total_cal, prot, fat, carbs = 0, 0, 0, 0
        results_text = "### 🍽️ Detected Items:\n"
        for item in detected_items:
            if item in FOOD_NUTRITION:
                info = FOOD_NUTRITION[item]
                total_cal += info['calories']
                prot += info['protein']
                fat += info['fat']
                carbs += info['carbs']
                results_text += (
                    f"- **{item.title()}**: {info['calories']} kcal, "
                    f"{info['protein']}g protein, {info['fat']}g fat, {info['carbs']}g carbs  \n"
                )
        results_text += f"\n---\n**Total Estimated Calories:** {total_cal} kcal"
        st.markdown(results_text)
    else:
        st.info("No recognizable food items detected.")
elif not model:
    st.error("❌ Could not load model. Please check your model path.")