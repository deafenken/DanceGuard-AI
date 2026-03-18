import os
import tempfile
import unittest

import mindspore as ms
import numpy as np

from app.model import DanceSet, EvalNet, fake_data, load_model, predict, train_epoch


class TestProject(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        ms.set_context(mode=ms.PYNATIVE_MODE)

    def test_dataset_shape(self):
        mocap, score = fake_data(n=12, t=32, j=24, seed=1)
        ds = DanceSet(mocap, score).to_ds(batch_size=4, shuffle=False)
        mocap_b, rgb_b, flow_b, y = next(ds.create_tuple_iterator(num_epochs=1))
        self.assertEqual(mocap_b.shape, (4, 32, 24, 3))
        self.assertEqual(rgb_b.shape, (4, 32, 3, 224, 224))
        self.assertEqual(flow_b.shape, (4, 32, 2, 224, 224))
        self.assertTrue(np.all(y.asnumpy() >= 0))

    def test_train_and_infer(self):
        mocap, score = fake_data(n=16, t=32, j=24, seed=2)
        ds = DanceSet(mocap, score).to_ds(batch_size=4, shuffle=False)
        net = EvalNet(joints=24)

        with tempfile.TemporaryDirectory() as td:
            ckpt = os.path.join(td, "m.ckpt")
            train_epoch(net, ds, lr=1e-3, ckpt_path=ckpt)
            self.assertTrue(os.path.exists(ckpt))

            net2 = load_model(ckpt, joints=24)
            mocap_b, _, _, _ = next(ds.create_tuple_iterator(num_epochs=1))
            base, res, final = predict(net2, mocap_b.asnumpy())
            self.assertEqual(base.shape[0], 4)
            self.assertEqual(res.shape[0], 4)
            self.assertEqual(final.shape[0], 4)


if __name__ == "__main__":
    unittest.main()

