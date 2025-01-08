import streamlit as st
import numpy as np
from PIL import Image
from db_connect import get_db_connection, get_gpt_key
import bcrypt
from psycopg2.errors import UniqueViolation
from sourcecode1 import preprocess_image, ocr_with_tesseract, ocr_with_easyocr, ask_gpt, classify_fruit_vegetable, insert_recipe

# CSS for background image and custom styling
page_bg_img = '''
<style>
.stApp {
    background-image: url('https://st2.depositphotos.com/3476693/10008/i/950/depositphotos_100089844-stock-photo-healthy-cooking-background.jpg');
    background-size: cover;
    background-position: center;
}
.sidebar .sidebar-content {
    background-color: rgba(0, 0, 0, 0.5);
}
[data-testid="stHeader"] {
    background-color: rgba(0, 0, 0, 0);
}
.stTextInput input, .stTextArea textarea, .stButton > button {
    background-color: rgba(255, 255, 255, 0.7);
    color: black;
}
.stButton > button {
    background-color: white;  /* Default button background color */
    color: black;  /* Default button text color */
    border: 1px solid #cccccc;  /* Light border for contrast */
    padding: 10px 20px;
    cursor: pointer;
    font-weight: bold;
}
.stButton > button:hover {
    background-color: #f0f0f0;  /* Slightly darker shade when hovered */
}
.stButton > button:active {
    background-color: orange;  /* Change to orange when clicked */
    color: black;  /* Text remains black */
    transform: translateY(1px);  /* Optional: Slight 'pressed' effect */
}
</style>
'''
st.markdown(page_bg_img, unsafe_allow_html=True)
st.markdown("""
    <h1 style="text-align: center; color: Black; font-size: 2.25rem; font-family: 'Trebuchet MS', sans-serif;">
        🍽️ Smart Recipe Generator 🍽️
    </h1>
""", unsafe_allow_html=True)

# Sidebar for navigation
with st.sidebar:
    if st.session_state.get("username"):
        st.sidebar.subheader("Profile Details")
    else:
        st.title("Menu")
        page = st.radio("Select Option", ("Home","Login", "Register"))
        st.session_state["page"] = page

# Initialize session state
# Initialize session state
if "username" not in st.session_state:
    st.session_state["username"] = None
if "page" not in st.session_state:
    st.session_state["page"] = "Home"
if "profile_data" not in st.session_state:
    st.session_state["profile_data"] = {}
if "current_recipe_name" not in st.session_state:
    st.session_state["current_recipe_name"] = ""
if "recipe_generated" not in st.session_state:
    st.session_state["recipe_generated"] = False  # New flag for recipe generation



def home():
    st.markdown("""
        <div style="text-align: center; font-family: 'Georgia', serif; font-size: 1.2rem; margin-top: 20px;">
            "Cooking is an art, and Smart Recipe Generator is your canvas! 🎨✨"
        </div>
        <hr style="border: 1px solid #ccc; margin-top: 20px; margin-bottom: 20px;">
    """, unsafe_allow_html=True)
    
    st.subheader("Welcome to Smart Recipe Generator!")
    
    # Enhanced content styling
    st.markdown("""
        <div style="font-family: 'Arial', sans-serif; font-size: 1.1rem; line-height: 1.8; color: #333; margin-top: 20px;">
            <ul style="list-style-type: disc; padding-left: 20px;">
                <li><strong>Upload an image:</strong> Detect ingredients using advanced OCR technology.</li>
                <li><strong>Generate Recipes:</strong> Get tailored recipe suggestions with detailed instructions.</li>
                <li><strong>Save Your Favorites:</strong> Save recipes to your personal collection and access them anytime.</li>
                <li><strong>View Saved Recipes:</strong> Explore your saved recipes and revisit your favorites easily.</li>
            </ul>
            <p style="margin-top: 10px; font-weight: bold; text-align: center;">
                Sign in to get started or register if you're new here!
            </p>
        </div>
    """, unsafe_allow_html=True)


# Helper function to convert profile picture data if needed
def get_image_data(profile_picture_data):
    if isinstance(profile_picture_data, memoryview):
        profile_picture_data = profile_picture_data.tobytes()
    return profile_picture_data

# User registration function
def register_user(username, phone_no, email, profile_picture_data, password):
    connection = get_db_connection()
    if connection is None:
        return "Database connection error."
    try:
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO users (username, phone_no, email, profile_picture, password) VALUES (%s, %s, %s, %s, %s)",
                (username, phone_no, email, profile_picture_data, hashed_password.decode('utf-8'))
            )
            connection.commit()
            return True
    except UniqueViolation:
        return "Username or email already exists. Please choose a different one."
    except Exception as e:
        return f"Registration failed: {e}"
    finally:
        connection.close()

# User authentication function
def authenticate_user(username, password):
    connection = get_db_connection()
    if connection is None:
        return False
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT password, phone_no, email, profile_picture FROM users WHERE username = %s", (username,))
            result = cursor.fetchone()
            if result:
                stored_password, phone_no, email, profile_picture = result
                if bcrypt.checkpw(password.encode('utf-8'), stored_password.encode('utf-8')):
                    st.session_state["profile_data"] = {
                        "username": username,
                        "phone_no": phone_no,
                        "email": email,
                        "profile_picture": profile_picture
                    }
                    return True
                else:
                    st.error("Login failed. Incorrect password.")
            else:
                st.error("Login failed. Username not found.")
            return False
    except Exception as e:
        st.error(f"Error during authentication: {e}")
        return False
    finally:
        connection.close()

# Registration page
# Registration page
def register():
    st.subheader("Register")
    username = st.text_input("Username")
    phone_no = st.text_input("Phone Number")
    email = st.text_input("Email")
    profile_picture = st.file_uploader("Profile Picture", type=["jpg", "jpeg", "png"])
    password = st.text_input("Password", type="password")

    if st.button("Register"):
        if username and phone_no and email and profile_picture and password:
            # Validate email length
            if len(email) < 16:
                st.error("Email must contain at least 6 characters.")
                return
            
            # Validate phone number format
            if not (phone_no.isdigit() and len(phone_no) == 10 and phone_no[0] in "6789"):
                st.error("Phone number must start with 6, 7, 8, or 9 and be 10 digits long.")
                return
            
            # Read and save profile picture data
            profile_picture_data = profile_picture.read()
            
            # Register user
            registration_response = register_user(username, phone_no, email, profile_picture_data, password)
            if registration_response == True:
                st.success("Registration successful! Please log in.")
                st.session_state["page"] = "login"
            else:
                st.error(registration_response)
        else:
            st.error("All fields are required.")


# Login page
def login():
    st.subheader("Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    
    if st.button("Login"):
        if authenticate_user(username, password):
            st.session_state["username"] = username
            st.success(f"Welcome, {username}!")
            st.session_state["page"] = "main"
        else:
            st.error("Login failed. Check your username and password.")


# Function to generate recipe details
def generate_recipe_details(food_category, uploaded_images):
    username = st.session_state["username"]
    all_detected_ingredients = []

    # Process each uploaded image
    for uploaded_file in uploaded_images:
        image = np.array(Image.open(uploaded_file))
        preprocessed_image = preprocess_image(image)
        detected_text = ocr_with_tesseract(preprocessed_image)
        detected_text_easyocr = ocr_with_easyocr(image)
        combined_text = detected_text.strip() + ' ' + ' '.join(detected_text_easyocr).strip()

        if len(combined_text.strip()) > 10:
            gpt_prompt = f"Identify and list only the ingredients or food items from this text: '{combined_text}'"
            gpt_response = ask_gpt(gpt_prompt)
            detected_ingredients = gpt_response.strip().split(", ")
            all_detected_ingredients.extend(detected_ingredients)
        else:
            detected_label = classify_fruit_vegetable(image)
            all_detected_ingredients.append(detected_label)

    unique_ingredients = list(set(all_detected_ingredients))
    # Generate prompts for recipe details
    ing_prompt = f"give me these ingredients {', '.join(unique_ingredients)} each in a new line if first letter capital remaining all small letters in bullet points each."
    ing = ask_gpt(ing_prompt).strip()

    recipe_name = ""
    for _ in range(3):  # Try a few times to get a unique recipe name
        recipe_prompt = f"Generate a recipe name based on the following labels or ingredients for a {food_category}: {', '.join(unique_ingredients)}. Don't give ingredients again."
        recipe_name_candidate = ask_gpt(recipe_prompt).strip()
        if recipe_name_candidate != st.session_state.get("current_recipe_name", ""):
            recipe_name = recipe_name_candidate
            st.session_state["current_recipe_name"] = recipe_name
            break

    procedure_prompt = f"Provide a step-by-step procedure in new lines for preparing the recipe '{recipe_name}' as a {food_category} using ingredients. Don't give ingredients again: {', '.join(unique_ingredients)}. Mention the procedure as of making with the quantity (e.g., 1/2 cup or 30 grams) for better understanding."
    procedure = ask_gpt(procedure_prompt).strip()

    cooking_time_prompt = f"Given the following recipe: {recipe_name}. Provide the approximate cooking time for this recipe. Just mention how many minutes it will take. Do not exceed more than three words and do not mention the recipe name again."
    cooking_time_response = ask_gpt(cooking_time_prompt).strip()
    try:
        cooking_time = int(cooking_time_response.split()[0])
    except ValueError:
        cooking_time = 10  # Default to 20 minutes if parsing fails


    nutritional_info_prompt = (
        f"Given the following recipe: {recipe_name}. "
        "Please provide the nutritional information for this recipe, including approximate values for calories, protein, fat, and carbohydrates. "
        "List each value on a new line, without any headings, and use grams value in the following order:\n"
        "- Calories\n (e.g., Calories :30g)\n"
        "- Protein\n (e.g., Protein :35g)\n"
        "- Fat (e.g., Fat :3g)\n"
        "- Carbohydrates (e.g., Carbohydrates :13g)\n"
        "If precise quantities of each ingredient aren't available, approximate values based on standard serving sizes and typical nutritional content for similar dishes. dont give ingredients names again"
    )
    nutritional_info = ask_gpt(nutritional_info_prompt).strip()

    cuisine_prompt = f"Give the cuisine name only for a recipe named '{recipe_name}' .just give it in one word like italian, indian etc."
    cuisine = ask_gpt(cuisine_prompt).strip()

    return {
        "ingredients": unique_ingredients,
        "recipe_name": recipe_name,
        "procedure": procedure,
        "cooking_time": cooking_time,
        "nutritional_info": nutritional_info,
        "cuisine": cuisine,
        "formatted_ingredients": ing
    }
def main_app():
    
    # Rest of the app content like recipe generation and saved recipes will go here
    tabs = st.tabs(["Instructions","Generate Recipe", "Saved Recipes"])
        # Instructions tab for "Do's and Don'ts"
        # Instructions tab for "Do's and Don'ts"
    with tabs[0]:
        st.subheader("Do's and Don'ts for Uploading Images")
        # Don'ts section
        st.write("### Don'ts")
        st.write("1. Do not upload images containing **multiple ingredients** grouped together.")
        st.write("2. Avoid blurry or out-of-focus images.")
        st.write("3. Do not use images with complex backgrounds or additional objects.")
        st.write("4. Avoid images with poor lighting or shadows over the ingredient.")

    # Example images for Don'ts
        st.write("**Example images for Don'ts**:")
        dont_columns = st.columns(3)
        dont_images = [
        "C:/Users/yvind/Downloads/Smart-Recipe-Generator_oct_2024/Tested_images/donts_1.jpg",
        "C:/Users/yvind/Downloads/Smart-Recipe-Generator_oct_2024/Tested_images/donts_2.jpg",
        "C:/Users/yvind/Downloads/Smart-Recipe-Generator_oct_2024/Tested_images/donts_3.jpg",
        ]
    
        for i, img_path in enumerate(dont_images):
            dont_columns[i].image(img_path, width=150)  # Adjust width as needed
    # Do's section
        st.write("### Do's")
        st.write("1. Upload a clear image of a **single ingredient** at a time.")
        st.write("2. Make sure the ingredient is well-lit and fully visible in the image.")
        st.write("3. Ensure the image background is plain, without any distracting elements.")
        st.write("4. For best results, take photos of the ingredients on a contrasting background (e.g., white for dark ingredients).")
    
    # Example images for Do's
        st.write("**Example images for Do's**:")
        do_columns = st.columns(3)
        do_images = [
        "C:/Users/yvind/Downloads/Smart-Recipe-Generator_oct_2024/Tested_images/dos_1.jpg",
        "C:/Users/yvind/Downloads/Smart-Recipe-Generator_oct_2024/Tested_images/dos_2.jpg",
        "C:/Users/yvind/Downloads/Smart-Recipe-Generator_oct_2024/Tested_images/dos_3.jpg"
        ]
    
        for i, img_path in enumerate(do_images):
            do_columns[i].image(img_path, width=150)  # Adjust width as needed
    


    with tabs[1]:
        st.subheader("Generate a Recipe")
        uploaded_images = st.file_uploader("Upload Ingredient Images", accept_multiple_files=True, type=["jpg", "jpeg", "png"])
        food_category = st.selectbox("Select Food Category", ["Vegetarian", "Non-Vegetarian", "Dessert", "Vegan", "Snack", "Salad", "Soup", "Gluten-Free"])

        if st.session_state.get("username") and not st.session_state["recipe_generated"]:
            if st.button("Generate Recipe"):
                if uploaded_images:
                    recipe_details = generate_recipe_details(food_category, uploaded_images)
                    display_recipe_details(recipe_details)
                    st.session_state["recipe_generated"] = True  
                else:
                    st.error("Please upload at least one ingredient image.")
    
        if st.session_state["recipe_generated"]:
            if st.button("Save Recipe"):
                recipe_data = st.session_state["generated_recipe"]
                insert_recipe(
                st.session_state["username"],
                recipe_data["ingredients"],
                recipe_data["recipe_name"],
                recipe_data["cooking_time"],
                recipe_data["nutritional_info"],
                recipe_data["cuisine"]
                )
                st.success("Recipe saved successfully!")
                st.session_state["generated_recipe"] = None
                st.session_state["recipe_generated"] = False

            if st.button("Generate Another Recipe"):
                st.session_state["generated_recipe"] = None
                st.session_state["recipe_generated"] = False
                if uploaded_images:
                    recipe_details = generate_recipe_details(food_category, uploaded_images)
                    display_recipe_details(recipe_details)
                    st.session_state["recipe_generated"] = True
                else:
                    st.error("Please upload at least one ingredient image.")
    with tabs[2]:
        connection = get_db_connection()
        if connection:
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT recipe FROM recipes WHERE username = %s", (st.session_state["username"],))
                    recipes = cursor.fetchall()
                
                    if recipes:
                        recipe_names = ["Select a recipe"] + [recipe[0] for recipe in recipes]  # Add placeholder
                        selected_recipe = st.selectbox("Please select a saved recipe to view details", recipe_names, index=0)  # Default to "Select a recipe"

                        if selected_recipe != "Select a recipe":  # Check if the user selected an actual recipe
                            cursor.execute(
                                "SELECT ingredients, recipe, cooking_time, nutritional_info, cuisine FROM recipes WHERE recipe = %s AND username = %s",
                                (selected_recipe, st.session_state["username"])
                            )
                            recipe_details = cursor.fetchone()
                        
                            if recipe_details:
                                st.write("### Recipe Details")
                                st.write("**Ingredients**:", recipe_details[0])
                                st.write("**Recipe Name**:", recipe_details[1])
                                st.write("**Cooking Time (mins)**:", recipe_details[2])
                                st.write("**Nutritional Info**:", recipe_details[3])
                                st.write("**Cuisine**:", recipe_details[4])
                            else:
                                st.write("No details found for the selected recipe.")

                    else:
                        st.write("No saved recipes found.")
            except Exception as e:
                st.error(f"Error fetching saved recipes: {e}")
            finally:
                connection.close()

def display_recipe_details(recipe_details):
    st.subheader("Generated Recipe Details")
    st.write(f"**Recipe Name:** {recipe_details['recipe_name']}")
    st.write(f"**Ingredients:**")
    st.write(recipe_details['formatted_ingredients'])
    st.write("**Procedure:**")
    st.write(recipe_details['procedure'])
    st.write(f"**Cooking Time:** {recipe_details['cooking_time']} minutes")
    st.write("**Nutritional Info:**")
    st.write(recipe_details['nutritional_info'])
    st.write("**Cuisine:**")
    st.write(recipe_details['cuisine'])

    # Store the generated recipe in session state
    st.session_state["generated_recipe"] = recipe_details

# Profile view section
if st.session_state.get("username"):
    profile_data = st.session_state["profile_data"]
    profile_image_data = get_image_data(profile_data["profile_picture"])
    
    # Display profile details in sidebar
    st.sidebar.image(profile_image_data, width=100, use_column_width=False)
    
    st.sidebar.write(f"**Username:** {profile_data['username']}")
    st.sidebar.write(f"**Email:** {profile_data['email']}")
    st.sidebar.write(f"**Phone:** {profile_data['phone_no']}")
    
    # Custom styled Logout button
    if st.sidebar.button("Logout"):
        st.session_state["username"] = None
        st.session_state["page"] = "Login"
        st.session_state["profile_data"] = {}


# Page rendering based on session state
if st.session_state["page"] == "Home":
    home()
if st.session_state["page"] == "Login":
    login()
elif st.session_state["page"] == "Register":
    register()
elif st.session_state.get("username"):
    main_app()
    
