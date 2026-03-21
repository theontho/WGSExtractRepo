import os
import sys


def generate_map(fai_path, out_path):
    with open(fai_path) as f_in, open(out_path, "w") as f_out:
        for line in f_in:
            parts = line.strip().split("\t")
            if len(parts) < 2:
                continue
            chrom = parts[0]
            length = int(parts[1])
            f_out.write(f">{chrom}\n")

            # Write sequence of 'A' (or 'C') in chunks of 60
            chunk = "A" * 60
            full_chunks = length // 60
            rem = length % 60

            for _ in range(full_chunks):
                f_out.write(chunk + "\n")
            if rem > 0:
                f_out.write("A" * rem + "\n")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: generate_full_map.py <ref.fa.fai> <out.fa>")
        sys.exit(1)
    generate_map(sys.argv[1], sys.argv[2])
