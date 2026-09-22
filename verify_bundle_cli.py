import hashlib
import json
import sys


def main():
    try:
        with open(sys.argv[1], encoding="utf-8") as handle:
            bundle = json.load(handle)
        array_json = json.dumps(
            bundle["evidence"], sort_keys=True, separators=(",", ":")
        )
        expected = hashlib.sha256(array_json.encode()).hexdigest()
        print("VALID" if expected == bundle["bundle_hash"] else "TAMPERED")
    except (IndexError, OSError, KeyError, TypeError, ValueError):
        print("TAMPERED")


if __name__ == "__main__":
    main()
