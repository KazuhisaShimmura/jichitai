
#!/usr/bin/env python3
import argparse
from grants_harvester.pipeline import run_pipeline

def main():
    ap = argparse.ArgumentParser(description="Grants Harvester")
    ap.add_argument("--sources", default="config/sources.yaml")
    ap.add_argument("--keywords", default="config/keywords.yaml")
    ap.add_argument("--out", default="out")
    args = ap.parse_args()

    out = run_pipeline(args.sources, args.keywords, args.out)
    print("Wrote:", out)

if __name__ == "__main__":
    main()
