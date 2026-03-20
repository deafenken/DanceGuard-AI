import argparse
import os
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from app.model.bvh_io import load_bvh_as_mocap
from app.model.runtime import Scorer


def infer_dance_type(bvh_path: str, dance_type: str) -> str:
    if dance_type:
        return dance_type
    low = os.path.basename(bvh_path).lower()
    if 'kara' in low or 'jorga' in low:
        return '黑走马 (Kara Jorga)'
    if 'muqam' in low:
        return '木卡姆 (Muqam)'
    return '黑走马 (Kara Jorga)'


def infer_one(dance_type: str, bvh_path: str, ckpt_path: str):
    dance_type = infer_dance_type(bvh_path, dance_type)
    seq = load_bvh_as_mocap(bvh_path)
    scorer = Scorer(dance_type=dance_type, ckpt_path=ckpt_path)
    result = scorer.score_mocap_sequence(seq)

    print(f"dance_type: {dance_type}")
    print(f"bvh_path: {bvh_path}")
    print(f"reference_path: {result.get('reference_path', '')}")
    print(f"score: {result['score']}")
    print(f"base: {result['base']:.4f}")
    print(f"residual: {result['residual']:.4f}")
    print(f"distance: {result['distance']:.6f}")
    print(f"worst_joint: {result['worst_joint']}")
    print(f"feedback: {result['feedback']}")
    print("joint_errors_top5:")
    for row in result.get('joint_errors', [])[:5]:
        print(f"  - {row['joint']}: {row['error']:.6f}")


def main():
    parser = argparse.ArgumentParser(description='BVH 离线评分推理')
    parser.add_argument('bvh_path', help='待评估 BVH 文件路径')
    parser.add_argument('--dance-type', default='', help='舞种名称；留空时按文件名自动推断')
    parser.add_argument('--ckpt', default=os.path.join(ROOT_DIR, 'assets', 'weights', 'best_dance_scoring.ckpt'), help='MindSpore 权重路径')
    args = parser.parse_args()

    infer_one(args.dance_type, args.bvh_path, args.ckpt)


if __name__ == '__main__':
    main()
