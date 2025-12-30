import comfy.model_management as mm
from comfy.model_patcher import ModelPatcher
from typing import Tuple, List, Union
from dataclasses import dataclass
import torch
import gc
import logging

try:
    from nunchaku import NunchakuFluxTransformer2dModel
    NUNCHAKU_AVAILABLE = True
except ImportError:
    NUNCHAKU_AVAILABLE = False
    NunchakuFluxTransformer2dModel = None

logger = logging.getLogger(__name__)

# Note: This doesn't work with reroute for some reason?
class AnyType(str):
    def __ne__(self, __value: object) -> bool:
        return False


@dataclass
class ModelInfo:
    classname: str
    device_current: Union[torch.device, int]
    device_target: Union[torch.device, int]
    device_offload: Union[torch.device, int]
    move_func: callable  # function to call to change the device


any = AnyType("*")

# Looking recursively for variable types to flag a non supported error
UNSUPPORTED_CHK = []

if NUNCHAKU_AVAILABLE:
    UNSUPPORTED_CHK.append(
        # each entry is a tuple describing what to check
        (
            ['model', 'diffusion_model', 'model'],  # variable names to check (first attribute model, then model.diffusion_model, then model.diffusion_model.model)
            "NunchakuFluxTransformer2dModel",  # unsupported class name to match
            "Nunchaku not supported (offloading directly managed in the binaries).\n"  #  error message 
            "solution: 1) Ignore errors or disable offloading for this node. 2) "
            "use the option to enable/disable automatic offloading directly the nunchaku loader."  # error resoltion message,
        ),
    )


device_options = ["auto","cpu"]
if torch.cuda.is_available():
    for i in range(torch.cuda.device_count()):
        # This creates user-friendly names like "cuda:0"
        device_name = torch.cuda.get_device_name(i)
        #device_options.append(f"cuda:{i} ({device_name})")  # People should know already their devices :)
        device_options.append(f"{torch.device(i)}")

class OffloadModel:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {"trigger_value": (any, )},
            "optional": {"model": (any, ),
                         "device": (device_options, {"default": "auto", "label": "Load Device", "tooltip": "Select the device to offload the model to."}),
                         "on_error": (["ignore", "raise"], {"default": "raise", "label": "On Error", "tooltip": "What to do on error: ignore or raise an exception."}),
                         "enable": ("BOOLEAN", {"default": True, "label": "Enable Offload", "tooltip": "Enable offloading of the model to the offload device."})                         
                         },
        }
    
    @classmethod
    def VALIDATE_INPUTS(s, **kwargs):
        return True
    
    RETURN_TYPES = (any, any)
    FUNCTION = "route"
    CATEGORY = "workflow"
    
    def route(self, **kwargs):
        logging.info("Offload Model (node)")
        model_candidate = kwargs.get("model")
        
        if not kwargs.get("enable", True):
            return (kwargs.get("trigger_value"), kwargs.get("model"),)

        # Check if the model is valid
        if not is_supported(model_candidate=model_candidate, on_error=kwargs.get("on_error", "raise"))[0]:
            return (kwargs.get("trigger_value"), kwargs.get("model"),)

        # get the device and function do move it between devices
        list_models = scan_for_models(top_model=model_candidate)
        for model in list_models:
            m_info: ModelInfo = get_model_info(model)
            cls = m_info.classname
            #preferred_device = m_info.device_target if m_info.device_target is not None else mm.get_torch_device()
            
            if kwargs.get("device", "auto") == "auto":
                offload_device = mm.unet_offload_device() if m_info.device_offload is not None else mm.unet_offload_device()
            else:
                # Use the requested device from parameters
                offload_device = torch.device(kwargs.get("device"))

            if torch.device(m_info.device_current) != torch.device(offload_device):

                if m_info.classname == "GGUFModelPatcher":
                    logging.info(f'- For GGUFModelPatcher {cls}, offloading  will move all patches to the offload device {torch.device(offload_device)}')
                    logger.info(f'- Changing the patch_on_device flag to False, overriding the default value from the gguf loader')
                    model.eject_model()  # eject the unet model to move it
                    model.unpatch_model()  # unpatch to avoid issues
                    model.model.to(torch.device(offload_device))
                else:

                    logging.info(f'- Offload {cls}: move from {torch.device(m_info.device_current)}'
                        f' to {torch.device(offload_device)}...')
                    m_info.move_func(torch.device(offload_device))
                    logging.info(f'- Offload {cls}: done')

            # Validate the migration
            m_info_post: ModelInfo = get_model_info(model)
            if torch.device(m_info_post.device_current) == torch.device(offload_device):
                logging.info(f'- Offload {cls}: validated')
                logging.debug('- Freeing VRAM...')
                gc.collect()
                mm.cleanup_models_gc()
                mm.soft_empty_cache()
                logging.debug('- cleanup done')
                # todo custom cleanup for known models? eg. flux transformer
                # model_size = mm.module_size(self.transformer)
                # do migration to offload device
                # mm.free_memory(model_size, device)
            else:
                logging.error(f'- Error for {cls}: Could not validate offloading, '
                      f'model is on {torch.device(m_info_post.device_current)} instead of {torch.device(offload_device)}')

        return (kwargs.get("trigger_value"), kwargs.get("model"),)
    
    
class RecallModel:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {"trigger_value": (any, )}, # For passthrough
            "optional": {"model": (any, ),
                         "device": (device_options, {"default": "auto", "label": "Load Device", "tooltip": "Select the device to recall the model to."}),
                         "on_error": (["ignore", "raise"], {"default": "raise", "label": "On Error", "tooltip": "What to do on error: ignore or raise an exception."}),
                         "enable": ("BOOLEAN", {"default": True, "label": "Enable Recall", "tooltip": "Enable recall of the model to the preferred device."}),
                         
                         },
        }
    
    @classmethod
    def VALIDATE_INPUTS(s, **kwargs):
        return True
    
    RETURN_TYPES = (any, any)
    FUNCTION = "route"
    CATEGORY = "workflow"

    def route(self, **kwargs):
        logging.info("Recall Model (node)")
        check_gc_for_dangling_clones(classname_to_check="GGUFModelPatcher")  # checking for dangling clones

        model_candidate = kwargs.get("model")
        cls = model_candidate.__class__.__name__
        if not kwargs.get("enable", True):
            return (kwargs.get("trigger_value"), kwargs.get("model"),)

        # Check if the model is valid
        
        if not is_supported(model_candidate=model_candidate, on_error=kwargs.get("on_error", "raise"))[0]:
            return (kwargs.get("trigger_value"), kwargs.get("model"),)
            

        # get the device and function do move it between devices
        list_models = scan_for_models(top_model=model_candidate)
        if len(list_models) > 0:
            logging.debug('- Freeing VRAM...')
            mm.soft_empty_cache()
            gc.collect()
            logging.debug('- done')
        for model in list_models:
            m_info: ModelInfo = get_model_info(model)
            
            if kwargs.get("device", "auto") == "auto":
                preferred_device = m_info.device_target if m_info.device_target is not None else mm.get_torch_device()
            else:
                # Use the requested device from parameters
                preferred_device = torch.device(kwargs.get("device"))
            #offload_device = mm.unet_offload_device() if m_info.device_offload is not None else mm.unet_offload_device()

            if torch.device(m_info.device_current) != torch.device(preferred_device):
                logging.info(f'- Recall {cls} from {torch.device(m_info.device_current)}'
                    f' to {torch.device(preferred_device)}...')
                if m_info.classname == "GGUFModelPatcher":
                    logging.info(f'- Overriding GGUFModelPatcher''s default behavior')
                    model.eject_model()  # eject the unet model to move it
                    model.unpatch_model()  # unpatch to avoid issues
                    model.model.to(torch.device(preferred_device))
                    model.patch_model()  # reapply patches
                if m_info.classname == "ModelPatcher":
                    logging.info(f'- Overriding ModelPatcher''s default behavior')
                    model.eject_model()  # eject the unet model to move it
                    model.unpatch_model()  # unpatch to avoid issues
                    model.model.to(torch.device(preferred_device))
                    model.patch_model()  # reapply patches

                else:

                    m_info.move_func(torch.device(preferred_device))
                    logging.info(f'- Recalling {cls} done')

            # Validate the migration
            m_info_post: ModelInfo = get_model_info(model)
            if torch.device(m_info_post.device_current) == torch.device(preferred_device):
                logging.info(f'- Recalling {cls} validated')
            else:
                logging.error(f'- Error for {cls}: Could not validate recall, '
                      f'model is on {torch.device(m_info_post.device_current)} instead of {torch.device(preferred_device)}')

        return (kwargs.get("trigger_value"), kwargs.get("model"),)
   
       

def is_supported(model_candidate, on_error: str = "raise") -> Tuple[bool, str]:
    """
    Return true if the model is known to be unsupported/problematic
    """
    # Eclude unsupported models first
    for nested_obj, class_name, err_msg in UNSUPPORTED_CHK:
        # Check for unsupported models
        if get_nested_class_name(obj=model_candidate, path=nested_obj) == class_name:
            err_str = f"Unsupported {model_candidate.__class__.__name__} model.\n {err_msg}"
            logging.error(f"- Error: {err_str}")
            if on_error == "raise":
                raise ValueError(err_str)
            else:
                return False, err_str
        


    # Then by default check for supported models
    if type(model_candidate) == ModelPatcher:
        logging.info(f"- model of type {model_candidate.__class__.__name__}")
        return True, ''
    elif issubclass(type(model_candidate), ModelPatcher):
        logging.info(f"- model of type {model_candidate.__class__.__name__}, a subclass of ModelPatcher, it might not be supported for Offload/recall")
        return True, ''
    elif hasattr(model_candidate, 'device') and hasattr(model_candidate, 'to'):
        logging.info(f"- Model of type {model_candidate.__class__.__name__} supported (contains 'model.device' and 'model.to()')")
        return True, ''
    elif hasattr(model_candidate, 'device') and hasattr(model_candidate, 'to'):
        logging.info(f"- Model of type {model_candidate.__class__.__name__} supported (contains 'model.device' and 'model.to()')")
        return True, ''  
    elif NUNCHAKU_AVAILABLE and issubclass(type(model_candidate), NunchakuFluxTransformer2dModel):
        logging.info(f"- model of type {model_candidate.__class__.__name__}, a subclass of ModelPatcher, it might not be supported for Offload/recall")
        return True, ''  
    
    else:

        # If no checks matched, log a warning   
        logging.warning(f"- Warning: No compatible device found for this model {model_candidate.__class__.__name__}.")
        return False, ''


def scan_for_models(top_model: object) -> List[object]:
    """
    Return supported models, and eventually embedded models
    Args:
        model: The model to check.
    Returns:
        List[object]: the current model if supported and any embedded one (e.g. ModelPatcher contains a model)
    """
    if type(top_model) == ModelPatcher or issubclass(type(top_model), ModelPatcher):
        #return [top_model, top_model.model]  # modelpatcher takes care of the relocation, accessing the nested model isn't going to solve anything
        return [top_model]
    elif hasattr(top_model, 'device') and hasattr(top_model, 'to'):
        return [top_model]
    else:
        return []
    

def get_nested_class_name(obj, path):
    for attr in path:
        obj = getattr(obj, attr, None)
        if obj is None:
            return None
    return getattr(obj.__class__, '__name__', None)


def get_model_info(model) -> ModelInfo:
    """
    Get info about the model and its devices
    Args:
        model: The model to check.
    Returns:
        ModelInfo: info summary about the devices

    """
    
    if type(model) == ModelPatcher or issubclass(type(model), ModelPatcher):
        # model patcher
        mp_info = ModelInfo(classname=type(model).__name__,
                       device_current=next(model.model.parameters()).device,
                       device_target=model.load_device,
                       device_offload=model.offload_device if hasattr(model, 'offload_device') else None,
                       move_func=model.model.to)
        return mp_info
    elif NUNCHAKU_AVAILABLE and type(model) == NunchakuFluxTransformer2dModel:
        # model patcher
        mp_info = ModelInfo(classname=type(model).__name__,
                       device_current=next(model.model.parameters()).device,
                       device_target=model.load_device,
                       device_offload=model.offload_device if hasattr(model, 'offload_device') else None,
                       move_func=model.model.to)
        return mp_info
    else:
        m_info = ModelInfo(classname=type(model).__name__,
                       device_current=model.device,
                       device_target=None,
                       device_offload=model.offload_device if hasattr(model, 'offload_device') else None,
                       move_func=model.to)
        return m_info
    

def check_gc_for_dangling_clones(classname_to_check = "GGUFModelPatcher") -> None:
    """
    Check for dangling clones in the garbage collector.
    This is useful to identify models that may not have been properly offloaded.
    """
    # --- START DEBUGGING CODE ---
    logging.info(f"Checking garbage collector for dangling clones of type {classname_to_check}...")
    gc.collect()  # Force a garbage collection run

    # Find all ModelPatcher objects the GC knows about
    type_instances = []
    for obj in gc.get_objects():
        if type(obj).__name__ ==  classname_to_check:
            type_instances.append(obj)

    logging.info(f"Found {len(type_instances)} {classname_to_check} instances in memory.")

    # If we have more than one, it's suspicious. Let's inspect them.
    if len(type_instances) > 1:
        logging.warning(f"Potential leak! Expected 1 {classname_to_check}, found {len(type_instances)}.")

        for i, patcher in enumerate(type_instances):
            logging.info(f"--- Instance {i} (id: {id(patcher)}) ---")

            # Get the list of objects referring to this patcher
            referrers = gc.get_referrers(patcher)
            logging.info(f"Found {len(referrers)} referrers.")

            # Try to print some useful info about the referrers
            for ref in referrers:
                # Avoid printing the huge list of all objects
                if isinstance(ref, list) and len(ref) > 100: 
                    logging.info(f"  -> Referenced by a large list (len: {len(ref)})")
                # Avoid printing massive dictionaries
                elif isinstance(ref, dict) and len(ref) > 100:
                    logging.info(f"  -> Referenced by a large dict (keys: {list(ref.keys())[:5]}...)")
                # This is the most common culprit!
                elif 'execution' in str(type(ref)):
                     logging.info(f"  -> CRITICAL: Referenced by an execution frame or cache: {type(ref)}")
                else:
                    # Print a snippet of the referrer
                    logging.info(f"  -> Referenced by: {str(ref)[:150]}")

    logging.info("!!! FINISHED CLONE CHECK !!!")
    # --- END DEBUGGING CODE ---