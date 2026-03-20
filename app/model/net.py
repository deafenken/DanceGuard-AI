import numpy as np
import mindspore as ms
from mindspore import Tensor, Parameter, nn, ops


class EvalNet(nn.Cell):
    """MoCap 主导 + 视觉缺失模态插补 + 残差微调（限制在 ±2 分）。"""

    def __init__(self, joints: int = 24, mocap_hidden: int = 256, visual_hidden: int = 16):
        super().__init__()

        in_c = joints * 3
        self.mocap_conv1 = nn.Conv1d(in_c, 128, 5, pad_mode="pad", padding=2, has_bias=True)
        self.mocap_conv2 = nn.Conv1d(128, 256, 3, pad_mode="pad", padding=1, has_bias=True)
        self.mocap_gru = nn.GRU(256, mocap_hidden, num_layers=1, has_bias=True, batch_first=True)

        self.rgb_fc = nn.Dense(3, visual_hidden)
        self.flow_fc = nn.Dense(2, visual_hidden)
        self.rgb_missing_token = Parameter(Tensor(np.zeros((1, visual_hidden), dtype=np.float32)), name="rgb_missing_token")
        self.flow_missing_token = Parameter(Tensor(np.zeros((1, visual_hidden), dtype=np.float32)), name="flow_missing_token")

        self.base_fc = nn.Dense(mocap_hidden, 1)

        self.cat = ops.Concat(axis=1)
        self.drop = nn.Dropout(p=0.1)
        self.fuse = nn.SequentialCell(
            nn.Dense(mocap_hidden + visual_hidden + visual_hidden, 128),
            nn.ReLU(),
            nn.Dense(128, 32),
            nn.ReLU(),
        )
        self.res_fc = nn.Dense(32, 1)

        self.relu = nn.ReLU()
        self.sigmoid = ops.Sigmoid()
        self.tanh = ops.Tanh()
        self.res_scale = Tensor(2.0, ms.float32)
        self.zero_gate = Tensor(1e-6, ms.float32)

    def _impute_visual_latent(self, feat, encoder, missing_token):
        raw = self.relu(encoder(feat))
        energy = ops.reduce_sum(ops.abs(feat), axis=1)
        mask = ops.cast(energy > self.zero_gate, ms.float32)
        mask = ops.expand_dims(mask, 1)
        token = ops.broadcast_to(missing_token, raw.shape)
        return raw * mask + token * (1.0 - mask)

    def construct(self, mocap, rgb, flow):
        b, t, j, c = mocap.shape
        x = ops.reshape(mocap, (b, t, j * c))
        x = ops.transpose(x, (0, 2, 1))
        x = self.relu(self.mocap_conv1(x))
        x = self.relu(self.mocap_conv2(x))
        x = ops.transpose(x, (0, 2, 1))
        x, _ = self.mocap_gru(x)
        mocap_latent = ops.reduce_mean(x, axis=1)

        rgb_feat = ops.reduce_mean(rgb, axis=(1, 3, 4))
        flow_feat = ops.reduce_mean(flow, axis=(1, 3, 4))
        rgb_latent = self._impute_visual_latent(rgb_feat, self.rgb_fc, self.rgb_missing_token)
        flow_latent = self._impute_visual_latent(flow_feat, self.flow_fc, self.flow_missing_token)

        base = self.sigmoid(self.base_fc(mocap_latent)) * 100.0

        latent = self.cat((mocap_latent, rgb_latent, flow_latent))
        latent = self.drop(latent)
        latent = self.fuse(latent)
        res = self.tanh(self.res_fc(latent)) * self.res_scale

        final = ops.clip_by_value(base + res, Tensor(0.0, ms.float32), Tensor(100.0, ms.float32))
        return base, res, final
