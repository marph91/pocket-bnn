import larq as lq
import tensorflow as tf

# for resizing
import cv2
import numpy as np

(train_images, train_labels), (
    test_images,
    test_labels,
) = tf.keras.datasets.mnist.load_data()

# reshape the inputs
# train_images = np.stack([cv2.resize(img, (22, 22)) for img in train_images])
train_images = train_images.reshape((60000, 28, 28, 1))
# test_images = np.stack([cv2.resize(img, (22, 22)) for img in test_images])
test_images = test_images.reshape((10000, 28, 28, 1))

# All quantized layers except the first will use the same options
kwargs = dict(
    input_quantizer="ste_sign",
    kernel_quantizer="ste_sign",
    kernel_constraint="weight_clip",
)

model = tf.keras.models.Sequential()

# In the first layer we only quantize the weights and not the input
model.add(
    lq.layers.QuantConv2D(
        8,
        (3, 3),
        kernel_quantizer="ste_sign",
        kernel_constraint="weight_clip",
        use_bias=False,
        input_shape=train_images.shape[1:],
    )
)
# Scale is not needed, since we clip afterwards anyway.
model.add(tf.keras.layers.BatchNormalization(scale=False))

model.add(lq.layers.QuantConv2D(16, (3, 3), use_bias=False, **kwargs))
model.add(tf.keras.layers.BatchNormalization(scale=False))
model.add(tf.keras.layers.MaxPooling2D((2, 2)))

model.add(lq.layers.QuantConv2D(32, (3, 3), use_bias=False, **kwargs))
model.add(tf.keras.layers.BatchNormalization(scale=False))
model.add(tf.keras.layers.MaxPooling2D((2, 2)))

model.add(lq.layers.QuantConv2D(64, (1, 1), use_bias=False, **kwargs))
model.add(tf.keras.layers.BatchNormalization(scale=False))
# model.add(tf.keras.layers.Dropout(0.2))
if True:
    model.add(lq.layers.QuantConv2D(10, (1, 1), use_bias=False, **kwargs))
    model.add(lq.layers.tf.keras.layers.GlobalAveragePooling2D())
else:
    # fully connected layer instead of 1x1 convolution
    model.add(tf.keras.layers.Flatten())
    model.add(lq.layers.QuantDense(10, use_bias=False, **kwargs))
model.add(tf.keras.layers.Activation("softmax"))

lq.models.summary(model)

model.compile(
    optimizer="adam", loss="sparse_categorical_crossentropy", metrics=["accuracy"]
)
model.fit(train_images, train_labels, batch_size=64, epochs=10)
test_loss, test_acc = model.evaluate(test_images, test_labels)
print(f"Test accuracy {test_acc * 100:.2f} %")

model.save("../models/test")
