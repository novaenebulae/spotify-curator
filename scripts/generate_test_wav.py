import argparse
import math
import struct
import wave
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True, help="Output WAV path")
    parser.add_argument("--seconds", type=float, default=2.0)
    parser.add_argument("--sr", type=int, default=44100)
    parser.add_argument("--freq", type=float, default=440.0)
    args = parser.parse_args()

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    n = int(args.sr * args.seconds)
    amp = 0.2
    with wave.open(str(out), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(args.sr)
        for i in range(n):
            v = amp * math.sin(2 * math.pi * args.freq * (i / args.sr))
            w.writeframes(struct.pack("<h", int(v * 32767)))

    print(out)


if __name__ == "__main__":
    main()

