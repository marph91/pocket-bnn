import tensorflow as tf
import larq as lq
import numpy as np
import matplotlib.pyplot as plt

num_classes = 10

(
    (train_images, train_labels),
    (test_images, test_labels,),
) = tf.keras.datasets.cifar10.load_data()

train_images = train_images.reshape((50000, 32, 32, 3)).astype("float32")
test_images = test_images.reshape((10000, 32, 32, 3)).astype("float32")

# Normalize pixel values to be between -1 and 1
train_images, test_images = train_images / 127.5 - 1, test_images / 127.5 - 1

train_labels = tf.keras.utils.to_categorical(train_labels, num_classes)
test_labels = tf.keras.utils.to_categorical(test_labels, num_classes)


# All quantized layers except the first will use the same options
kwargs = dict(
    input_quantizer="ste_sign",
    kernel_quantizer="ste_sign",
    kernel_constraint="weight_clip",
    use_bias=False,
)

model = tf.keras.models.Sequential(
    [
        # In the first layer we only quantize the weights and not the input
        lq.layers.QuantConv2D(
            128,
            3,
            kernel_quantizer="ste_sign",
            kernel_constraint="weight_clip",
            use_bias=False,
            input_shape=(32, 32, 3),
        ),
        tf.keras.layers.BatchNormalization(momentum=0.999, scale=False),
        lq.layers.QuantConv2D(128, 3, padding="same", **kwargs),
        tf.keras.layers.MaxPool2D(pool_size=(2, 2), strides=(2, 2)),
        tf.keras.layers.BatchNormalization(momentum=0.999, scale=False),
        lq.layers.QuantConv2D(256, 3, padding="same", **kwargs),
        tf.keras.layers.BatchNormalization(momentum=0.999, scale=False),
        lq.layers.QuantConv2D(256, 3, padding="same", **kwargs),
        tf.keras.layers.MaxPool2D(pool_size=(2, 2), strides=(2, 2)),
        tf.keras.layers.BatchNormalization(momentum=0.999, scale=False),
        lq.layers.QuantConv2D(512, 3, padding="same", **kwargs),
        tf.keras.layers.BatchNormalization(momentum=0.999, scale=False),
        lq.layers.QuantConv2D(512, 3, padding="same", **kwargs),
        tf.keras.layers.MaxPool2D(pool_size=(2, 2), strides=(2, 2)),
        tf.keras.layers.BatchNormalization(momentum=0.999, scale=False),
        tf.keras.layers.Flatten(),
        lq.layers.QuantDense(1024, **kwargs),
        tf.keras.layers.BatchNormalization(momentum=0.999, scale=False),
        lq.layers.QuantDense(1024, **kwargs),
        tf.keras.layers.BatchNormalization(momentum=0.999, scale=False),
        lq.layers.QuantDense(10, **kwargs),
        tf.keras.layers.BatchNormalization(momentum=0.999, scale=False),
        tf.keras.layers.Activation("softmax"),
    ]
)


lq.models.summary(model)


model.compile(
    tf.keras.optimizers.Adam(lr=0.01, decay=0.0001),
    loss="categorical_crossentropy",
    metrics=["accuracy"],
)

trained_model = model.fit(
    train_images,
    train_labels,
    batch_size=50,
    epochs=100,
    validation_data=(test_images, test_labels),
    shuffle=True,
)


plt.plot(trained_model.history["acc"])
plt.plot(trained_model.history["val_acc"])
plt.title("model accuracy")
plt.ylabel("accuracy")
plt.xlabel("epoch")
plt.legend(["train", "test"], loc="upper left")

print(np.max(trained_model.history["acc"]))
print(np.max(trained_model.history["val_acc"]))


plt.plot(trained_model.history["loss"])
plt.plot(trained_model.history["val_loss"])
plt.title("model loss")
plt.ylabel("loss")
plt.xlabel("epoch")
plt.legend(["train", "test"], loc="upper left")

print(np.min(trained_model.history["loss"]))
print(np.min(trained_model.history["val_loss"]))
