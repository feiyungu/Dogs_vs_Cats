import glob
import os

import numpy as np
import tflearn
from skimage import transform
from skimage.io import imread
from sklearn.model_selection import train_test_split

pjoin = os.path.join
TRAIN_DATA = pjoin(os.path.dirname(__file__), 'images')
MODEL_PATH = pjoin(os.path.dirname(__file__), 'model')
if not os.path.exists(MODEL_PATH):
    os.makedirs(MODEL_PATH, mode=0755)

MEAN_PIXEL = [127, 127, 127]


def crop_image(image, dshape):
    factor = float(min(dshape[:2])) / min(image.shape[:2])
    new_size = [int(image.shape[0] * factor), int(image.shape[1] * factor)]
    if new_size[0] < dshape[0]:
        new_size[0] = dshape[0]
    if new_size[1] < dshape[0]:
        new_size[1] = dshape[0]
    resized_image = transform.resize(image, new_size)
    sample = np.asarray(resized_image) * 256
    if dshape[0] < sample.shape[0] or dshape[1] < sample.shape[1]:
        xx = int((sample.shape[0] - dshape[0]))
        yy = int((sample.shape[1] - dshape[1]))
        xstart = xx / 2
        ystart = yy / 2
        xend = xstart + dshape[0]
        yend = ystart + dshape[1]
        sample = sample[xstart:xend, ystart:yend, :]
    return sample


def preprocess_image(path, dshape):
    image = imread(path)
    image = crop_image(image, dshape=dshape)
    image -= MEAN_PIXEL
    return image


def postprocess_image(image, dshape):
    image = np.reshape(image, dshape) + MEAN_PIXEL
    image = np.clip(image, 0, 255).astype(np.uint8)
    return image


def read_data():
    X = []
    Y = []
    for f in glob.glob(TRAIN_DATA + '/*.jpg'):
        fname = os.path.basename(f)
        # 0 for cat, 1 for dog
        label = 0 if fname.startswith('cat') else 1
        image = preprocess_image(f, [256, 256, 3])
        print(image.shape)
        X.append(image)
        Y.append(label)
        # split training data and validation set data
    X, X_test, y, y_test = train_test_split(X, Y,
                                            test_size=0.2,
                                            random_state=42)
    return (X, y), (X_test, y_test)


(X, Y), (X_test, Y_test) = read_data()
Y = tflearn.data_utils.to_categorical(Y, 2)
Y_test = tflearn.data_utils.to_categorical(Y_test, 2)

# Residual blocks
n = 5

# Building Residual Network
net = tflearn.input_data(shape=[None, 256, 256, 3])
net = tflearn.conv_2d(net, 16, 3, regularizer='L2', weight_decay=0.0001)
net = tflearn.residual_block(net, n, 16)
net = tflearn.residual_block(net, 1, 32, downsample=True)
net = tflearn.residual_block(net, n - 1, 32)
net = tflearn.residual_block(net, 1, 64, downsample=True)
net = tflearn.residual_block(net, n - 1, 64)
net = tflearn.batch_normalization(net)
net = tflearn.activation(net, 'relu')
net = tflearn.global_avg_pool(net)
# Regression
net = tflearn.fully_connected(net, 2, activation='softmax')
net = tflearn.regression(net, optimizer='adam', loss='categorical_crossentropy')
# Training
model = tflearn.DNN(net, checkpoint_path='model_resnet',
                    max_checkpoints=10, tensorboard_verbose=0,
                    clip_gradients=0.)

if os.path.exists(pjoin(MODEL_PATH, 'resnet_cat_dog.model')):
    model.load(pjoin(MODEL_PATH, 'resnet_cat_dog.model'))

model.fit(X, Y, n_epoch=200, validation_set=(X_test, Y_test),
          snapshot_epoch=False, snapshot_step=500,
          show_metric=True, batch_size=16, shuffle=True,
          run_id='resnet_cat_dog')

model.save(pjoin(MODEL_PATH, 'resnet_cat_dog.model'))