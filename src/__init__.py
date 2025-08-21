"""AZ-Ray: Azure V2Ray Proxy Solution"""

from .main import main, AzRayApp
from .config import Config
from .azure_manager import AzureManager
from .v2ray_manager import V2RayManager
from .health_monitor import HealthMonitor

__version__ = "1.0.0"
__author__ = "AZ-Ray Development Team"

__all__ = [
    "main",
    "AzRayApp", 
    "Config",
    "AzureManager",
    "V2RayManager", 
    "HealthMonitor"
]
