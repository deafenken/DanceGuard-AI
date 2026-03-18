import os
import mindspore as ms
import numpy as np
from mindspore import Tensor

from .net import EvalNet


def load_model(ckpt_path: str, joints: int = 24):
    if not os.path.exists(ckpt_path):
        raise FileNotFoundError(f"Checkpoint not found: {ckpt_path}")
    net = EvalNet(joints=joints)
    params = ms.load_checkpoint(ckpt_path)
    ms.load_param_into_net(net, params)
    net.set_train(False)
    return net


def predict(net, mocap_np: np.ndarray):
    """mocap_np: [B,T,J,3]"""
    b, t, _, _ = mocap_np.shape
    rgb = np.zeros((b, t, 3, 224, 224), dtype=np.float32)
    flow = np.zeros((b, t, 2, 224, 224), dtype=np.float32)

    mocap = Tensor(mocap_np, ms.float32)
    rgb = Tensor(rgb, ms.float32)
    flow = Tensor(flow, ms.float32)

    base, res, final = net(mocap, rgb, flow)
    return base.asnumpy(), res.asnumpy(), final.asnumpy()
