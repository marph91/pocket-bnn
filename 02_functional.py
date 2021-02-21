# https://keras.io/guides/functional_api/

import os

os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"  # ERROR

import tensorflow as tf
import larq as lq

# x = tf.keras.Input(shape=(28, 28, 1))
# y = tf.keras.layers.Reshape((28 * 28,))(x)
# y = larq.layers.QuantDense(
#     512, kernel_quantizer="ste_sign", kernel_constraint="weight_clip"
# )(y)
# y = larq.layers.QuantDense(
#     10,
#     input_quantizer="ste_sign",
#     kernel_quantizer="ste_sign",
#     kernel_constraint="weight_clip",
#     activation="softmax",
# )(y)

# input_ = tf.keras.Input(batch_shape=(1, 28, 28, 1), name="img")
# x = tf.keras.layers.Conv2D(16, 3, activation="relu")(input_)
# x = tf.keras.layers.Conv2D(32, 3, activation="relu")(x)
# x = tf.keras.layers.MaxPooling2D(3)(x)
# x = tf.keras.layers.Conv2D(32, 3, activation="relu")(x)
# x = tf.keras.layers.Conv2D(16, 3, activation="relu")(x)
# output_ = tf.keras.layers.GlobalMaxPooling2D()(x)
# model = tf.keras.Model(inputs=input_, outputs=output_)
# # model.summary()

# print(model(tf.ones((1, 28, 28, 1))))

############################### max pooling
# input_ = tf.keras.Input(batch_shape=(1, 4, 4, 3), name="img")
# output_ = tf.keras.layers.MaxPooling2D(pool_size=(2, 2), strides=(2, 2))(input_)
# model = tf.keras.Model(inputs=input_, outputs=output_)
## model.summary()

# image_list = [1, 2, 3] * 16
# image_tensor = tf.convert_to_tensor(image_list)
# result = model(tf.reshape(image_tensor, (1, 4, 4, 3)))
# print(result)
# print(list(result.numpy().flat))

############################### conv
import math
import numpy as np
import random

input_ = tf.keras.Input(batch_shape=(1, 4, 4, 3), name="img")
x = lq.layers.QuantConv2D(8, (3, 3), use_bias=False, name="test_conv")(input_)
x = tf.keras.layers.BatchNormalization(name="test_batchnorm")(x)
output_ = lq.quantizers.SteSign()(x)
model = tf.keras.Model(inputs=input_, outputs=output_)
# model.summary()

# print(model.get_layer("test_conv").get_weights()[0])
model.get_layer("test_conv").set_weights(
    [
        np.array(
            [random.choice([-1, 1]) for _ in range(math.prod((3, 3, 3, 8)))]
        ).reshape((3, 3, 3, 8))
    ]
)
# print(model.get_layer("test_conv").get_weights()[0])

# beta=offset, gamma=scale, mean, variance
# original_batch_weights = model.get_layer("test_batchnorm").get_weights()
##print("aaa", original_batch_weights)
## set mean to 0.5
# model.get_layer("test_batchnorm").set_weights([original_batch_weights[0], original_batch_weights[1], np.array([3 * 4 * 4 / 2] * 8), original_batch_weights[3]])
##print("aaa", model.get_layer("test_batchnorm").get_weights())

# image_list = [0, 1, 0] * 16
import random

image_list = [random.choice([-1, 1]) for _ in range(3 * 4 * 4)]
print(image_list)
image_tensor = tf.convert_to_tensor(image_list)
result = model(tf.reshape(image_tensor, (1, 4, 4, 3)))
print(result)
print(list(result.numpy().flat))
