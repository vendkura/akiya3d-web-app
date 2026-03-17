"""
FPN Model Inference Wrapper
Loads the trained FPN ResNet34 model and performs inference on floor plan images.
"""

import torch
import torch.nn.functional as F
import segmentation_models_pytorch as smp
from pathlib import Path
from PIL import Image
import numpy as np
import albumentations as A
from albumentations.pytorch import ToTensorV2


class FPNInference:
    """
    Wrapper for FPN inference on floor plan images.
    
    Attributes:
        model_path (Path): Path to the trained model checkpoint
        device (torch.device): GPU or CPU device
        model: Loaded FPN model
        transform: Image transformation pipeline
        class_names (list): 13 room/feature class names
    """
    
    # Class names (must match training)
    CLASS_NAMES = [
        "dining_area", "bathroom", "bedroom", "closet", "room",
        "door", "entrance", "kitchen", "outdoor_space",
        "sliding_door", "stairs", "window", "balcony"
    ]
    
    def __init__(self, model_path, device=None):
        """
        Initialize FPN inference engine.
        
        Args:
            model_path (str or Path): Path to best_model.pth
            device (torch.device, optional): GPU or CPU. Auto-detect if None.
        """
        self.model_path = Path(model_path)
        
        # Robust device detection with CUDA fallback
        if device is None:
            try:
                # Test if CUDA is actually usable
                if torch.cuda.is_available():
                    torch.tensor([1.0]).cuda()  # Test CUDA
                    self.device = torch.device('cuda')
                else:
                    self.device = torch.device('cpu')
            except Exception as e:
                print(f"⚠️ CUDA test failed: {e}")
                print("🔄 Falling back to CPU...")
                self.device = torch.device('cpu')
        else:
            self.device = device
        
        # Validate model exists
        if not self.model_path.exists():
            raise FileNotFoundError(f"Model not found: {self.model_path}")
        
        # Load model
        self.model = self._load_model()
        self.model.to(self.device)
        self.model.eval()
        
        # Transform pipeline (matching training)
        self.transform = A.Compose([
            A.Resize(512, 512),
            A.Normalize(
                mean=[0.485, 0.456, 0.406],
                std=[0.229, 0.224, 0.225]
            ),
            ToTensorV2()
        ])
        
        print(f"✓ FPN model loaded from {self.model_path}")
        print(f"✓ Device: {self.device}")
        print(f"✓ Classes: {len(self.CLASS_NAMES)} ({', '.join(self.CLASS_NAMES)})")
    
    def _load_model(self):
        """Load FPN model with ResNet34 encoder."""
        model = smp.FPN(
            encoder_name='resnet34',
            encoder_weights=None,  # Pre-trained weights already in checkpoint
            in_channels=3,
            classes=13,  # 13 room/feature classes
            activation=None  # Raw logits
        )
        
        # Load checkpoint with proper device mapping
        try:
            checkpoint = torch.load(self.model_path, map_location=self.device)
        except Exception as e:
            print(f"⚠️ Failed to load on {self.device}, trying CPU...")
            checkpoint = torch.load(self.model_path, map_location='cpu')
            self.device = torch.device('cpu')
        
        # Handle different checkpoint formats
        if isinstance(checkpoint, dict) and 'model_state_dict' in checkpoint:
            model.load_state_dict(checkpoint['model_state_dict'])
        elif isinstance(checkpoint, dict) and 'state_dict' in checkpoint:
            model.load_state_dict(checkpoint['state_dict'])
        else:
            # Assume raw state dict
            model.load_state_dict(checkpoint)
        
        return model
    
    def infer(self, image_path, return_prob=False):
        """
        Run inference on a floor plan image.
        
        Args:
            image_path (str or Path): Path to input floor plan image (PNG/JPG)
            return_prob (bool): If True, return probability map and upsampled mask. If False, return class labels.
        
        Returns:
            If return_prob is False:
                mask (np.ndarray): Segmentation mask with shape (H, W) (class IDs 0-12, upsampled)
                original_shape (tuple): Original image (H, W) before resize
                classes_present (dict): Class name → count mapping for detected classes
            If return_prob is True:
                mask (np.ndarray): Segmentation mask (H, W), upsampled to original size
                original_shape (tuple): Original image (H, W)
                classes_present (dict): Class name → count mapping for detected classes
                prob_map (np.ndarray): Probability map (13, H, W), upsampled to original size (bilinear)
        """
        image_path = Path(image_path)
        if not image_path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")
        
        # Load and convert image
        image = Image.open(image_path).convert('RGB')
        original_shape = image.size[::-1]  # (H, W)
        
        # Apply transforms
        image_array = np.array(image)
        transformed = self.transform(image=image_array)
        image_tensor = transformed['image'].unsqueeze(0).to(self.device)  # (1, 3, 512, 512)
        
        # Inference
        with torch.no_grad():
            logits = self.model(image_tensor)  # (1, 13, 512, 512)
            
            if return_prob:
                # Return probability maps for all 13 classes
                probs = F.softmax(logits, dim=1)  # (1, 13, 512, 512)
                probs_np = probs.squeeze(0).cpu().numpy()  # (13, 512, 512)
                # Get class mask (argmax)
                mask_512 = np.argmax(probs_np, axis=0).astype(np.uint8)  # (512, 512)
            else:
                # Return class labels
                mask_512 = torch.argmax(logits, dim=1).squeeze(0).cpu().numpy().astype(np.uint8)  # (512, 512)
        
        # Upsample mask to original size
        mask_pil = Image.fromarray(mask_512)
        mask_original = mask_pil.resize(original_shape[::-1], Image.NEAREST)
        mask_array = np.array(mask_original)
        
        # Analyze detected classes
        unique_classes = np.unique(mask_array)
        classes_present = {
            self.CLASS_NAMES[cls_id]: int(np.sum(mask_array == cls_id))
            for cls_id in unique_classes if cls_id < len(self.CLASS_NAMES)
        }
        
        if not return_prob:
            return mask_array, original_shape, classes_present
        else:
            # Upsample probability map to original size (bilinear)
            import cv2
            H, W = original_shape
            prob_map_upsampled = np.zeros((probs_np.shape[0], H, W), dtype=np.float32)
            for c in range(probs_np.shape[0]):
                prob_map_upsampled[c] = cv2.resize(probs_np[c], (W, H), interpolation=cv2.INTER_LINEAR)
            return mask_array, original_shape, classes_present, prob_map_upsampled
    
    def infer_batch(self, image_paths):
        """
        Run inference on multiple images.
        
        Args:
            image_paths (list): List of image paths
        
        Returns:
            results (list): List of (mask, shape, classes_present) tuples
        """
        results = []
        for image_path in image_paths:
            try:
                result = self.infer(image_path)
                results.append(result)
                print(f"✓ Processed: {Path(image_path).name}")
            except Exception as e:
                print(f"✗ Error processing {image_path}: {e}")
                results.append(None)
        
        return results
    
    def save_mask(self, mask, output_path):
        """
        Save segmentation mask as PNG.
        
        Args:
            mask (np.ndarray): Segmentation mask (H, W) with class IDs 0-12
            output_path (str or Path): Output PNG path
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert to PIL and save
        mask_pil = Image.fromarray(mask.astype(np.uint8))
        mask_pil.save(output_path)
        print(f"✓ Saved mask: {output_path}")


def main():
    """Test FPN inference."""
    # Paths
    model_path = Path("../U-NET/scripts/model_output/fpn_62images/best_model.pth")
    test_image = Path("../U-NET/data/floorplan/Capture d'écran 2025-06-05 224143.png")
    output_dir = Path("test_output")
    
    if not model_path.exists():
        print(f"Error: Model not found at {model_path}")
        print("Update model_path in main() to correct location")
        return
    
    if not test_image.exists():
        print(f"Error: Test image not found at {test_image}")
        print("Update test_image in main() to a valid floor plan image")
        return
    
    # Initialize
    fpn = FPNInference(model_path)
    
    # Run inference
    print(f"\nInferring on: {test_image.name}")
    mask, original_shape, classes_present = fpn.infer(test_image)
    
    print(f"✓ Original shape: {original_shape}")
    print(f"✓ Mask shape: {mask.shape}")
    print(f"✓ Classes detected:")
    for class_name, count in sorted(classes_present.items(), key=lambda x: x[1], reverse=True):
        print(f"  - {class_name}: {count} pixels")
    
    # Save mask
    output_dir.mkdir(exist_ok=True, parents=True)
    output_path = output_dir / "fpn_inference_mask.png"
    fpn.save_mask(mask, output_path)


if __name__ == "__main__":
    main()
