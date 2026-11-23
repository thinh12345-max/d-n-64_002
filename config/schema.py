"""Configuration schema with validation using Pydantic."""
from typing import List, Dict, Optional
from pathlib import Path
from pydantic import BaseModel, Field, validator
import yaml


class ProjectConfig(BaseModel):
    name: str = "traffic_ai"
    version: str = "1.0"


class ModelConfig(BaseModel):
    path: str
    imgsz: int = Field(gt=0)
    confidence: float = Field(ge=0.0, le=1.0)
    iou: float = Field(ge=0.0, le=1.0)
    device: str = "auto"

    @validator("path")
    def validate_model_path(cls, v):
        path = Path(v)
        if not path.exists():
            raise ValueError(f"Model file not found: {path}")
        return v


class VideoConfig(BaseModel):
    source: str
    output: str
    frame_size: List[int] = Field(min_items=2, max_items=2)
    frame_skip: int = Field(ge=0)

    @validator("source")
    def validate_video_source(cls, v):
        path = Path(v)
        if not path.exists():
            raise ValueError(f"Video file not found: {path}")
        return v


class TrackerConfig(BaseModel):
    type: str = "bytetrack"
    config: Dict = Field(default_factory=dict)

    @validator("config")
    def validate_tracker_config(cls, v):
        if "stale_frames" in v:
            if not isinstance(v["stale_frames"], int) or v["stale_frames"] <= 0:
                raise ValueError("stale_frames must be a positive integer")
        return v


class ROIConfig(BaseModel):
    enabled: bool = True
    points: List[List[int]] = Field(min_items=3)

    @validator("points")
    def validate_roi_points(cls, v):
        for point in v:
            if len(point) != 2 or not all(isinstance(c, int) for c in point):
                raise ValueError(f"Each ROI point must be [x, y] with integer coordinates, got {point}")
        return v


class CountingConfig(BaseModel):
    countable_labels: List[str] = Field(min_items=1)
    min_confidence: float = Field(ge=0.0, le=1.0)
    min_box_size: int = Field(gt=0)


class OutputConfig(BaseModel):
    directory: str
    save_json: bool = True
    json_filename: str = "vehicle_counts.json"
    save_video: bool = False
    video_filename: str = "output_video.mp4"
    video_fps: int = Field(gt=0)


class VisualizationConfig(BaseModel):
    show_window: bool = True
    window_name: str = "AI Counting"
    roi_color: List[int] = Field(default=[0, 0, 255], min_items=3, max_items=3)
    roi_thickness: int = Field(gt=0)
    outside_roi_color: List[int] = Field(default=[128, 128, 128], min_items=3, max_items=3)
    class_colors: Dict[str, List[int]] = Field(default_factory=dict)


class LoggingConfig(BaseModel):
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    @validator("level")
    def validate_level(cls, v):
        valid = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid:
            raise ValueError(f"Log level must be one of {valid}")
        return v.upper()


class SeedsConfig(BaseModel):
    random: int
    numpy: int
    torch: int
    torch_cuda: int
    cudnn_deterministic: bool
    cudnn_benchmark: bool


class Config(BaseModel):
    project: ProjectConfig
    model: ModelConfig
    video: VideoConfig
    tracker: TrackerConfig
    roi: ROIConfig
    counting: CountingConfig
    output: OutputConfig
    visualization: VisualizationConfig
    logging: LoggingConfig
    seeds: SeedsConfig


def load_config(config_path: str = "config/config.yaml") -> Config:
    """Load and validate configuration from YAML file."""
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    return Config(**data)