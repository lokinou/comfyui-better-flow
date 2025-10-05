from .common import any_type, c_Y, c_B, c_G, c_0, CACHE_DIR

class Wait:
    """
    Wait for all triggers to Useful for sequencing logic blocks.
    Note: forceInput=True ensures overrides laziness during execution
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "main": (any_type,),
                "trigger1": (any_type, {"forceInput": True, "lazy": True}),
                "trigger2": (any_type, {"forceInput": True, "lazy": True}),
                "trigger3": (any_type, {"forceInput": True, "lazy": True}),
            }
        }

    RETURN_TYPES = (any_type,)
    RETURN_NAMES = ("main_output",)
    FUNCTION = "forward"
    OUTPUT_NODE = False

    CATEGORY = "lnk/sequencing"

    def forward(self, main, trigger1=None, trigger2=None, trigger3=None):
        # All triggers are evaluated due to forceInput=True (if needed upstream),
        # but we return only the 'main' input as the meaningful output.
        return (main,)

    @staticmethod
    def check_lazy_status(main=None, trigger1=None, trigger2=None, trigger3=None):
        # Always force evaluation of all triggers if they are not yet computed
        needed = []
        if trigger1 is None:
            needed.append("trigger1")
        if trigger2 is None:
            needed.append("trigger2")
        if trigger3 is None:
            needed.append("trigger3")
        return needed
    
class WaitMulti:
    """
    Wait for all triggers to complete before passing through main input.
    Dynamically adds new trigger inputs as they are connected.
    Note: forceInput=True ensures overrides laziness during execution
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "main": (any_type,),
            },
            "optional": {
                "trigger1": (any_type, {"forceInput": True, "lazy": True}),
            },
            "hidden": {
                "extra_pnginfo": "EXTRA_PNGINFO",
                "unique_id": "UNIQUE_ID",
            }
        }

    @classmethod
    def INPUT_TYPES_WITH_NODE_ID(cls, node_id=None, extra_pnginfo=None):
        """
        This method is called when the node is being displayed/updated in the UI.
        We check how many triggers are connected and add one more slot.
        """
        inputs = {
            "required": {
                "main": (any_type,),
            },
            "optional": {}
        }
        
        # Default: always show at least trigger1
        num_triggers = 1
        
        # Check how many triggers are currently connected
        if extra_pnginfo is not None and "workflow" in extra_pnginfo:
            workflow = extra_pnginfo["workflow"]
            if "nodes" in workflow:
                for node in workflow["nodes"]:
                    if str(node.get("id")) == str(node_id):
                        if "inputs" in node:
                            # Count how many trigger inputs exist
                            trigger_count = 0
                            for inp in node["inputs"]:
                                if inp.get("name", "").startswith("trigger"):
                                    trigger_count += 1
                                    # Check if this input is connected
                                    if inp.get("link") is not None:
                                        num_triggers = max(num_triggers, trigger_count + 1)
                        break
        
        # Add trigger slots (always one more than connected)
        for i in range(1, num_triggers + 1):
            inputs["optional"][f"trigger{i}"] = (any_type, {"forceInput": True, "lazy": True})
        
        return inputs

    RETURN_TYPES = (any_type,)
    RETURN_NAMES = ("main_output",)
    FUNCTION = "forward"
    OUTPUT_NODE = False

    CATEGORY = "lnk/sequencing"

    def forward(self, main, **kwargs):
        # All triggers are evaluated due to forceInput=True (if needed upstream),
        # but we return only the 'main' input as the meaningful output.
        return (main,)

    @staticmethod
    def check_lazy_status(main=None, **kwargs):
        # Force evaluation of all triggers that are not yet computed
        needed = []
        for key, value in kwargs.items():
            if key.startswith("trigger") and value is None:
                needed.append(key)
        return needed

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return float("nan")