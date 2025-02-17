import argparse
import glob
import math
import numpy as np
from scipy import ndimage
from matplotlib import pyplot
from PIL import Image, ImageOps
import os
import multiprocessing as mp
import os.path
import cv2

def smooth_gaussian(im:np.ndarray, sigma) -> np.ndarray:

    if sigma == 0:
        return im

    im_smooth = im.astype(float)
    kernel_x = np.arange(-3*sigma,3*sigma+1).astype(float)
    kernel_x = np.exp((-(kernel_x**2))/(2*(sigma**2)))

    im_smooth = ndimage.convolve(im_smooth, kernel_x[np.newaxis])

    im_smooth = ndimage.convolve(im_smooth, kernel_x[np.newaxis].T)

    return im_smooth


def gradient(im_smooth:np.ndarray):

    gradient_x = im_smooth.astype(float)
    gradient_y = im_smooth.astype(float)

    kernel = np.arange(-1,2).astype(float)
    kernel = - kernel / 2

    gradient_x = ndimage.convolve(gradient_x, kernel[np.newaxis])
    gradient_y = ndimage.convolve(gradient_y, kernel[np.newaxis].T)

    return gradient_x,gradient_y


def sobel(im_smooth):
    gradient_x = im_smooth.astype(float)
    gradient_y = im_smooth.astype(float)

    kernel = np.array([[-1,0,1],[-2,0,2],[-1,0,1]])

    gradient_x = ndimage.convolve(gradient_x, kernel)
    gradient_y = ndimage.convolve(gradient_y, kernel.T)

    return gradient_x,gradient_y


def compute_normal_map(gradient_x:np.ndarray, gradient_y:np.ndarray, intensity=1):

    width = gradient_x.shape[1]
    height = gradient_x.shape[0]
    max_x = np.max(gradient_x)
    max_y = np.max(gradient_y)

    max_value = max_x

    if max_y > max_x:
        max_value = max_y

    normal_map = np.zeros((height, width, 3), dtype=np.float32)

    intensity = 1 / intensity

    strength = max_value / (max_value * intensity)

    normal_map[..., 0] = gradient_x / max_value
    normal_map[..., 1] = gradient_y / max_value
    normal_map[..., 2] = 1 / strength

    norm = np.sqrt(np.power(normal_map[..., 0], 2) + np.power(normal_map[..., 1], 2) + np.power(normal_map[..., 2], 2))

    normal_map[..., 0] /= norm
    normal_map[..., 1] /= norm
    normal_map[..., 2] /= norm

    normal_map *= 0.5
    normal_map += 0.5

    return normal_map

def normalized(a) -> float: 
    factor = 1.0/math.sqrt(np.sum(a*a)) # normalize
    return a*factor

def my_gauss(im:np.ndarray):
    return ndimage.uniform_filter(im.astype(float),size=20)

def shadow(im:np.ndarray):
    
    shadowStrength = .5
    
    im1 = im.astype(float)
    im0 = im1.copy()
    im00 = im1.copy()
    im000 = im1.copy()

    for _ in range(0,2):
        im00 = my_gauss(im00)

    for _ in range(0,16):
        im0 = my_gauss(im0)

    for _ in range(0,32):
        im1 = my_gauss(im1)

    im000=normalized(im000)
    im00=normalized(im00)
    im0=normalized(im0)
    im1=normalized(im1)
    im00=normalized(im00)

    shadow=im00*2.0+im000-im1*2.0-im0 
    shadow=normalized(shadow)
    mean = np.mean(shadow)
    rmse = np.sqrt(np.mean((shadow-mean)**2))*(1/shadowStrength)
    shadow = np.clip(shadow, mean-rmse*2.0,mean+rmse*0.5)

    return shadow

def flip_green(path:str):
    try:
        with Image.open(path) as img:
            red, green, blue, alpha= img.split()
            image = Image.merge("RGB",(red,ImageOps.invert(green),blue))
            image.save(path)
    except ValueError:
        with Image.open(path) as img:
            red, green, blue = img.split()
            image = Image.merge("RGB",(red,ImageOps.invert(green),blue))
            image.save(path)

def cleanup_AO(path:str):
    '''
    Remove unnsesary channels.
    '''
    try:
        with Image.open(path) as img:
            red, green, blue, alpha= img.split()
            NewG = ImageOps.colorize(green,black=(100, 100, 100),white=(255,255,255),blackpoint=0,whitepoint=180)
            NewG.save(path)
    except ValueError:
        with Image.open(path) as img:
            red, green, blue = img.split()
            NewG = ImageOps.colorize(green,black=(100, 100, 100),white=(255,255,255),blackpoint=0,whitepoint=180)
            NewG.save(path)

def adjust_path(Org_Path:str,addto:str):
    '''
    Adjust the given path to correctly save the new file.
    '''

    path = Org_Path.split("\\")
    file = path[-1]
    filename = file.split(".")[0]
    format_str="_albedo"
    # Filename without _albedo
    filename = filename[:-len(format_str)]
    fileext = file.split(".")[-1]

    newfilename = filename + "_" + addto + "." + fileext
    path.pop(-1)
    path.append(newfilename)

    newpath = '\\'.join(path)

    return newpath

def resize(input_file : str , size : int):
    not_setted = size < 0
    if not_setted:
        return
    
    original_img=cv2.imread(input_file)
    original_width=original_img.shape[1]
    original_height=original_img.shape[0]
    original_ratio=float(original_width)/float(original_height)
    new_width=size
    new_height=int(size*original_ratio)
    # width and height are in reversed order for cv2
    new_img=cv2.resize(original_img, (new_height,new_width))
    cv2.imwrite(input_file, new_img)

def convert_normal_map(input_file,smoothness,intensity,size : int):

    normal_filename=adjust_path(input_file,"normal")
    # Only convert it not exists
    if os.path.isfile(normal_filename):
        print(f"{normal_filename} exists. Skipping it")
        return
    
    im = pyplot.imread(input_file)

    if im.ndim == 3:
        im_grey = np.zeros((im.shape[0],im.shape[1])).astype(float)
        im_grey = (im[...,0] * 0.3 + im[...,1] * 0.6 + im[...,2] * 0.1)
        im = im_grey

    im_smooth = smooth_gaussian(im, smoothness)

    sobel_x, sobel_y = sobel(im_smooth)
    normal_map = compute_normal_map(sobel_x, sobel_y, intensity)

    pyplot.imsave(normal_filename,normal_map)
    flip_green(normal_filename)

    resize(normal_filename,size)

    print(f"Created {normal_filename}")

def convert_ao_map(input_file,size : int): 
    ao_filename=adjust_path(input_file,"ao")
    # Only convert it not exists
    if os.path.isfile(ao_filename):
        print(f"{ao_filename} exists. Skipping it")
        return
    
    im = pyplot.imread(input_file)

    if im.ndim == 3:
        im_grey = np.zeros((im.shape[0],im.shape[1])).astype(float)
        im_grey = (im[...,0] * 0.3 + im[...,1] * 0.6 + im[...,2] * 0.1)
        im = im_grey

    im_shadow = shadow(im)

    pyplot.imsave(ao_filename,im_shadow)
    cleanup_AO(ao_filename)
    
    resize(ao_filename,size)

    print(f"Created {ao_filename}")

def convert(input_file,smoothness,intensity,size : int):

    convert_normal_map(input_file,smoothness,intensity,size)
    convert_ao_map(input_file,size)

def start_convert():
    
    parser = argparse.ArgumentParser(description='Compute normal map of an image')

    parser.add_argument('input_folder', type=str, help='input folder path')
    parser.add_argument('-sm', '--smooth', default=0., type=float, help='smooth gaussian blur applied on the image')
    parser.add_argument('-it', '--intensity', default=1., type=float, help='intensity of the normal map')
    parser.add_argument('-sz', '--size', default=-1, type=int, help='size of image')

    args = parser.parse_args()

    sigma = args.smooth
    intensity = args.intensity
    input_folder = args.input_folder
    size = args.size

    image_name_format = f"{input_folder}/*_albedo"
    image_files = glob.glob(f"{image_name_format}.png",recursive=True) + glob.glob(f"{image_name_format}.jpg",recursive=True)
    
    for input_file in image_files:
        print(f"Converting {input_file}")
        convert(input_file,sigma,intensity,size)

    print("Completed")

if __name__ == "__main__":
    start_convert()