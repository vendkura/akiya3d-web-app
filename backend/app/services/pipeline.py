"""
Pipeline Service - Wraps the 3D pipeline v5 (Dollhouse Style) for API use
Uses: main_pipeline_v5.py components for proper wall-based extrusion
"""
import sys
import asyncio
import base64
import time
from pathlib import Path
from typing import AsyncGenerator, Optional
import numpy as np
import cv2
from PIL import Image
import io

from app.config import settings
from app.utils.sse import (
    create_step_event, 
    create_result_event, 
    create_error_event,
    StepStatus
)


class PipelineService:
    """
    Service class that orchestrates the 2D->3D conversion pipeline v5.
    Yields SSE events for real-time progress updates.
    Sends keepalive events during long CPU-bound operations to prevent proxy timeouts.
    """
    
    def __init__(self):
        self.fpn_model = None
        self.device = None
        self._initialized = False
        self._initializing = False  # Prevent concurrent init
        
        # Pipeline v5 parameters
        self.postprocess_min_area = 2000
        self.enable_rectangular_fitting = True
        self.min_rectangle_coverage = 0.70
        self.wall_thickness = 0.12  # 12cm
        self.wall_height = 2.5  # 2.5m
        self.min_wall_length = 0.3  # Filter walls shorter than 30cm
    
    async def initialize(self):
        """Lazy initialization of the model (heavy operation)"""
        if self._initialized:
            return
        
        if self._initializing:
            # Another request is already initializing, wait for it
            while self._initializing:
                await asyncio.sleep(0.5)
            return
        
        self._initializing = True
        
        try:
            print(f"🔧 Initializing pipeline v5...")
            print(f"📍 Model path: {settings.model_weights_path}")
            print(f"📍 Model exists: {settings.model_weights_path.exists()}")
            
            # Check if model weights exist
            if not settings.model_weights_path.exists():
                print("❌ Model weights not found! Attempting download...")
                try:
                    from app.download_model import download_model_weights
                    success = download_model_weights()
                    if not success:
                        raise FileNotFoundError(f"Model weights not found: {settings.model_weights_path}")
                except Exception as e:
                    raise FileNotFoundError(f"Failed to download model weights: {e}")
            
            # Import pipeline modules
            try:
                from app.services.fpn_inference import FPNInference
                print("✅ Pipeline modules imported successfully")
            except ImportError as e:
                raise ImportError(f"Failed to import pipeline modules: {e}")
            
            self.device = settings.get_device()
            print(f"🖥️ Initializing on device: {self.device}")
            
            # Load model in thread pool so we don't block the event loop
            # (FPNInference.__init__ does torch.load + model.to() which is heavy)
            try:
                loop = asyncio.get_event_loop()
                self.fpn_model = await loop.run_in_executor(
                    None,
                    lambda: FPNInference(
                        model_path=str(settings.model_weights_path),
                        device=self.device
                    )
                )
                print("✅ FPN model loaded successfully")
            except Exception as e:
                raise RuntimeError(f"Failed to load FPN model: {e}")
            
            self._initialized = True
            print("🎉 Pipeline initialized successfully!")
        finally:
            self._initializing = False
    
    def _mask_to_preview_base64(self, mask: np.ndarray) -> str:
        """Convert segmentation mask to colored preview image (base64)"""
        COLORS = [
            [255, 179, 186],  # dining_area - pink
            [186, 255, 201],  # bathroom - mint
            [186, 225, 255],  # bedroom - light blue
            [255, 255, 186],  # closet - light yellow
            [223, 186, 255],  # room - lavender
            [139, 69, 19],    # door - brown
            [255, 165, 0],    # entrance - orange
            [255, 105, 180],  # kitchen - hot pink
            [144, 238, 144],  # outdoor_space - light green
            [165, 42, 42],    # sliding_door - dark brown
            [128, 128, 128],  # stairs - gray
            [0, 191, 255],    # window - deep sky blue
            [152, 251, 152],  # balcony - pale green
        ]
        
        h, w = mask.shape
        colored = np.zeros((h, w, 3), dtype=np.uint8)
        
        for class_id, color in enumerate(COLORS):
            colored[mask == class_id] = color
        
        _, buffer = cv2.imencode('.png', cv2.cvtColor(colored, cv2.COLOR_RGB2BGR))
        return base64.b64encode(buffer).decode('utf-8')
    
    def _boundaries_to_preview_base64(self, mask: np.ndarray, rooms: list) -> str:
        """Create a preview showing detected room boundaries"""
        h, w = mask.shape
        preview = np.zeros((h, w, 3), dtype=np.uint8)
        
        for room in rooms:
            vertices = np.array(room['vertices'], dtype=np.int32)
            color = room.get('color', [200, 200, 200])
            cv2.fillPoly(preview, [vertices], color)
            cv2.polylines(preview, [vertices], True, (255, 255, 255), 2)
        
        _, buffer = cv2.imencode('.png', preview)
        return base64.b64encode(buffer).decode('utf-8')
    
    async def _run_with_keepalive(self, executor_func, *args, step_name="processing"):
        """
        Run a CPU-bound function in thread pool while yielding keepalive events.
        This prevents Render's proxy from timing out during long operations.
        
        Returns: (result, list_of_keepalive_events)
        """
        loop = asyncio.get_event_loop()
        keepalive_events = []
        
        # Create a future for the CPU-bound work
        future = loop.run_in_executor(None, executor_func, *args)
        
        start_time = time.time()
        while not future.done():
            await asyncio.sleep(3)  # Check every 3 seconds
            if not future.done():
                elapsed = int(time.time() - start_time)
                keepalive_events.append(create_step_event(
                    step_name,
                    StepStatus.RUNNING,
                    progress=min(90, elapsed * 3),  # Rough progress estimate
                    message=f"Processing... ({elapsed}s)"
                ))
        
        result = future.result()
        return result, keepalive_events
    
    async def process_image(
        self, 
        image_path: Path, 
        job_id: str,
        output_dir: Path
    ) -> AsyncGenerator[dict, None]:
        """
        Process a floorplan image through the full pipeline v5.
        Yields SSE events for each step, with keepalive during long operations.
        """
        try:
            print(f"🚀 Starting processing for job: {job_id}")
            print(f"📁 Image path: {image_path}")
            print(f"📁 Output dir: {output_dir}")
            
            # ========== INITIALIZATION ==========
            if not self._initialized:
                yield create_step_event(
                    "init",
                    StepStatus.RUNNING,
                    progress=0,
                    message="Loading AI model (first request may take a moment)..."
                )
                
                await self.initialize()
                
                yield create_step_event(
                    "init",
                    StepStatus.COMPLETED,
                    progress=100,
                    message="Model loaded successfully"
                )
            
            print("✅ Pipeline ready for processing")
            
            # Import pipeline v5 modules
            from app.services.segmentation_postprocess import SegmentationPostProcessor
            from app.services.rectangular_room_fitter import RectangularRoomFitter
            from app.services.wall_based_extrusion import WallDetector, WallBasedExtruder, WallOBJExporter
            print("✅ Pipeline modules imported for processing")
            
            loop = asyncio.get_event_loop()
            
            # ========== STEP 1: SEGMENTATION ==========
            yield create_step_event(
                "segmentation", 
                StepStatus.RUNNING, 
                progress=0,
                message="Running FPN inference..."
            )
            
            # Run inference with keepalive to prevent timeout
            (raw_mask, original_shape, classes_present), keepalives = await self._run_with_keepalive(
                self.fpn_model.infer,
                str(image_path),
                step_name="segmentation"
            )
            
            # Yield any keepalive events that were generated
            for event in keepalives:
                yield event
            
            # Generate preview
            mask_preview = self._mask_to_preview_base64(raw_mask)
            
            # Save raw mask
            raw_mask_path = output_dir / f"{job_id}_mask_raw.png"
            cv2.imwrite(str(raw_mask_path), raw_mask)
            
            yield create_step_event(
                "segmentation",
                StepStatus.COMPLETED,
                progress=100,
                message=f"Detected {len(classes_present)} room types",
                data={
                    "preview": f"data:image/png;base64,{mask_preview}",
                    "classes": classes_present,
                    "shape": list(original_shape)
                }
            )
            
            # ========== STEP 2: POST-PROCESSING ==========
            yield create_step_event(
                "postprocess",
                StepStatus.RUNNING,
                progress=0,
                message="Cleaning up segmentation mask..."
            )
            
            postprocessor = SegmentationPostProcessor(
                min_region_area=self.postprocess_min_area,
                enable_straightening=True
            )
            clean_mask = await loop.run_in_executor(None, postprocessor.process, raw_mask)
            
            clean_mask_path = output_dir / f"{job_id}_mask_clean.png"
            cv2.imwrite(str(clean_mask_path), clean_mask)
            
            yield create_step_event(
                "postprocess",
                StepStatus.COMPLETED,
                progress=100,
                message=f"Removed {postprocessor.stats['regions_removed']} noise regions",
                data={
                    "regions_removed": postprocessor.stats["regions_removed"],
                    "pixels_changed": postprocessor.stats["pixels_changed"]
                }
            )
            
            # ========== STEP 3: RECTANGULAR FITTING ==========
            yield create_step_event(
                "fitting",
                StepStatus.RUNNING,
                progress=0,
                message="Fitting rectangular rooms..."
            )
            
            if self.enable_rectangular_fitting:
                fitter = RectangularRoomFitter(
                    min_rectangle_coverage=self.min_rectangle_coverage,
                    enable_lshape=True
                )
                final_mask = await loop.run_in_executor(None, fitter.fit_mask, clean_mask)
                summary = fitter.get_summary()
                
                rect_mask_path = output_dir / f"{job_id}_mask_rectangular.png"
                cv2.imwrite(str(rect_mask_path), final_mask)
                
                yield create_step_event(
                    "fitting",
                    StepStatus.COMPLETED,
                    progress=100,
                    message=f"Fitted {summary['stats']['rectangle_fits']} rectangles, {summary['stats']['lshape_fits']} L-shapes",
                    data=summary["stats"]
                )
            else:
                final_mask = clean_mask
                yield create_step_event(
                    "fitting",
                    StepStatus.COMPLETED,
                    progress=100,
                    message="Rectangular fitting skipped"
                )
            
            # Save final mask
            mask_path = output_dir / f"{job_id}_mask.png"
            cv2.imwrite(str(mask_path), final_mask)
            
            # ========== STEP 4: CALCULATE SCALE ==========
            non_zero = np.argwhere(final_mask > 0)
            if len(non_zero) > 0:
                min_y, min_x = non_zero.min(axis=0)
                max_y, max_x = non_zero.max(axis=0)
                width_px = max_x - min_x
                scale_factor = 12.0 / width_px if width_px > 0 else 0.01
            else:
                scale_factor = 0.01
            
            # ========== STEP 5: WALL DETECTION & EXTRUSION ==========
            yield create_step_event(
                "extrusion",
                StepStatus.RUNNING,
                progress=0,
                message="Detecting walls and generating 3D geometry..."
            )
            
            detector = WallDetector(
                wall_thickness=self.wall_thickness,
                min_wall_length=self.min_wall_length
            )
            walls = await loop.run_in_executor(
                None, detector.detect_from_mask, final_mask, scale_factor
            )
            
            extruder = WallBasedExtruder(
                wall_thickness=self.wall_thickness,
                wall_height=self.wall_height
            )
            await loop.run_in_executor(None, extruder.extrude_walls, walls)
            await loop.run_in_executor(None, extruder.add_colored_floor, final_mask, scale_factor)
            
            geometry = extruder.get_geometry()
            bounds = extruder.get_bounds()
            
            stats = {
                "num_walls": len(walls),
                "num_vertices": len(geometry["vertices"]),
                "num_faces": len(geometry["faces"]),
                "bounds": bounds,
                "scale_factor": scale_factor
            }
            
            yield create_step_event(
                "extrusion",
                StepStatus.COMPLETED,
                progress=100,
                message=f"Generated {len(walls)} walls, {len(geometry['vertices'])} vertices",
                data={"stats": stats}
            )
            
            # ========== STEP 6: EXPORT ==========
            yield create_step_event(
                "export",
                StepStatus.RUNNING,
                progress=0,
                message="Exporting OBJ and MTL files..."
            )
            
            exporter = WallOBJExporter()
            exporter.load_geometry(geometry)
            
            obj_path = output_dir / f"{job_id}.obj"
            mtl_path = output_dir / f"{job_id}.mtl"
            
            await loop.run_in_executor(None, exporter.export_obj, str(obj_path), f"{job_id}.mtl")
            await loop.run_in_executor(None, exporter.export_mtl, str(mtl_path))
            
            yield create_step_event(
                "export",
                StepStatus.COMPLETED,
                progress=100,
                message="Files exported successfully"
            )
            
            # ========== FINAL RESULT ==========
            yield create_result_event(
                success=True,
                job_id=job_id,
                obj_url=f"/api/v1/download/{job_id}/{job_id}.obj",
                mtl_url=f"/api/v1/download/{job_id}/{job_id}.mtl",
                mask_url=f"/api/v1/download/{job_id}/{job_id}_mask.png",
                boundaries_url=f"/api/v1/download/{job_id}/{job_id}_boundaries.json",
                stats=stats
            )
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            yield create_error_event(job_id, str(e))


# Global service instance (singleton pattern)
pipeline_service = PipelineService()