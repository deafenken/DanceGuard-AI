import os
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
import mindspore as ms

from app.model import DanceSet, fake_data, load_model, predict


def main():
    ms.set_context(mode=ms.PYNATIVE_MODE)
    mocap, score = fake_data(n=8, t=64, j=24, seed=9)
    ds = DanceSet(mocap, score).to_ds(batch_size=4, shuffle=False)
    net = load_model("assets/weights/best_dance_scoring.ckpt", joints=24)

    mocap_batch, _, _, label = next(ds.create_tuple_iterator(num_epochs=1))
    base, res, final = predict(net, mocap_batch.asnumpy())

    print("GT score (sample0):", float(label[0].asnumpy()))
    print("Base score (sample0):", float(base[0, 0]))
    print("Residual score (sample0):", float(res[0, 0]))
    print("Final score (sample0):", float(final[0, 0]))


if __name__ == "__main__":
    main()


