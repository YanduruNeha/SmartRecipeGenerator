import cv2
import pytesseract
import openai
import torch
import torchvision.transforms as transforms
from PIL import Image
import numpy as np
import easyocr
from transformers import AutoModelForImageClassification
import db_connect  # Importing the connection code

# Preprocessing function for image enhancement (OCR)
def preprocess_image(image):
    gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred_image = cv2.GaussianBlur(gray_image, (5, 5), 0)
    thresh_image = cv2.adaptiveThreshold(blurred_image, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                         cv2.THRESH_BINARY, 11, 2)
    kernel = np.ones((3, 3), np.uint8)
    processed_image = cv2.morphologyEx(thresh_image, cv2.MORPH_CLOSE, kernel)
    return processed_image

# Tesseract OCR Function
def ocr_with_tesseract(image):
    text = pytesseract.image_to_string(image)
    return text

# EasyOCR Function
def ocr_with_easyocr(image_path):
    reader = easyocr.Reader(['en'])
    result = reader.readtext(image_path, detail=0)
    return result


def classify_fruit_vegetable(image):
    model = AutoModelForImageClassification.from_pretrained("jazzmacedo/fruits-and-vegetables-detector-36")
    labels = list(model.config.id2label.values())

    preprocess = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])

    pil_image = Image.fromarray(image)
    input_tensor = preprocess(pil_image).unsqueeze(0)
    outputs = model(input_tensor)
    predicted_idx = torch.argmax(outputs.logits, dim=1).item()
    predicted_label = labels[predicted_idx]
    return predicted_label

# GPT API call
def ask_gpt(prompt):
    # Get GPT key from your db connection (make sure db_connect.get_gpt_key() works as expected)
    gpt_key = db_connect.get_gpt_key()
    
    # Set the OpenAI API key
    openai.api_key = gpt_key

    try:
        # Make the request to OpenAI's GPT-3.5 API
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",  # Use the appropriate model
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}  # Pass the user input prompt here
            ]
        )

        # Extract and return the response message content
        return response['choices'][0]['message']['content']

    except Exception as e:
        print(f"Error while generating response from GPT: {e}")
        return "Sorry, I couldn't process that."







# Fruits/Vegetables detection using pre-trained model

# Function to insert data into user_recipes table
def insert_recipe(username, ingredients, recipe, cooking_time, nutritional_info, cuisine):
    connection = db_connect.get_db_connection()

    if not connection:
        print("Failed to connect to the database.")
        return

    try:
        cur = connection.cursor()

        # Convert ingredients list to a string
        ingredients_str = ', '.join(ingredients)

        # Check for duplicate recipe names before insertion
        cur.execute("SELECT * FROM recipes WHERE recipe = %s", (recipe,))
        if cur.fetchone():
            print(f"Recipe '{recipe}' already exists in the database. Generating a new name...")

        else:
            cur.execute(""" 
                INSERT INTO recipes (username, ingredients, recipe, cooking_time, nutritional_info, cuisine)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (username, ingredients_str, recipe, cooking_time, nutritional_info, cuisine))

            connection.commit()
            print("Recipe inserted successfully.")
    except Exception as e:
        print(f"Database error: {e}")
    finally:
        if cur:
            cur.close()
        if connection:
            connection.close()
