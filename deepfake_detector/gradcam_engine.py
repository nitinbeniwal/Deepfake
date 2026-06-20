"""
gradcam_engine.py — Grad-CAM heatmap generation for forensic evidence.

Generates visual explanations showing WHICH facial regions triggered the
FAKE classification. Used for law enforcement reports.

Supports:
  - Xception (timm): target = last conv block (block12)
  - EfficientNet-B4 (timm): target = conv_head

Output: base64-encoded PNG overlay (original face + heatmap) per face crop.
"""

import os, base64, io
import numpy as np


def _get_target_layer(model, model_type: str):
    """Return the last meaningful convolutional layer for Grad-CAM."""
    try:
        if model_type == "xception":
            # timm Xception: last separable conv block before global avg pool
            return [model.block12.rep[-1]]
        elif model_type == "efficientnet_b4":
            # timm EfficientNet-B4: conv_head is the last conv before pooling
            return [model.conv_head]
        else:
            return None
    except AttributeError:
        return None


def generate_gradcam(
    model,
    model_type: str,
    face_paths: list,
    fake_class_idx: int = 1,
    max_faces: int = 5,
) -> list:
    """
    Generate Grad-CAM heatmap overlays for top face crops.

    Args:
        model: timm model (Xception or EfficientNet-B4 wrapper's .model)
        model_type: "xception" or "efficientnet_b4"
        face_paths: list of face image paths
        fake_class_idx: index of FAKE class in model output (default 1)
        max_faces: max number of faces to process (memory limit)

    Returns:
        list of dicts: [{path, heatmap_b64, fake_prob}, ...]
    """
    try:
        from pytorch_grad_cam import GradCAM
        from pytorch_grad_cam.utils.image import show_cam_on_image
        from pytorch_grad_cam.utils.model_targets import ClassifierOutputTarget
    except ImportError:
        print("[gradcam] grad-cam package not installed — skipping")
        return []

    try:
        import torch
        from torchvision import transforms
        from PIL import Image
    except ImportError:
        return []

    target_layers = _get_target_layer(model, model_type)
    if not target_layers:
        print(f"[gradcam] No target layer found for {model_type}")
        return []

    if model_type == "xception":
        input_size = 299
        norm_mean, norm_std = [0.5, 0.5, 0.5], [0.5, 0.5, 0.5]
    else:
        input_size = 380
        norm_mean, norm_std = [0.485, 0.456, 0.406], [0.229, 0.224, 0.225]

    preprocess = transforms.Compose([
        transforms.Resize((input_size, input_size)),
        transforms.ToTensor(),
        transforms.Normalize(norm_mean, norm_std),
    ])

    results = []
    targets = [ClassifierOutputTarget(fake_class_idx)]

    model.eval()

    cam = GradCAM(model=model, target_layers=target_layers)

    for path in face_paths[:max_faces]:
        try:
            pil = Image.open(path).convert("RGB")
            tensor = preprocess(pil).unsqueeze(0)

            # Grad-CAM mask
            grayscale_cam = cam(input_tensor=tensor, targets=targets)
            grayscale_cam = grayscale_cam[0]  # (H, W)

            # Get fake probability
            with torch.no_grad():
                probs = torch.softmax(model(tensor), dim=1)
                fake_prob = float(probs[0][fake_class_idx])

            # Overlay on original image (resize to match)
            rgb = np.array(pil.resize((input_size, input_size))).astype(np.float32) / 255.0
            overlay = show_cam_on_image(rgb, grayscale_cam, use_rgb=True)

            # Encode as base64 PNG
            img_pil = Image.fromarray(overlay)
            buf = io.BytesIO()
            img_pil.save(buf, format="PNG")
            b64 = base64.b64encode(buf.getvalue()).decode("utf-8")

            results.append({
                "face_path": os.path.basename(path),
                "heatmap_b64": b64,
                "fake_probability": round(fake_prob * 100, 2),
            })

        except Exception as e:
            print(f"[gradcam] Error on {os.path.basename(path)}: {e}")

    return results


def gradcam_for_image(image_path: str, model_type: str = "xception") -> dict:
    """
    Run Grad-CAM on a single image using the classifier's loaded model.
    Returns dict with heatmap_b64 and fake_probability, or error.
    """
    try:
        from classifier import _get_xception, _get_efficientnet

        if model_type == "xception":
            wrapper = _get_xception()
            if wrapper is None:
                return {"error": "Xception model not loaded"}
            model = wrapper.model
        elif model_type == "efficientnet_b4":
            wrapper = _get_efficientnet()
            if wrapper is None:
                return {"error": "EfficientNet-B4 model not loaded"}
            model = wrapper.model
        else:
            return {"error": f"Unknown model_type: {model_type}"}

        results = generate_gradcam(model, model_type, [image_path], max_faces=1)
        return results[0] if results else {"error": "Grad-CAM produced no output"}

    except Exception as e:
        return {"error": str(e)}
