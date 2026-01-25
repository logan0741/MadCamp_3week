"""
VTON Postprocessor
Enhances output quality of virtual try-on results.
"""

import cv2
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter
from typing import Optional, Tuple
from loguru import logger


class VTONPostprocessor:
    """
    Postprocessor for IDM-VTON outputs.

    Handles:
    - Artifact removal
    - Color correction
    - Sharpness enhancement
    - Face restoration (preserves original face)
    """

    def __init__(
        self,
        enable_face_restoration: bool = True,
        enhance_sharpness: bool = True,
        enhance_color: bool = True,
    ):
        """
        Initialize postprocessor.

        Args:
            enable_face_restoration: Restore original face from input
            enhance_sharpness: Apply sharpening filter
            enhance_color: Enhance color saturation
        """
        self.enable_face_restoration = enable_face_restoration
        self.enhance_sharpness = enhance_sharpness
        self.enhance_color = enhance_color

        logger.info("VTONPostprocessor initialized")

    def process(
        self,
        output_image: Image.Image,
        original_person_image: Optional[Image.Image] = None,
    ) -> Image.Image:
        """
        Post-process VTON output.

        Args:
            output_image: VTON output image
            original_person_image: Original person image (for face restoration)

        Returns:
            Enhanced output image
        """
        result = output_image.copy()

        # Restore original face if enabled and source image provided
        if self.enable_face_restoration and original_person_image is not None:
            result = self._restore_face(result, original_person_image)

        # Enhance sharpness
        if self.enhance_sharpness:
            result = self._enhance_sharpness(result)

        # Enhance color
        if self.enhance_color:
            result = self._enhance_color(result)

        # Remove artifacts
        result = self._remove_artifacts(result)

        return result

    def _restore_face(
        self,
        output_image: Image.Image,
        original_image: Image.Image,
        feather_radius: int = 20,
    ) -> Image.Image:
        """
        Restore original face from source image.

        This prevents face distortion that can occur during try-on.

        Args:
            output_image: VTON output
            original_image: Original person image
            feather_radius: Smoothing radius for face boundary

        Returns:
            Image with restored face
        """
        # TODO: Integrate face detection and alignment (MediaPipe, DLIB)
        logger.warning("Face restoration not fully implemented. Using simplified version.")

        # Simplified: Blend top 30% of image
        width, height = output_image.size
        original_resized = original_image.resize((width, height), Image.Resampling.LANCZOS)

        # Create gradient mask for smooth blending
        mask = Image.new("L", (width, height), 0)
        gradient_height = int(height * 0.3)

        # Draw gradient
        import numpy as np
        mask_array = np.array(mask)

        for y in range(gradient_height):
            # Linear gradient from 255 (top) to 0 (bottom)
            alpha = int(255 * (1 - y / gradient_height))
            mask_array[y, :] = alpha

        # Apply Gaussian blur for smooth transition
        mask = Image.fromarray(mask_array)
        mask = mask.filter(ImageFilter.GaussianBlur(feather_radius))

        # Composite images
        result = Image.composite(original_resized, output_image, mask)

        return result

    def _enhance_sharpness(
        self,
        image: Image.Image,
        factor: float = 1.5,
    ) -> Image.Image:
        """
        Enhance image sharpness.

        Args:
            image: Input image
            factor: Sharpness factor (1.0 = original, >1.0 = sharper)

        Returns:
            Sharpened image
        """
        enhancer = ImageEnhance.Sharpness(image)
        return enhancer.enhance(factor)

    def _enhance_color(
        self,
        image: Image.Image,
        saturation_factor: float = 1.2,
        contrast_factor: float = 1.1,
    ) -> Image.Image:
        """
        Enhance color saturation and contrast.

        Args:
            image: Input image
            saturation_factor: Color saturation multiplier
            contrast_factor: Contrast multiplier

        Returns:
            Enhanced image
        """
        # Enhance saturation
        enhancer = ImageEnhance.Color(image)
        result = enhancer.enhance(saturation_factor)

        # Enhance contrast
        enhancer = ImageEnhance.Contrast(result)
        result = enhancer.enhance(contrast_factor)

        return result

    def _remove_artifacts(
        self,
        image: Image.Image,
        denoise_strength: float = 0.5,
    ) -> Image.Image:
        """
        Remove compression artifacts and noise.

        Args:
            image: Input image
            denoise_strength: Denoising strength (0.0 to 1.0)

        Returns:
            Denoised image
        """
        if denoise_strength <= 0:
            return image

        # Convert to OpenCV format
        img_array = np.array(image)
        img_cv = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)

        # Apply bilateral filter (preserves edges while removing noise)
        h_param = int(denoise_strength * 10)
        denoised = cv2.bilateralFilter(img_cv, d=5, sigmaColor=h_param, sigmaSpace=h_param)

        # Convert back to PIL
        denoised_rgb = cv2.cvtColor(denoised, cv2.COLOR_BGR2RGB)
        return Image.fromarray(denoised_rgb)

    def blend_with_original(
        self,
        output_image: Image.Image,
        original_image: Image.Image,
        mask: Image.Image,
        feather_radius: int = 10,
    ) -> Image.Image:
        """
        Blend VTON output with original image using mask.

        Args:
            output_image: VTON output
            original_image: Original person image
            mask: Blending mask (white=use output, black=use original)
            feather_radius: Smoothing radius for mask edges

        Returns:
            Blended image
        """
        # Ensure all images are same size
        width, height = output_image.size
        original_resized = original_image.resize((width, height), Image.Resampling.LANCZOS)
        mask_resized = mask.resize((width, height), Image.Resampling.LANCZOS)

        # Feather mask edges
        mask_feathered = mask_resized.filter(ImageFilter.GaussianBlur(feather_radius))

        # Composite images
        result = Image.composite(output_image, original_resized, mask_feathered)

        return result

    def apply_color_transfer(
        self,
        source_image: Image.Image,
        target_garment_image: Image.Image,
    ) -> Image.Image:
        """
        Transfer color statistics from target garment to result.

        This ensures the output garment color matches the original garment.

        Args:
            source_image: VTON output image
            target_garment_image: Original garment image

        Returns:
            Color-corrected image
        """
        # Convert to LAB color space
        source_array = cv2.cvtColor(np.array(source_image), cv2.COLOR_RGB2LAB)
        target_array = cv2.cvtColor(np.array(target_garment_image), cv2.COLOR_RGB2LAB)

        # Calculate statistics
        source_mean, source_std = source_array.mean(axis=(0, 1)), source_array.std(axis=(0, 1))
        target_mean, target_std = target_array.mean(axis=(0, 1)), target_array.std(axis=(0, 1))

        # Transfer color statistics (only to A and B channels, preserve L)
        result_array = source_array.copy().astype(np.float32)
        for channel in [1, 2]:  # A and B channels
            result_array[:, :, channel] = (
                (result_array[:, :, channel] - source_mean[channel])
                * (target_std[channel] / source_std[channel])
                + target_mean[channel]
            )

        # Clip values and convert back
        result_array = np.clip(result_array, 0, 255).astype(np.uint8)
        result_rgb = cv2.cvtColor(result_array, cv2.COLOR_LAB2RGB)

        return Image.fromarray(result_rgb)

    def create_comparison_grid(
        self,
        original_person: Image.Image,
        garment: Image.Image,
        output: Image.Image,
        labels: Optional[list[str]] = None,
    ) -> Image.Image:
        """
        Create side-by-side comparison grid.

        Args:
            original_person: Original person image
            garment: Garment image
            output: VTON output
            labels: Optional text labels for each image

        Returns:
            Grid image
        """
        if labels is None:
            labels = ["Original", "Garment", "Try-On Result"]

        # Resize all to same height
        target_height = 512
        images = [original_person, garment, output]
        resized = []

        for img in images:
            aspect = img.width / img.height
            new_width = int(target_height * aspect)
            resized.append(img.resize((new_width, target_height), Image.Resampling.LANCZOS))

        # Create grid
        total_width = sum(img.width for img in resized) + 40  # 20px padding between
        grid = Image.new("RGB", (total_width, target_height + 50), (255, 255, 255))

        # Paste images
        x_offset = 20
        for img, label in zip(resized, labels):
            grid.paste(img, (x_offset, 30))

            # Add label (requires PIL font - optional)
            # from PIL import ImageDraw, ImageFont
            # draw = ImageDraw.Draw(grid)
            # draw.text((x_offset, 5), label, fill=(0, 0, 0))

            x_offset += img.width + 20

        return grid
