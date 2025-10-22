from .offload_recall import OffloadModel, RecallModel
from .cache_any import CacheAny
from .md5_hash import AnyToHash, AnyToHashMulti
from .wait import Wait, WaitMulti
from .reroute_triggerable import RerouteTriggerable

# Blind ComfyUI needs to be told where to look for js code
WEB_DIRECTORY = "./js"

# A dictionary that contains all nodes you want to export with their names
# NOTE: names should be globally unique
NODE_CLASS_MAPPINGS = {
    "OffloadModelv2": OffloadModel,
    "RecallModelv2": RecallModel,
    "CacheAny": CacheAny,
    "AnyToHash": AnyToHash,
    "AnyToHashMulti": AnyToHashMulti,
    "Wait": Wait,
    "WaitMulti": WaitMulti,
    "RerouteTriggerable": RerouteTriggerable
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "OffloadModelv2": "Model Offload",
    "RecallModelv2": "Model Recall",
    "CacheAny": "Cache any",
    "AnyToHash" : "any to hash",
    "AnyToHashMulti" : "any to hash x2",
    "Wait": "Wait",
    "WaitMulti": "Wait xN",
    "RerouteTriggerable": "Reroute Triggerable"
}

__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS', 'WEB_DIRECTORY']