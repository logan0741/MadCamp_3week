"""
VTON Preprocessor
Handles image preprocessing for virtual try-on inference.
"""

import cv2
import numpy as np
from PIL import Image
from typing import Tuple, Optional
from loguru import logger


class VTONPreprocessor:
    """
    Preprocessor for IDM-VTON inputs.

    Handles:
    - Image resizing and aspect ratio preservation
    - Person detection and cropping
    - Background removal (optional)
    - Image normalization
    """

    def __init__(
        self,
        target_size: Tuple[int, int] = (768, 768),
        enable_background_removal: bool = False,
    ):
        """
        Initialize preprocessor.

        Args:
            target_size: Target image size (width, height)
            enable_background_removal: Remove background from person image
        """
        self.target_size = target_size
        self.enable_background_removal = enable_background_removal

        logger.info(f"VTONPreprocessor initialized (target_size={target_size})")

    def process_person_image(
        self,
        image: Image.Image,
        crop_to_person: bool = True,
    ) -> Image.Image:
        """
        Preprocess person image for VTON.

        Args:
            image: Input PIL Image
            crop_to_person: Automatically crop to person's bounding box

        Returns:
            Preprocessed PIL Image
        """
        # Convert to RGB if needed
        if image.mode != "RGB":
            image = image.convert("RGB")

        # Optionally crop to person
        if crop_to_person:
            image = self._crop_to_person(image)

        # Resize to target size
        image = self._resize_with_padding(image, self.target_size)

        # Optionally remove background
        if self.enable_background_removal:
            image = self._remove_background(image)

        return image

    def process_garment_image(
        self,
        image: Image.Image,
        remove_background: bool = True,
    ) -> Image.Image:
        """
        Preprocess garment image.

        Args:
            image: Input PIL Image
            remove_background: Remove background from garment

        Returns:
            Preprocessed PIL Image
        """
        # Convert to RGB
        if image.mode != "RGB":
            image = image.convert("RGB")

        # Remove background from garment (usually on white background)
        if remove_background:
            image = self._remove_white_background(image)

        # Resize to target size
        image = self._resize_with_padding(image, self.target_size)

        return image

    def _crop_to_person(self, image: Image.Image) -> Image.Image:
        """
        Detect and crop to person's bounding box.

        This is a simplified implementation using OpenCV's face detection.
        For production, use a proper person detector (YOLOv8, MediaPipe, etc.).

        Args:
            image: Input image

        Returns:
            Cropped image
        """
        # TODO: Integrate person detection model (YOLOv8-pose recommended)

        # For now, return original image with center crop
        logger.warning("Using simplified person cropping. Integrate pose detector for production.")

        width, height = image.size

        # Assume person is in center with 80% coverage
        crop_width = int(width * 0.8)
        crop_height = int(height * 0.9)

        left = (width - crop_width) // 2
        top = int(height * 0.05)
        right = left + crop_width
        bottom = top + crop_height

        return image.crop((left, top, right, bottom))

    def _resize_with_padding(
        self,
        image: Image.Image,
        target_size: Tuple[int, int],
        fill_color: Tuple[int, int, int] = (255, 255, 255),
    ) -> Image.Image:
        """
        Resize image while maintaining aspect ratio using padding.

        Args:
            image: Input image
            target_size: Target (width, height)
            fill_color: Padding color (RGB)

        Returns:
            Resized and padded image
        """
        target_width, target_height = target_size
        img_width, img_height = image.size

        # Calculate scaling factor
        scale = min(target_width / img_width, target_height / img_height)

        new_width = int(img_width * scale)
        new_height = int(img_height * scale)

        # Resize image
        resized = image.resize((new_width, new_height), Image.Resampling.LANCZOS)

        # Create padded canvas
        padded = Image.new("RGB", target_size, fill_color)

        # Paste resized image in center
        paste_x = (target_width - new_width) // 2
        paste_y = (target_height - new_height) // 2
        padded.paste(resized, (paste_x, paste_y))

        return padded

    def _remove_background(self, image: Image.Image) -> Image.Image:
        """
        Remove background from person image.

        Uses rembg library or custom segmentation model.

        Args:
            image: Input image

        Returns:
            Image with transparent/white background
        """
        try:
            from rembg import remove

            # Remove background
            output = remove(image)

            # Convert transparent background to white
            white_bg = Image.new("RGB", output.size, (255, 255, 255))
            white_bg.paste(output, mask=output.split()[3])  # Use alpha channel as mask

            return white_bg

        except ImportError:
            logger.warning("rembg not installed. Skipping background removal.")
            logger.info("Install with: pip install rembg[gpu]")
            return image

    def _remove_white_background(
        self,
        image: Image.Image,
        threshold: int = 240,
    ) -> Image.Image:
        """
        Remove white background from garment image.

        Args:
            image: Input image
            threshold: White threshold (0-255)

        Returns:
            Image with background removed
        """
        # Convert to numpy array
        img_array = np.array(image)

        # Create mask for white pixels
        # White pixels have all channels > threshold
        white_mask = np.all(img_array > threshold, axis=2)

        # Create RGBA image
        rgba = np.dstack((img_array, np.where(white_mask, 0, 255).astype(np.uint8)))

        # Convert back to PIL
        output = Image.fromarray(rgba, mode="RGBA")

        # Paste on white background for RGB output
        white_bg = Image.new("RGB", output.size, (255, 255, 255))
        white_bg.paste(output, mask=output.split()[3])

        return white_bg

    def create_mask_from_segmentation(
        self,
        image: Image.Image,
        target_labels: list[str] = ["upper_clothes"],
    ) -> Image.Image:
        """
        Create mask from human parsing segmentation.

        Args:
            image: Input person image
            target_labels: Body parts to mask (e.g., ["upper_clothes", "dress"])

        Returns:
            Binary mask image
        """
        # TODO: Integrate human parsing model (LIP, Graphonomy, SCHP)
        logger.warning("Segmentation mask generation not implemented. Using placeholder.")

        # Return white mask for entire torso region
        width, height = image.size
        mask = Image.new("L", (width, height), 0)

        # Simple torso rectangle
        from PIL import ImageDraw
        draw = ImageDraw.Draw(mask)

        torso_bbox = (
            int(width * 0.25),
            int(height * 0.2),
            int(width * 0.75),
            int(height * 0.7),
        )
        draw.rectangle(torso_bbox, fill=255)

        return mask

    def normalize_image(
        self,
        image: Image.Image,
        mean: Tuple[float, float, float] = (0.5, 0.5, 0.5),
        std: Tuple[float, float, float] = (0.5, 0.5, 0.5),
    ) -> np.ndarray:
        """
        Normalize image for neural network input.

        Args:
            image: Input PIL Image
            mean: Channel-wise mean
            std: Channel-wise standard deviation

        Returns:
            Normalized numpy array (C, H, W)
        """
        # Convert to numpy array and normalize to [0, 1]
        img_array = np.array(image).astype(np.float32) / 255.0

        # Apply normalization
        img_array = (img_array - mean) / std

        # Convert from (H, W, C) to (C, H, W)
        img_array = np.transpose(img_array, (2, 0, 1))

        return img_array
