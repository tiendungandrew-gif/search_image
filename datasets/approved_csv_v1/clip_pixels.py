"""Pinned CLIP geometry, preserving the encoder's exact 224x224 input pixels."""
from PIL import Image

def prepare(image):
    width,height=image.size
    short,long=(width,height) if width<=height else (height,width)
    new_short,new_long=224,int(224*long/short)
    size=(new_short,new_long) if width<=height else (new_long,new_short)
    resized=image.resize(size,resample=Image.Resampling.BICUBIC)
    left=(resized.width-224)//2
    top=(resized.height-224)//2
    return resized.crop((left,top,left+224,top+224))
