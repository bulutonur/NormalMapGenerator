# Normal Map Generator

Normal Map Generator is a tool written in Python

## Required

- Python 3
- numpy
- matplotlib
- Pillow
- scipy
- opencv-python

See requirements.txt

## Usage

Add images ending with _albedo.png or _albedo.jpg to input_folder. For example:

input_folder/bricks_albedo.png

input_folder/bricks_albedo.jpg

```
python3 normal_map_generator.py input_folder --smooth SMOOTH_VALUE --intensity INTENSITY_VALUE
```

#### input_folder            
input image path

### Optional arguments:

#### -h, --help            
Show help message

#### -sm SMOOTH_VALUE, --smooth SMOOTH_VALUE
Smooth gaussian blur applied on the image

#### -it INTENSITY_VALUE, --intensity INTENSITY_VALUE
Intensity of the normal map

#### -sz SIZE, --size SIZE
Size of texture. For example : 512

If size is not defined, it will be original size of albedo textures.
