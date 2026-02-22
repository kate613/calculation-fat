import telebot
from PIL import Image
import cv2
import numpy as np
from ultralytics import YOLO
import config
import io

# Initialize bot
bot = telebot.TeleBot(config.API_TOKEN)
CUSTOM_MODEL_PATH = "yolo26n.pt"

# Load model once
model = YOLO("yolo26n.pt")

FOOD_NUTRITION = {
    "samosa": {"calories": 262, "protein": 4.5, "fat": 17, "carbs": 24},
    "dosa": {"calories": 168, "protein": 3.9, "fat": 6, "carbs": 26},
    "banana": {"calories": 105, "protein": 1.3, "fat": 0.4, "carbs": 27},
    "pizza": {"calories": 285, "protein": 12, "fat": 10, "carbs": 36},
}

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, """Hello! You're welcome to the best carb calculating bot!
Here you can send a picture of your food and I will calculate how many carbs it has 🔥 
Type /help to get better instructions""")

@bot.message_handler(commands=['help'])
def send_help(message):
    bot.reply_to(message, "Send me a photo of food and I'll estimate its calories and nutrients!")

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    try:
        # Send typing indicator
        bot.send_chat_action(message.chat.id, 'typing')
        
        # Get the photo file
        file_id = message.photo[-1].file_id
        file_info = bot.get_file(file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        # Convert to image
        image_bytes = io.BytesIO(downloaded_file)
        pil_image = Image.open(image_bytes).convert("RGB")
        
        # Process image with YOLO
        results = model(pil_image)
        
        # Convert to OpenCV format for drawing
        image_np = np.array(pil_image)
        frame_bgr = cv2.cvtColor(image_np, cv2.COLOR_RGB2BGR)
        
        # Draw boxes and detect items
        detected_items = []
        if results[0].boxes and model.names:
            for box in results[0].boxes:
                cls_id = int(box.cls.item())
                label = model.names[cls_id].lower().replace(" ", "")
                if label in FOOD_NUTRITION:
                    detected_items.append(label)
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    cv2.rectangle(frame_bgr, (x1, y1), (x2, y2), (3, 50, 8), 2)
        
        if detected_items:
            # Remove duplicates
            detected_items = list(set(detected_items))
            
            # Calculate totals
            total_calories = sum(FOOD_NUTRITION[item]['calories'] for item in detected_items)
            
            # Convert back to RGB for saving
            frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
            result_image = Image.fromarray(frame_rgb)
            
            # Save to bytes
            img_bytes = io.BytesIO()
            result_image.save(img_bytes, format='JPEG')
            img_bytes.seek(0)
            
            # Send annotated photo
            bot.send_photo(message.chat.id, img_bytes)
            
            # Send nutrition info
            response = "**Detected items:**\n"
            for item in detected_items:
                info = FOOD_NUTRITION[item]
                response += f"• {item.title()}: {info['calories']} kcal\n"
            response += f"\n**Total calories: {total_calories} kcal**"
            
            bot.reply_to(message, response, parse_mode='Markdown')
        else:
            bot.reply_to(message, "No recognizable food items detected. Try a clearer photo!")
            
    except Exception as e:
        bot.reply_to(message, f"Sorry, an error occurred: {str(e)}")

    bot.infinity_polling()