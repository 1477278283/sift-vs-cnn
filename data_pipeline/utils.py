import cv2 as cv
import os
import torch
from skimage import transform
import numpy as np
import pandas as pd
import torch.nn as nn
import matplotlib.pyplot as plt

device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")

def read_images(root_path, indices, N=None, grey=True):
    print('Reading images from ', root_path)
    images = []
    for index in range(len(indices)):
        image_path = os.path.join(root_path, indices.iloc[index, 0])
        image = cv.imread(image_path)
        if grey:
            image = cv.cvtColor(image, cv.COLOR_BGR2GRAY)
        images.append(image)
        if N is not None and index == N-1:
            break
    print('Read', len(images), 'images')
    return images

# Rescale and ToTensor taken from this tutorial: 
# https://pytorch.org/tutorials/beginner/data_loading_tutorial.html

class Rescale(object):
    """Rescale the image in a sample to a given size.

    Args:
        output_size (tuple or int): Desired output size. If tuple, output is
            matched to output_size. If int, smaller of image edges is matched
            to output_size keeping aspect ratio the same.
    """

    def __init__(self, output_size):
        assert isinstance(output_size, (int, tuple))
        self.output_size = output_size

    def __call__(self, image):
        return transform.resize(image, (self.output_size, self.output_size))

class SampleRescale(object):
    """Rescale the image in a sample to a given size.

    Args:
        output_size (tuple or int): Desired output size. If tuple, output is
            matched to output_size. If int, smaller of image edges is matched
            to output_size keeping aspect ratio the same.
    """

    def __init__(self, output_size):
        assert isinstance(output_size, (int, tuple))
        self.output_size = output_size

    def __call__(self, sample):
        image, label = sample
        img = transform.resize(image, (self.output_size, self.output_size))
        return img, label

class SampleToTensor(object):
    """Convert ndarrays in sample to Tensors."""

    def __init__(self, grey):
        self.grey = grey

    def __call__(self, sample):
        image, label = sample
        if self.grey:
            image = np.expand_dims(image, axis=0)
        else:
            # swap color axis because
            # numpy image: H x W x C
            # torch image: C X H X W
            image = image.transpose((2, 0, 1))
        # the dataset labels are indexed from one
        label_index = label - 1
        return torch.from_numpy(image).float(), label_index

class ToTensor(object):
    """Convert ndarrays to Tensors."""

    def __init__(self, grey):
        self.grey = grey

    def __call__(self, image):
        if self.grey:
            image = np.expand_dims(image, axis=0)
        else:
            # swap color axis because
            # numpy image: H x W x C
            # torch image: C X H X W
            image = np.array(image).transpose((2, 0, 1))
        return torch.from_numpy(image).float()

def get_all_data_from_loader(dataloader):
    features = torch.FloatTensor().to(device)
    labels = torch.LongTensor().to(device)
    for x, y in dataloader:
        x = x.to(device)
        y = y.to(device)
        features = torch.cat((features, x.float()), 0)
        labels = torch.cat((labels, y), 0)
    return torch.squeeze(features).cpu().numpy(), torch.squeeze(labels).cpu().numpy()

def normalise_rgb_dims(image):
    # normalisation should reduce sensitivity to lumincance, surface orientation and other conditions
    # as per Verma et al.
    normaliser = np.expand_dims(image.sum(-1), axis=2)
    # avoid dividing by zero in case all dimensions are 0
    normaliser[normaliser == 0] = 1
    return ((image / normaliser)*255).astype('uint8')

def change_image_colourspace(color_space, image):
    # opencv color order is (blue, green, red)
    transform = None
    color_space = color_space.lower()
    if color_space == 'hsv':
        transform = lambda image: cv.cvtColor(image, cv.COLOR_BGR2HSV)
    elif color_space == 'ycrcb':
        transform = lambda image: cv.cvtColor(image, cv.COLOR_BGR2YCrCb)
    elif color_space == 'bgr':
        transform = lambda image: normalise_rgb_dims(image)
    else:
        raise ValueError('Color space', color_space, 'not supported')
    return transform(image)

# https://discuss.pytorch.org/t/size-mismatch-after-loading-saved-model-please-explain/21295/7
class Flatten(nn.Module):
    def __init__(self):
        super(Flatten, self).__init__()
        
    def forward(self, x):
        return x.reshape(x.size(0), -1)

def visualise_cnn(image, till_kernel, preprocess):
    model = nn.Sequential(*list(till_kernel))  
    res = model(preprocess(image).unsqueeze(0).to(device))
    size = 4
    fig = plt.figure(figsize=(8, 8))
    for i in range(1, size**2+1):
        fig.add_subplot(size, size, i)
        plt.imshow(res.detach().numpy()[0, i, :, :])
    plt.show()
