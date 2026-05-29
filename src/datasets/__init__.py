"""Knowledge Dataset Engine — produção de datasets locais para IA."""

from src.datasets.dataset_engine import DatasetEngine, DatasetBuildResult, get_dataset_engine
from src.datasets.readiness import compute_knowledge_readiness_score
from src.datasets.registry.dataset_registry import DatasetRegistry, get_dataset_registry

__all__ = [
    "DatasetBuildResult",
    "DatasetEngine",
    "DatasetRegistry",
    "compute_knowledge_readiness_score",
    "get_dataset_engine",
    "get_dataset_registry",
]
