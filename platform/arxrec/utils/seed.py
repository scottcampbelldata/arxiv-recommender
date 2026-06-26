"""Deterministic seeding for numpy, random, and torch."""

from __future__ import annotations

import os
import random

import numpy as np

try:
    import torch
    _TORCH = torch
except ImportError:
    _TORCH = None


def seed_all(seed: int) -> None:
    os.environ["PYTHONHASHSEED"] = str(seed)
    random.seed(seed)
    np.random.seed(seed)
    if _TORCH is not None:
        _TORCH.manual_seed(seed)
        if _TORCH.cuda.is_available():
            _TORCH.cuda.manual_seed_all(seed)
