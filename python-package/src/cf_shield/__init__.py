"""
CF-Shield

A Python package for detecting DDoS attacks and enabling security measures 
on Cloudflare automatically by monitoring CPU usage.
"""

__version__ = "0.1.0"
__author__ = "Sakura-sx"
__email__ = "sakura@voxga.xyz"

from .main import run, main, setup

__all__ = ["run", "main", "setup"] 