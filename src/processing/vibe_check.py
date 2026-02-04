import torch
from PIL import Image
from transformers import CLIPModel, CLIPProcessor

# Load the model once (Global variable to avoid reloading it 100 times)
print("🧠 Loading AI Model (CLIP)... this might take a minute...")
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32", use_safetensors=True)
model.eval()
model.to(device)
processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")


def _normalize_embedding(embedding: torch.Tensor) -> torch.Tensor:
    return torch.nn.functional.normalize(embedding, p=2, dim=-1)


def _move_inputs_to_device(inputs: dict) -> dict:
    return {key: value.to(device) for key, value in inputs.items()}


def get_text_embedding(text):
    """Converts a search query (e.g., 'aggressive defense') into numbers."""
    inputs = _move_inputs_to_device(processor(text=[text], return_tensors="pt", padding=True))
    with torch.no_grad():
        text_features = model.get_text_features(**inputs)
    text_features = _normalize_embedding(text_features)
    return text_features[0].tolist()  # Convert tensor to standard list


def get_image_embedding(image_path_or_url):
    """Converts an image into numbers."""
    if isinstance(image_path_or_url, str):
        # If it's a URL or path, open it. 
        # Note: For URLs, you'd need requests.get(), but we'll assume local paths for now
        image = Image.open(image_path_or_url)
    else:
        image = image_path_or_url

    inputs = _move_inputs_to_device(processor(images=image, return_tensors="pt"))
    with torch.no_grad():
        image_features = model.get_image_features(**inputs)
    image_features = _normalize_embedding(image_features)
    return image_features[0].tolist()
