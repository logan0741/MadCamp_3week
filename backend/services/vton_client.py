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
# Default to Gemini 1.5 Flash - it's fast and supports multimodal
DEFAULT_MODEL_NAME = 'gemini-2.5-flash-image'

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
    if not api_key:
        logger.error(" [VTON-API] GEMINI_API_KEY is not set!")
        return False

    try:
        logger.info(f" [VTON-API] Requesting Gemini VTON - User Path: {user_image_path}")
        
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

        # 3. Choose Model
        # Using a fallback mechanism: environment variable > 'gemini-2.5-flash-image' (reliable)
        model_candidate = os.getenv("GEMINI_MODEL_NAME", DEFAULT_MODEL_NAME)
        
        try:
            model = genai.GenerativeModel(model_candidate)
            logger.info(f" [VTON-API] Using Gemini model: {model_candidate}")
        except Exception as e:
            logger.warning(f" [VTON-API] Model {model_candidate} not found, falling back to {DEFAULT_MODEL_NAME}")
            model = genai.GenerativeModel(DEFAULT_MODEL_NAME)

        # 4. Construct Prompt
        prompt = [
            "Task: Generate a image by putting the clothing the person in the 'Clothing Product Image' is wearing onto the person in the 'User Image'.",
            "Only change the clothing. Keep the user's face, body, pose, and identity unchanged.",
            "Match the clothing's color, texture, and details as closely as possible.",
            "Use a modern fitting room background"
            "User Image:",
            {
                "mime_type": "image/jpeg",
                "data": user_image_data
            },
            "Clothing Product Image:",
            {
                "mime_type": "image/jpeg",
                "data": product_image_data
            },
            "\nIMPORTANT: If you can generate the image, return it in your response parts. If you cannot generate binary images, please describe why."
        ]

        # 5. Generate Content
        logger.info(" [VTON-API] Sending request to Gemini (Async)...")
        response = await model.generate_content_async(prompt)
        logger.info(" [VTON-API] Response received from Gemini")

        # 6. Parse Response
        success = False
        
        if not hasattr(response, 'parts') or not response.parts:
            logger.error(" [VTON-API] Response has no parts (blocked or empty)")
            if hasattr(response, 'text'):
                logger.warning(f" [VTON-API] Response Text: {response.text}")
            return False

        for i, part in enumerate(response.parts):
            # Check for inline_data (which could be an image)
            if hasattr(part, 'inline_data') and part.inline_data:
                mime = part.inline_data.mime_type
                logger.info(f" [VTON-API] Part {i} has inline_data (mime: {mime})")
                if 'image' in mime:
                    img_data = part.inline_data.data
                    # base64 decode if needed
                    if isinstance(img_data, str):
                        img_data = base64.b64decode(img_data)
                    
                    with open(output_path, 'wb') as f:
                        f.write(img_data)
                    logger.info(f" ✅ [VTON-API] Successfully saved generated image to: {output_path}")
                    success = True
                    break
            
            # Check for text
            if hasattr(part, 'text') and part.text:
                logger.info(f" [VTON-API] Part {i} contains text: {part.text[:200]}...")

        if not success:
            logger.warning(" [VTON-API] No image found in Gemini response. The LLM might have returned only text.")
            if hasattr(response, 'text'):
                logger.info(f" [VTON-API] Gemini Text Response: {response.text[:500]}")
            
        return success

    except Exception as e:
        logger.error(f" ❌ [VTON-API] VTON generation failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False
