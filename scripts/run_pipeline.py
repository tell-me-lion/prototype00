"""전체 파이프라인 실행 진입점.

블록 단위(Pre-processor, EP, Blueprint, Quiz Generation, QA Validation, Guides) 또는
전처리 Phase 범위 지정으로 실행할 수 있도록 한다.
"""

import argparse
import sys
from pathlib import Path


def main() -> None:
    project_root = Path(__file__).resolve().parent.parent

    # 패키지 import를 위해 경로 추가
    sys.path.insert(0, str(project_root))

    from pipeline import paths  # noqa: WPS433
    from pipeline.blueprint import runner as blueprint_runner  # noqa: WPS433
    from pipeline.ep import runner as ep_runner  # noqa: WPS433
    from pipeline.guides import runner as guides_runner  # noqa: WPS433
    from pipeline.phase1 import runner as phase1_runner  # noqa: WPS433
    from pipeline.phase2 import runner as phase2_runner  # noqa: WPS433
    from pipeline.phase3 import runner as phase3_runner  # noqa: WPS433
    from pipeline.phase4 import runner as phase4_runner  # noqa: WPS433
    from pipeline.phase5 import runner as phase5_runner  # noqa: WPS433
    from pipeline.qa_validation import runner as qa_runner  # noqa: WPS433
    from pipeline.quiz_generation import runner as qg_runner  # noqa: WPS433

    parser = argparse.ArgumentParser(description="Run tell-me-lion full pipeline")
    parser.add_argument(
        "--from-block",
        choices=["preproc", "ep", "blueprint", "quiz", "qa", "guides"],
        default="preproc",
        help="실행 시작 블록 (기본: preproc).",
    )
    parser.add_argument(
        "--to-block",
        choices=["preproc", "ep", "blueprint", "quiz", "qa", "guides"],
        default="guides",
        help="실행 종료 블록 (기본: guides).",
    )
    parser.add_argument(
        "--from-phase",
        type=int,
        default=1,
        help="전처리(Pre-processor)에서 시작할 Phase (1~5).",
    )
    parser.add_argument(
        "--to-phase",
        type=int,
        default=5,
        help="전처리(Pre-processor)에서 종료할 Phase (1~5).",
    )
    args = parser.parse_args()

    print("=== tell-me-lion pipeline ===")
    print(f"ROOT: {project_root}")
    print(f"DATA_RAW: {paths.DATA_RAW}")
    print(f"DATA_PHASE5_FACTS: {paths.DATA_PHASE5_FACTS}")
    print()

    blocks = ["preproc", "ep", "blueprint", "quiz", "qa", "guides"]
    start_idx = blocks.index(args.from_block)
    end_idx = blocks.index(args.to_block)

    for block in blocks[start_idx : end_idx + 1]:
        if block == "preproc":
            print("[Pre-processor] Phase 1~5 실행")
            if args.from_phase <= 1 <= args.to_phase:
                phase1_runner.run_phase1()
            if args.from_phase <= 2 <= args.to_phase:
                phase2_runner.run_phase2()
            if args.from_phase <= 3 <= args.to_phase:
                phase3_runner.run_phase3()
            if args.from_phase <= 4 <= args.to_phase:
                phase4_runner.run_phase4()
            if args.from_phase <= 5 <= args.to_phase:
                phase5_runner.run_phase5()
        elif block == "ep":
            print("[EP] 핵심 개념/학습 포인트 식별 실행")
            ep_runner.run_ep()
        elif block == "blueprint":
            print("[Blueprint] 문제 블루프린트 작성 실행")
            blueprint_runner.run_blueprint()
        elif block == "quiz":
            print("[Quiz Generation] 퀴즈/해설 생성 실행")
            qg_runner.run_quiz_generation()
        elif block == "qa":
            print("[QA Validation] 퀴즈 품질/사실 검증 실행")
            qa_runner.run_validation()
        elif block == "guides":
            print("[Guides] 학습 가이드/핵심 요약 생성 실행")
            guides_runner.run_guides()


if __name__ == "__main__":
    main()