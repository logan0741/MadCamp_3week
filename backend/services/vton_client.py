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
    logger.info(f" [VTON-API] Requesting Gemini VTON - User Path: {user_image_path}")
    try:
        # 1. Load User Image
        if not os.path.exists(user_image_path):
            logger.error(f" [VTON-API] User image not found: {user_image_path}")
            return False
            
        with open(user_image_path, "rb") as f:
            user_image_data = f.read()
        logger.info(f" [VTON-API] Loaded user image ({len(user_image_data)} bytes)")

        # 2. Download Product Image
        logger.info(f" [VTON-API] Downloading product image from: {product_image_url}")
        async with httpx.AsyncClient() as client:
            resp = await client.get(product_image_url)
            if resp.status_code != 200:
                logger.error(f" [VTON-API] Failed to download product image. Status: {resp.status_code}")
                return False
            product_image_data = resp.content
        logger.info(f" [VTON-API] Downloaded product image ({len(product_image_data)} bytes)")

        # 3. Prepare Model
        model_name = 'gemini-3-pro-image-preview'
        logger.info(f" [VTON-API] Configuring Gemini model: {model_name}")
        try:
             model = genai.GenerativeModel(model_name)
        except Exception as e:
             logger.warning(f" [VTON-API] Model {model_name} initialization warning: {e}")
             model = genai.GenerativeModel(model_name)

        # 4. Construct Prompt
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
        logger.info(" [VTON-API] Sending request to Gemini...")
        response = model.generate_content(prompt)
        logger.info(" [VTON-API] Response received from Gemini")
        
        # 6. Decode and Save
        try:
            if hasattr(response, 'parts') and response.parts:
                logger.info(f" [VTON-API] Response has {len(response.parts)} parts")
                part = response.parts[0]
                
                # Log response structure for debugging
                logger.info(f" [VTON-API] Part 0 keys: {dir(part)}")
                
                if hasattr(part, 'inline_data') and part.inline_data:
                    logger.info(" [VTON-API] Found inline_data in response")
                    img_data = base64.b64decode(part.inline_data.data)
                    with open(output_path, 'wb') as f:
                        f.write(img_data)
                    logger.info(f" [VTON-API] Saved generated image to: {output_path}")
                    return True
                else:
                    # Log text content if no image data
                    text_content = response.text if hasattr(response, 'text') else 'No text'
                    logger.error(f" [VTON-API] Response did not contain inline_data. Text length: {len(text_content)}")
                    logger.error(f" [VTON-API] Text snippet: {text_content[:200]}...")
                    return False
            else:
                logger.error(" [VTON-API] Response parts missing or empty")
                if hasattr(response, 'prompt_feedback'):
                    logger.error(f" [VTON-API] Prompt feedback: {response.prompt_feedback}")
                return False
                
        except Exception as e:
            logger.error(f" [VTON-API] Error processing response: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False

    except Exception as e:
        logger.error(f" [VTON-API] VTON generation failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False
