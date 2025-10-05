# comfyui-better-flow 

Nodes for controlling workflow and reducing VRAM fingerprint.
All assembled for ComfyUI for the goal of making workflows easier and spare computing space. 

***TODO: untested release***

***TODO: add image use cases for each custom node***

## Custom Nodes

### Model offload/ Model recall

Manually offload and reload models between devices (cpu, cuda ...).
Helps greatly to reduce VRAM usage in complex workflows

Works with gguf models and .safetensor models.
Nunchaku is unsupported/ignored since it mangages its own VRAM usage outside python.

###  Any to Hash
returns a md5 hash for the input object.
Limitations:
- doesn't support None inputs
- Inconsistent with objects of type Tensor: Those can be located on RAM or VRAM, hence returning different values. In the case of an image, we migrate the image to CPU before calculating the Hash

###  Any to Hash x2
Same as any to Hash but combines two individual hashes.
It re-hashes the concatenation of the md5 hash of each input

###  Cache any
saves the input to cache into a .pkl file, referenced with 
- a key name
- a hash calculated by its input
During the next execution, if a matching key+hash is found in cache, it will Skips the heavy computing and return the pickled value instead.

Multiple inputs keys can be used when combined with "any to hash x2" (for example 2 images + 1 prompt)

###  Wait
Stops the execution of the workflow until the trigger value has been executed. Due to lazy loading, this specific  node is deprioritized.

### Wait Multi (experimental)
Wait multiple triggers at once, the node dynamically adds new inputs for each new input connected

### Reroute Triggerable
Reroute that can be triggered using the advanced Mode>OnTrigger UI elements. For advanced 

## Install

### Via ComfyUI

Search for "comfyui-better-flow" in the available node, or paste the github repo link to install from it. 

### Manual Install
```sh
# Go to the custom nodes
cd ./ComfyUI/custom_nodes
# Install the repo
git clone https://github.com/lokinou/comfyui-better-flow.git
```

## versions

- 0.1.1
    - bug fixes
- 0.1.0
    - initial release from all node
    - migrated here ([comfyui-offload-models 1.1.0](https://github.com/lokinou/comfyui-offload-models))