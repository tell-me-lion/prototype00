#!/bin/bash
# 문서-코드 정합성 자동 점검 (헤드리스 모드)
# 사용법: bash scripts/check_docs.sh

claude -p "Review all .md files in the project root and docs/ folder. For each file, verify that: (1) referenced file paths actually exist, (2) described features match actual implementations in the codebase, (3) deployment URLs and config values are current, (4) completion percentages in CLAUDE.md match actual code state. List all discrepancies with file name and line reference." \
  --allowedTools "Read,Glob,Grep,Bash"
