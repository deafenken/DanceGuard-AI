import numpy as np
import mindspore as ms
from mindspore import nn, ops


def train_epoch(net, dataset, lr: float = 1e-3, ckpt_path: str = "assets/weights/best_dance_scoring.ckpt"):
    loss_fn = nn.MSELoss()
    opt = nn.Adam(net.trainable_params(), learning_rate=lr)

    def forward_fn(mocap, rgb, flow, label):
        _, _, final = net(mocap, rgb, flow)
        pred = ops.squeeze(final, axis=-1)
        return loss_fn(pred, label)

    grad_fn = ops.value_and_grad(forward_fn, None, opt.parameters)

    losses = []
    net.set_train(True)
    for mocap, rgb, flow, label in dataset.create_tuple_iterator(num_epochs=1):
        loss, grads = grad_fn(mocap, rgb, flow, label)
        opt(grads)
        losses.append(float(loss.asnumpy()))

    mean_loss = float(np.mean(losses)) if losses else 0.0
    ms.save_checkpoint(net, ckpt_path)
    print(f"train_loss={mean_loss:.6f}, ckpt={ckpt_path}")
    return mean_loss


def eval_epoch(net, dataset) -> float:
    loss_fn = nn.MSELoss()
    losses = []
    net.set_train(False)
    for mocap, rgb, flow, label in dataset.create_tuple_iterator(num_epochs=1):
        _, _, final = net(mocap, rgb, flow)
        pred = ops.squeeze(final, axis=-1)
        loss = loss_fn(pred, label)
        losses.append(float(loss.asnumpy()))
    return float(np.mean(losses)) if losses else 0.0
