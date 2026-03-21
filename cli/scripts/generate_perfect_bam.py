import random

import pysam


def create_perfect_bam(ref_path, out_bam):
    # Read the first chromosome length
    with open(ref_path + ".fai") as f:
        line = f.readline().strip().split()
        chrom = line[0]
        length = int(line[1])

    header = {
        "HD": {"VN": "1.5", "SO": "coordinate"},
        "SQ": [{"SN": chrom, "LN": length}],
        "RG": [{"ID": "rg1", "SM": "sample1"}],
    }

    with pysam.AlignmentFile(out_bam, "wb", header=header) as outf:
        # Generate 50,000 pairs (100,000 reads) to ensure high coverage
        # Delly wants --> <-- orientation.
        # R1 is forward, R2 is reverse.
        for i in range(50000):
            # Pick a random start position
            # Read length 100, insert size 300
            start = random.randint(0, length - 400)

            # Read 1 (Forward)
            r1 = pysam.AlignedSegment()
            r1.query_name = f"read_{i}"
            r1.query_sequence = "A" * 100
            r1.flag = 99  # paired, properly paired, mate reverse, first in pair
            r1.reference_id = 0
            r1.reference_start = start
            r1.mapping_quality = 60
            r1.cigar = ((0, 100),)  # 100M
            r1.next_reference_id = 0
            r1.next_reference_start = start + 200
            r1.template_length = 300
            r1.tags = (("RG", "rg1"),)

            # Read 2 (Reverse)
            r2 = pysam.AlignedSegment()
            r2.query_name = f"read_{i}"
            r2.query_sequence = "T" * 100
            r2.flag = 147  # paired, properly paired, read reverse, second in pair
            r2.reference_id = 0
            r2.reference_start = start + 200
            r2.mapping_quality = 60
            r2.cigar = ((0, 100),)  # 100M
            r2.next_reference_id = 0
            r2.next_reference_start = start
            r2.template_length = -300
            r2.tags = (("RG", "rg1"),)

            outf.write(r1)
            outf.write(r2)


if __name__ == "__main__":
    create_perfect_bam("out/fake_30x/fake_ref.fa", "out/fake_30x/perfect.bam")
