import argparse
import json
import os
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

from app.model.bvh_io import load_bvh_as_mocap
from app.model.runtime import DANCE_KARA, DANCE_MUQAM, Scorer


def infer_dance_type(bvh_path: str, dance_type: str) -> str:
    if dance_type:
        return dance_type
    low = os.path.basename(bvh_path).lower()
    if 'kara' in low or 'jorga' in low:
        return DANCE_KARA
    if 'muqam' in low:
        return DANCE_MUQAM
    return DANCE_KARA


def infer_one(dance_type: str, bvh_path: str, ckpt_path: str):
    dance_type = infer_dance_type(bvh_path, dance_type)
    seq = load_bvh_as_mocap(bvh_path)
    scorer = Scorer(dance_type=dance_type, ckpt_path=ckpt_path)
    result = scorer.score_mocap_sequence(seq)
    payload = {
        'dance_type': dance_type,
        'bvh_path': bvh_path,
        'reference_path': result.get('reference_path', ''),
        'score': result['score'],
        'base': round(float(result['base']), 4),
        'residual': round(float(result['residual']), 4),
        'distance': round(float(result['distance']), 6),
        'worst_joint': result['worst_joint'],
        'feedback': result['feedback'],
        'joint_errors_top5': [
            {'joint': row['joint'], 'error': round(float(row['error']), 6)}
            for row in result.get('joint_errors', [])[:5]
        ],
        'cfpi': result.get('cfpi', {}),
    }
    return payload


def print_text(payload):
    print(f"dance_type: {payload['dance_type']}")
    print(f"bvh_path: {payload['bvh_path']}")
    print(f"reference_path: {payload.get('reference_path', '')}")
    print(f"score: {payload['score']}")
    print(f"base: {payload['base']:.4f}")
    print(f"residual: {payload['residual']:.4f}")
    print(f"distance: {payload['distance']:.6f}")
    print(f"worst_joint: {payload['worst_joint']}")
    print(f"feedback: {payload['feedback']}")
    if payload.get('cfpi'):
        print('cfpi_total:', payload['cfpi'].get('total', 0))
        print('cfpi_dimensions:')
        for key, value in payload['cfpi'].get('dimensions', {}).items():
            print(f"  - {key}: {value:.2f}")
        print('cfpi_components:')
        for key, value in payload['cfpi'].get('components', {}).items():
            print(f"  - {key}: {value:.2f}")
        print('cfpi_cultural_features:')
        for key, value in payload['cfpi'].get('cultural_features', {}).items():
            print(f"  - {key}: {value:.2f}")
    print('joint_errors_top5:')
    for row in payload.get('joint_errors_top5', []):
        print(f"  - {row['joint']}: {row['error']:.6f}")


def main():
    parser = argparse.ArgumentParser(description='对单个 BVH 动作文件执行评分推理并输出 CFPI 分析')
    parser.add_argument('bvh_path', help='待评估的 BVH 文件路径')
    parser.add_argument('--dance-type', default='', help='可选，显式指定舞种；不传则按文件名自动推断')
    parser.add_argument('--ckpt', default=os.path.join(ROOT_DIR, 'assets', 'weights', 'best_dance_scoring.ckpt'), help='MindSpore 权重路径')
    parser.add_argument('--json', action='store_true', help='以 JSON 格式输出')
    args = parser.parse_args()

    payload = infer_one(args.dance_type, args.bvh_path, args.ckpt)
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print_text(payload)


if __name__ == '__main__':
    main()
