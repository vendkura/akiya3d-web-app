"""
Server-Sent Events (SSE) utilities for streaming pipeline progress
"""
import json
from typing import Any, AsyncGenerator
from dataclasses import dataclass, asdict
from enum import Enum


class StepStatus(str, Enum):
    """Status of a pipeline step"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class PipelineStep:
    """Represents a single step in the pipeline"""
    name: str
    status: StepStatus
    progress: int = 0  # 0-100
    message: str = ""
    data: dict = None  # Additional data (preview URLs, stats, etc.)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for SSE"""
        payload = {
            "name": self.name,
            "status": self.status.value,
            "progress": self.progress,
            "message": self.message,
        }
        if self.data:
            payload["data"] = self.data
        return payload


@dataclass  
class PipelineResult:
    """Final result of the pipeline"""
    success: bool
    job_id: str
    obj_url: str = None
    mtl_url: str = None
    mask_url: str = None
    boundaries_url: str = None
    stats: dict = None
    error: str = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary for SSE"""
        return asdict(self)


# Pipeline step definitions
PIPELINE_STEPS = [
    {"name": "upload", "label": "Uploading image", "duration_estimate": 0.5},
    {"name": "segmentation", "label": "Running segmentation", "duration_estimate": 2.0},
    {"name": "boundary", "label": "Extracting boundaries", "duration_estimate": 0.5},
    {"name": "extrusion", "label": "Generating 3D model", "duration_estimate": 1.0},
    {"name": "export", "label": "Exporting files", "duration_estimate": 0.3},
]


def create_step_event(
    step_name: str,
    status: StepStatus,
    progress: int = 0,
    message: str = "",
    data: dict = None
) -> dict:
    """Create an SSE event for a pipeline step"""
    step = PipelineStep(
        name=step_name,
        status=status,
        progress=progress,
        message=message,
        data=data
    )
    return step.to_dict()


def create_result_event(
    success: bool,
    job_id: str,
    **kwargs
) -> dict:
    """Create an SSE event for the final result"""
    result = PipelineResult(
        success=success,
        job_id=job_id,
        **kwargs
    )
    return result.to_dict()


def create_error_event(job_id: str, error_message: str) -> dict:
    """Create an SSE event for an error"""
    return create_result_event(
        success=False,
        job_id=job_id,
        error=error_message
    )
