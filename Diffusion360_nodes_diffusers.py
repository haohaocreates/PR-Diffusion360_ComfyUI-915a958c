import torch
import folder_paths
import os
from .txt2panoimg import Text2360PanoramaImagePipeline
from .img2panoimg import Image2360PanoramaImagePipeline
import numpy as np
from diffusers.utils import load_image
import node_helpers
from PIL import Image, ImageOps, ImageSequence


class InputText:
    @classmethod
    def INPUT_TYPES(s):
        return {"required": {"text": ("STRING", {"multiline": True, "dynamicPrompts": True})}}
    RETURN_TYPES = ("CONDITIONING",)
    FUNCTION = "text"

    CATEGORY = "Diffusion360/diffusers"

    def text(self, text):
        return (text, )


class InputImage:
    @classmethod
    def INPUT_TYPES(s):
        files = ["i2p-image.jpg"]
        return {"required":
                    {"image": (sorted(files), {"image_upload": True})},
                }

    CATEGORY = "Diffusion360/diffusers"

    RETURN_TYPES = ("IMAGE", )
    FUNCTION = "load_image"

    def load_image(self, image):
        image_path = os.path.join('custom_nodes/Diffusion360_ComfyUI/data/', image)
        img = node_helpers.pillow(Image.open, image_path)

        output_images = []
        w, h = None, None

        excluded_formats = ['MPO']

        for i in ImageSequence.Iterator(img):
            i = node_helpers.pillow(ImageOps.exif_transpose, i)

            if i.mode == 'I':
                i = i.point(lambda i: i * (1 / 255))
            image = i.convert("RGB")

            if len(output_images) == 0:
                w = image.size[0]
                h = image.size[1]

            if image.size[0] != w or image.size[1] != h:
                continue

            image = np.array(image).astype(np.float32) / 255.0
            image = torch.from_numpy(image)[None,]
            output_images.append(image)

        if len(output_images) > 1 and img.format not in excluded_formats:
            output_image = torch.cat(output_images, dim=0)
        else:
            output_image = output_images[0]

        return (output_image, )


class Diffusion360SamplerText2Pano:
    @classmethod
    def INPUT_TYPES(s):
        return {"required":
                    {"model": ("MODEL",),
                     "noise_seed": ("INT", {"default": 0, "min": 0, "max": 65535}),  # 0xffffffffffffffff
                     "steps": ("INT", {"default": 20, "min": 1, "max": 10000}),
                     "cfg": ("FLOAT", {"default": 7.5, "min": 0.0, "max": 100.0, "step": 0.1, "round": 0.01}),
                     "positive": ("CONDITIONING",),
                     "negative": ("CONDITIONING",),
                     "upscale": (["disable", "enable"], ),
                     "refinement": (["disable", "enable"], ),
                     }
                }

    RETURN_TYPES = ("IMAGE",)
    FUNCTION = "sample"

    CATEGORY = "Diffusion360/diffusers"

    def sample(self, model, noise_seed, steps, cfg, positive, negative, upscale, refinement):
        input = {'prompt': positive, 'seed': noise_seed, 'num_inference_steps': steps, 'guidance_scale': cfg}
        if len(negative) > 1:
            input.update({'negative_prompt': negative})
        if upscale == 'enable':
            input.update({'upscale': True})
        else:
            input.update({'upscale': False})
        if refinement == 'enable':
            input.update({'refinement': True})
        else:
            input.update({'refinement': False})
        output = model(input)
        return ([torch.tensor(np.array(output) / 255.)], )


class Diffusion360LoaderText2Pano:
    @classmethod
    def INPUT_TYPES(cls):
        paths = []
        for search_path in folder_paths.get_folder_paths("diffusers"):
            if os.path.exists(search_path):
                for root, subdir, files in os.walk(search_path, followlinks=True):
                    if "RealESRGAN_x2plus.pth" in files:
                        paths.append(os.path.relpath(root, start=search_path))

        return {"required": {"model_path": (paths,), }}
    RETURN_TYPES = ("MODEL",)
    FUNCTION = "load_models"

    CATEGORY = "Diffusion360/diffusers"

    def load_models(self, model_path):
        pipe = Text2360PanoramaImagePipeline(os.path.join('models/diffusers', model_path), torch_dtype=torch.float16)
        return (pipe, )


class Diffusion360SamplerImage2Pano:
    @classmethod
    def INPUT_TYPES(s):
        return {"required":
                    {"model": ("MODEL",),
                     "image": ("IMAGE",),
                     "mask": ("IMAGE", ),
                     "noise_seed": ("INT", {"default": 0, "min": 0, "max": 65535}),  # 0xffffffffffffffff
                     "steps": ("INT", {"default": 20, "min": 1, "max": 10000}),
                     "cfg": ("FLOAT", {"default": 7.5, "min": 0.0, "max": 100.0, "step": 0.1, "round": 0.01}),
                     "positive": ("CONDITIONING",),
                     "negative": ("CONDITIONING",),
                     "upscale": (["disable", "enable"], ),
                     "refinement": (["disable", "enable"], ),
                     }
                }

    RETURN_TYPES = ("IMAGE",)
    FUNCTION = "sample"

    CATEGORY = "Diffusion360/diffusers"

    def sample(self, model, image, mask, noise_seed, steps, cfg, positive, negative, upscale, refinement):
        image = Image.fromarray((image[0] * 255).cpu().numpy().astype(np.uint8))
        input = {'prompt': positive, 'image': image.resize((512, 512)), 'mask': mask, 'seed': noise_seed, 'num_inference_steps': steps, 'guidance_scale': cfg}
        if len(negative) > 1:
            input.update({'negative_prompt': negative})
        if upscale == 'enable':
            input.update({'upscale': True})
        else:
            input.update({'upscale': False})
        if refinement == 'enable':
            input.update({'refinement': True})
        else:
            input.update({'refinement': False})
        output = model(input)
        output = torch.tensor(np.array(output) / 255.)
        return ([output], )


class Diffusion360LoaderImage2Pano:
    @classmethod
    def INPUT_TYPES(cls):
        paths = []
        for search_path in folder_paths.get_folder_paths("diffusers"):
            if os.path.exists(search_path):
                for root, subdir, files in os.walk(search_path, followlinks=True):
                    if "RealESRGAN_x2plus.pth" in files:
                        paths.append(os.path.relpath(root, start=search_path))

        return {"required": {"model_path": (paths,), }}
    RETURN_TYPES = ("MODEL", "IMAGE")
    FUNCTION = "load_models"

    CATEGORY = "Diffusion360/diffusers"

    def load_models(self, model_path):
        pipe = Image2360PanoramaImagePipeline(os.path.join('models/diffusers', model_path), torch_dtype=torch.float16)
        mask = load_image('custom_nodes/Diffusion360_ComfyUI/data/i2p-mask.jpg')
        return (pipe, mask)
