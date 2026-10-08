"""Compact evidence for the same complete-chain differential used by the fast gate."""
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.chain_checks import differential_chain
from scripts.chain_driver import build_chain
from scripts.consensus_evidence import begin_report,finish_report


def main():
    paths=begin_report('full-chain-v1'); manifest=paths[2]
    executable=build_chain()
    finish_report(paths,differential_chain(executable),manifest,executable=executable)


if __name__=='__main__': main()
