from .common import any_type
import pickle
import hashlib
import torch
from .common import _to_bytes

class AnyToHash:
    @classmethod
    def INPUT_TYPES(s):
        return {"required": {"anything": (any_type, {}), },"optional": {}, 
                "hidden": {"unique_id": "UNIQUE_ID", "extra_pnginfo": "EXTRA_PNGINFO",
                           }}

    RETURN_TYPES = (any_type,)
    RETURN_NAMES = ('string',)
    OUTPUT_NODE = True
    FUNCTION = "to_md5_hash"
    CATEGORY = "LNK"

    def to_md5_hash(self, anything, unique_id=None, extra_pnginfo=None, **kwargs):
        if anything is None:
            raise ValueError('AnyToHash received a None input')
        str_hash = []
        try:
            object_bytes = _to_bytes(anything)
            # hash it with md5
            md5_hash = hashlib.md5(object_bytes).hexdigest()
            str_hash = str(md5_hash)
        except Exception as e:
            print("AnyToHash: -Warning- encountered could not hash the input, returned a str")
            str_hash = str(e)
                    

        if not extra_pnginfo:
            pass
        elif (not isinstance(extra_pnginfo, dict) or "workflow" not in extra_pnginfo):
            pass
        else:
            workflow = extra_pnginfo["workflow"]
            node = next((x for x in workflow["nodes"] if str(x["id"]) == unique_id), None)
            if node:
                node["widgets_values"] = str_hash
        return (str_hash,)

class AnyToHashMulti:
    @classmethod
    def INPUT_TYPES(s):
        return {"required": {"anything1": (any_type, {}), 
                             "anything2": (any_type, {}), }, 
                "hidden": {"unique_id": "UNIQUE_ID", "extra_pnginfo": "EXTRA_PNGINFO",
                           }}

    RETURN_TYPES = (any_type,)
    RETURN_NAMES = ('string',)
    OUTPUT_NODE = True
    FUNCTION = "to_md5_hash_mult"
    CATEGORY = "LNK"

    def to_md5_hash_mult(self, anything1, anything2, unique_id=None, extra_pnginfo=None, **kwargs):
        if anything1 is None or anything2 is None:
            raise ValueError('AnyToHash received a None input')
        str_hash = []
        try:
            # serialize the key to bytes for hashing
            object_bytes = pickle.dumps([_to_bytes(anything1), 
                                         _to_bytes(anything2)], protocol=pickle.HIGHEST_PROTOCOL)
            # hash it with md5
            md5_hash = hashlib.md5(object_bytes).hexdigest()
            str_hash = str(md5_hash)
        except Exception as e:
            print("AnyToHash: -Warning- encountered could not hash the input, returned a str")
            str_hash = str(e)
                    

        if not extra_pnginfo:
            pass
        elif (not isinstance(extra_pnginfo, dict) or "workflow" not in extra_pnginfo):
            pass
        else:
            workflow = extra_pnginfo["workflow"]
            node = next((x for x in workflow["nodes"] if str(x["id"]) == unique_id), None)
            if node:
                node["widgets_values"] = str_hash
        return (str_hash,)