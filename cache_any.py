import pickle
import hashlib
from pathlib import Path
import os
import re
from .common import any_type, c_R, c_Y, c_B, c_G, c_P, c_0, CACHE_DIR, get_cache_path
import numpy as np


CLASS_STR = f"{c_B}CacheAny{c_0}"

class CacheAny:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "any_to_cache": (any_type, {"lazy": True}),
                "any_key": (any_type, ),
                "cache_name": ("STRING", {"default": "output"}),
                "cleanup_on_mismatch": ("BOOLEAN", {"default": True}),
                "force_recreate": ("BOOLEAN", {"default": False}),
            },
        }

    # MODIFIED: Added IMAGE passthrough
    RETURN_TYPES = (any_type, any_type,)
    RETURN_NAMES = ("any_cached", "key_passthrough",)
    FUNCTION = "run_caching"
    CATEGORY = "LNK"

    @classmethod
    def IS_CHANGED(cls, any_to_cache, any_key, cache_name, force_recreate, *args, **kwargs):
        if force_recreate:
            return float("NaN")
        cache_path = get_cache_path(any_key, cache_name, ignore_errors=True)
        if cache_path is None or not cache_path.exists():
            return float("NaN")
        print(f"{CLASS_STR}-{cache_name} is_changed={cache_path}")
        return str(cache_path)

    @classmethod
    def check_lazy_status(cls, any_to_cache, any_key, cache_name, force_recreate, *args, **kwargs):
        if any_key is None:
            print(f"{CLASS_STR}-{cache_name} {c_R}Error, the any_key input is required but given as None.{c_0}")
        cache_path = get_cache_path(any_key, cache_name)   
        if cache_path.exists() and not force_recreate:
            print(f"{CLASS_STR}-{cache_name} check_lazy_status {c_G}discards evaluation{c_0} of any_to_cache input.")
            return None
        print(f"{CLASS_STR}-{cache_name} check_lazy_status {c_Y}requests evaluation{c_0} of any_to_cache input.")
        return ["any_to_cache"]

    @classmethod
    def run_caching(cls, any_to_cache, any_key, cache_name, cleanup_on_mismatch, force_recreate, *args, **kwargs):
        if any_key is None:
            raise TypeError(f"Nonetype error for any_key input")
        if cache_name is None:
            raise TypeError(f"Nonetype error for cache_name input")
        if not isinstance(cache_name, str):
            raise TypeError(f"any_key must be a string, got {type(cache_name)} instead")
        if len(cache_name) == 0:
            raise ValueError(f"cache_name must be at least 1 character")
        if cache_name.find("+") >= 0:
            raise ValueError(f"Please do not use the character '+' in they cache_name={cache_name}")
        
        os.makedirs(CACHE_DIR, exist_ok=True)
        cache_path = get_cache_path(any_key, cache_name, verbose=True)

        current_hash = re.match(rf'{re.escape(cache_name)}+([a-fA-F0-9]{{32}})\.pkl$',str(cache_path))
        parent_folder = cache_path.parent
        if cleanup_on_mismatch:
            # Search for other files with same key but different hash
            other_versions = []
            for file in parent_folder.glob(f"{cache_name}+*.pkl"):
                file_match = re.match(rf"{re.escape(cache_name)}+([a-fA-F0-9]{{32}})\.pkl", file.name)
                if file_match:
                    file_hash = file_match.group(1)
                    if file_hash != current_hash:
                        other_versions.append(file)
            print(f"Found {len(other_versions)} other cache files with the same key, cleaning up...")
            for fn in other_versions:
                os.remove(fn)

        if cache_path.exists() and not force_recreate:
            with open(cache_path, 'rb') as f:
                cached_data = pickle.load(f)
            # Passthrough inputs
            return (cached_data, any_key,)

        with open(cache_path, 'wb') as f:
            pickle.dump(any_to_cache, f)



        
        # Passthrough inputs
        return (any_to_cache, any_key,)