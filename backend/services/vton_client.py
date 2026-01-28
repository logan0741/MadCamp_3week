"""
VTON Client - Virtual Try-On using Gemini (Nano Banana Pro API)
"""
import os
import base64
import logging
import google.generativeai as genai
import httpx
from core.config import settings

logger = logging.getLogger(__name__)

# Configure Gemini
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    logger.warning("GEMINI_API_KEY is not set. VTON features will not work.")
else:
    genai.configure(api_key=api_key)


async def generate_try_on_image(user_image_path: str, product_image_url: str, output_path: str) -> bool:
    """
    Generate VTON image using Gemini
    
    Args:
        user_image_path: Local path to user's photo
        product_image_url: URL of the product image
        output_path: Local path to save the generated image
    
    Returns:
        bool: Success
    """
    try:
        # 1. Load User Image
        if not os.path.exists(user_image_path):
            logger.error(f"User image not found: {user_image_path}")
            return False
            
        with open(user_image_path, "rb") as f:
            user_image_data = f.read()

        # 2. Download Product Image
        async with httpx.AsyncClient() as client:
            resp = await client.get(product_image_url)
            if resp.status_code != 200:
                logger.error(f"Failed to download product image: {product_image_url}")
                return False
            product_image_data = resp.content

        # 3. Prepare Model (Nano Banana Pro / gemini-3-pro-image-preview)
        # Note: The user explicitly requested 'gemini-3-pro-image-preview'
        # If this model name is invalid in the actual API, it will raise an error.
        model_name = 'gemini-3-pro-image-preview'
        try:
             model = genai.GenerativeModel(model_name)
        except Exception:
             # Fallback if the user's specific model name is valid but maybe configured differently?
             # Or maybe it's just 'gemini-pro-vision'?
             # But user requested SPECIFIC code. I will stick to it.
             logger.warning(f"Model {model_name} might be invalid, trying instantiation anyway.")
             model = genai.GenerativeModel(model_name)

        # 4. Construct Prompt
        # "Generate a realistic image of [User] wearing [Cloth]..."
        prompt = [
            "You are a professional fashion stylist AI.",
            "Please synthesize a 'Virtual Try-On' photo.",
            "1. The first image is the User.",
            "2. The second image is the Clothing Product.",
            "Task: Generate a realistic photo of the User wearing the Clothing Product. Keep the background futuristic.",
            "Ensure the face and body shape match the User. Ensure the clothing details match the Product.",
            {
                "mime_type": "image/jpeg",
                "data": user_image_data
            },
            {
                "mime_type": "image/jpeg", 
                "data": product_image_data
            },
             "Generate a high quality, realistic result."
        ]

        # 5. Generate Content
        response = model.generate_content(prompt)
        
        # 6. Decode and Save
        # The user provided snippet:
        # img_data = base64.b64decode(response.parts[0].inline_data.data)
        # However, standard Gemini response for images usually involves candidate access or direct access if it's text.
        # But if the output is an image, the user instructions say:
        # img_data = base64.b64decode(response.parts[0].inline_data.data)
        
        try:
            # We assume response structure based on user input. 
            # Real Gemini API returns text unless it's a specific image generation model.
            # If 'gemini-3-pro-image-preview' is an image generation model, it might return parts with inline_data.
            if hasattr(response, 'parts') and response.parts:
                part = response.parts[0]
                if hasattr(part, 'inline_data') and part.inline_data:
                    img_data = base64.b64decode(part.inline_data.data)
                    with open(output_path, 'wb') as f:
                        f.write(img_data)
                    return True
                else:
                    # Fallback/Check if it returned text
                    logger.error(f"Response did not contain inline_data. Content: {response.text if hasattr(response, 'text') else 'Unknown'}")
                    return False
            else:
                logger.error("Response parts missing.")
                return False
                
        except Exception as e:
            logger.error(f"Error processing response: {e}")
            return False

    except Exception as e:
        logger.error(f"VTON generation failed: {e}")
        return False
