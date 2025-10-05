import folder_paths
from pathlib import Path
import pickle
import hashlib
import os
import torch

# Contains common utilities and constants used by multiple nodes.

CACHE_DIR = Path(folder_paths.output_directory) / "cached_outputs"


class AlwaysEqualProxy(str):
    def __eq__(self, _):
        return True

    def __ne__(self, _):
        return False

# to accept any type of input and always consider it unchanged
any_type = AlwaysEqualProxy("*")


# Color codes for terminal output
c_R = "\033[31m"
c_G = "\033[32m"
c_Y = "\033[33m"
c_B = "\033[34m"
c_P = "\033[35m"
c_0 = "\033[0m"

def _to_bytes(obj):
    '''
    Convert to bytes, using Pickle and solving Tensor variability issues.
    No deep search for Tensor variables in obj
    '''
    if isinstance(obj, torch.Tensor):
        return obj.cpu().numpy().tobytes()
    else:
        return pickle.dumps(obj, protocol=pickle.HIGHEST_PROTOCOL)
    
def get_hash_from_any(any):
    obj_bytes = _to_bytes(any)
    return hashlib.md5(obj_bytes).hexdigest()

def get_hash_from_list_any(list_of_any):
    if not isinstance(list_of_any, list):
        raise TypeError(f'list_of_any should be a list, got {type(list_of_any)}')
    # directly hash each item in the list  individually to prevent manipulating massive blobs of data
    list_obj_bytes = [get_hash_from_any(item) for item in list_of_any]
    # re-hash the list
    return get_hash_from_any(list_obj_bytes)


def get_cache_path(any_key, cache_name, verbose=False) -> Path:

    if isinstance(any_key, list):
        valid_keys = [item for item in any_key if item is not None]
        if len(valid_keys) < len(any_key):
            return ValueError(f'Found a None value in the list of input keys, Cache name={cache_name}')
        md5_hash = get_hash_from_list_any(any_key)
    else:
        if any_key is None:
            return ValueError(f'Cannot provide a cache file for an input key=None. Cache name={cache_name}')
        md5_hash = get_hash_from_any(any_key)

    # compose the file name from the cache name and the md5 hash
    filename = f"{cache_name}+{md5_hash}.pkl"
    filepath = Path(CACHE_DIR) / filename
    if verbose:
        print(f"cache+md5={filename}")
    return filepath
