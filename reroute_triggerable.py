# Our any instance wants to be a wildcard string


class AnyType(str):
    """A special type that can be connected to any other types. Credit to pythongosssss"""

    def __ne__(self, __value: object) -> bool:
        return False

any_type = AnyType("*")

class RerouteTriggerable:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {"value": (any_type, )},
        }

    @classmethod
    def VALIDATE_INPUTS(s, **kwargs):
        return True

    RETURN_TYPES = (any_type,)
    FUNCTION = "route_triggerable"
    CATEGORY = "workflow"

    def route_triggerable(self, value, **kwargs):
        return (value,)