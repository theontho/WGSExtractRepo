import os
import subprocess
import tempfile
import pytest
from pathlib import Path

# Path to aconv.py
ACONV_PY = Path(__file__).resolve().parent.parent / "program" / "aconv.py"

@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory() as tmp:
        yield Path(tmp)

def create_combined_kit(path):
    content = [
        "#RSID\tCHROM\tPOS\tRESULT",
        "rs1\t1\t100\tAA",
        "rs2\t1\t200\tGT",
        "rs3\t2\t300\tCC",
        "rs4\tX\t400\tA",
        "rs5\tMT\t500\tG"
    ]
    with open(path, "w") as f:
        f.write("\n".join(content) + "\n")

def create_templates(base_dir, format_name, suffix, head_content, body_lines):
    head_dir = base_dir / "raw_file_templates" / "head"
    body_dir = base_dir / "raw_file_templates" / "body"
    head_dir.mkdir(parents=True, exist_ok=True)
    body_dir.mkdir(parents=True, exist_ok=True)
    
    with open(head_dir / f"{format_name}{suffix}", "w") as f:
        f.write(head_content + "\n")
    
    with open(body_dir / f"{format_name}{suffix}", "w") as f:
        f.write("\n".join(body_lines) + "\n")

def run_aconv(format_name, source, target_base, ref_dir):
    cmd = [
        "python3",
        str(ACONV_PY),
        format_name,
        str(source),
        str(target_base),
        str(ref_dir) + "/" # aconv.py appends "raw_file_templates/" to this
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result

def test_23andme_v3_format(temp_dir):
    source = temp_dir / "CombinedKit.txt"
    create_combined_kit(source)
    
    target_base = temp_dir / "output"
    
    head = "# 23andMe V3 Header\nrsid\tchromosome\tposition\tgenotype"
    body = [
        "rs1\t1\t100",
        "rs2\t1\t200",
        "rs3\t2\t300"
    ]
    create_templates(temp_dir, "23andMe_V3", ".txt", head, body)
    
    res = run_aconv("23andMe_V3", source, target_base, temp_dir)
    assert res.returncode == 0
    
    output_file = temp_dir / "output_23andMe_V3.txt"
    assert output_file.exists()
    
    with open(output_file, "r") as f:
        lines = f.readlines()
    
    assert lines[0].strip() == "# 23andMe V3 Header"
    assert lines[1].strip() == "rsid\tchromosome\tposition\tgenotype"
    assert lines[2].strip() == "rs1\t1\t100\tAA"
    assert lines[3].strip() == "rs2\t1\t200\tGT"
    assert lines[4].strip() == "rs3\t2\t300\tCC"

def test_ftdna_v2_format(temp_dir):
    source = temp_dir / "CombinedKit.txt"
    create_combined_kit(source)
    
    target_base = temp_dir / "output"
    
    head = "RSID,CHROMOSOME,POSITION,RESULT"
    body = [
        '"rs1","1","100",',
        '"rs2","1","200",',
        '"rs3","2","300",'
    ]
    create_templates(temp_dir, "FTDNA_V2", ".csv", head, body)
    
    res = run_aconv("FTDNA_V2", source, target_base, temp_dir)
    assert res.returncode == 0
    
    output_file = temp_dir / "output_FTDNA_V2.csv"
    assert output_file.exists()
    
    with open(output_file, "r") as f:
        lines = f.readlines()
    
    assert lines[0].strip() == "RSID,CHROMOSOME,POSITION,RESULT"
    
    # Based on our analysis of aconv.py, we suspect it is currently BROKEN.
    # It will likely produce '"rs1","1","100",\tAA'
    expected = '"rs1","1","100","AA"'
    actual = lines[1].strip()
    assert actual == expected, f"FTDNA V2 format is incorrect: {actual}"

def test_ancestry_v1_format(temp_dir):
    source = temp_dir / "CombinedKit.txt"
    create_combined_kit(source)
    
    target_base = temp_dir / "output"
    
    head = "# Ancestry V1 Header\nrsid\tchromosome\tposition\tallele1\tallele2"
    # Ancestry_V1 expects 4 files
    create_templates(temp_dir, "Ancestry_V1_1", ".txt", "", ["rs1\t1\t100"])
    create_templates(temp_dir, "Ancestry_V1_2", ".txt", "", ["rs2\t1\t200"])
    create_templates(temp_dir, "Ancestry_V1_3", ".txt", "", ["rs3\t2\t300"])
    create_templates(temp_dir, "Ancestry_V1_4", ".txt", "", [])
    # We also need the head file with the base name
    head_dir = temp_dir / "raw_file_templates" / "head"
    with open(head_dir / "Ancestry_V1.txt", "w") as f:
        f.write(head + "\n")
    
    res = run_aconv("Ancestry_V1", source, target_base, temp_dir)
    assert res.returncode == 0
    
    output_file = temp_dir / "output_Ancestry_V1.txt"
    assert output_file.exists()
    
    with open(output_file, "r") as f:
        lines = f.readlines()
    
    assert lines[0].strip() == "# Ancestry V1 Header"
    assert lines[1].strip() == "rsid\tchromosome\tposition\tallele1\tallele2"
    
    # Expected: rs1\t1\t100\tA\tA
    # Current aconv.py: rs1\t1\t100\tAA
    
    expected = "rs1\t1\t100\tA\tA"
    actual = lines[2].strip()
    assert actual == expected, f"Ancestry V1 format is incorrect: {actual}"

def test_no_call_handling(temp_dir):
    source = temp_dir / "CombinedKit.txt"
    create_combined_kit(source)
    
    target_base = temp_dir / "output"
    
    head = "rsid\tchromosome\tposition\tgenotype"
    body = [
        "rs_missing\t1\t999"
    ]
    create_templates(temp_dir, "23andMe_V3", ".txt", head, body)
    
    res = run_aconv("23andMe_V3", source, target_base, temp_dir)
    assert res.returncode == 0
    
    output_file = temp_dir / "output_23andMe_V3.txt"
    with open(output_file, "r") as f:
        lines = f.readlines()
    
    assert lines[1].strip() == "rs_missing\t1\t999\t--"
    
    # Expected for Ancestry: 00 for no-call
    # Actually for Ancestry it should be 0\t0
    create_templates(temp_dir, "Ancestry_V1_1", ".txt", "", ["rs_missing\t1\t999"])
    create_templates(temp_dir, "Ancestry_V1_2", ".txt", "", [])
    create_templates(temp_dir, "Ancestry_V1_3", ".txt", "", [])
    create_templates(temp_dir, "Ancestry_V1_4", ".txt", "", [])
    head_dir = temp_dir / "raw_file_templates" / "head"
    with open(head_dir / "Ancestry_V1.txt", "w") as f:
        f.write("rsid\tchromosome\tposition\tallele1\tallele2\n")

    run_aconv("Ancestry_V1", source, target_base, temp_dir)
    output_file_anc = temp_dir / "output_Ancestry_V1.txt"
    with open(output_file_anc, "r") as f:
        lines_anc = f.readlines()
    
    assert lines_anc[1].strip() == "rs_missing\t1\t999\t0\t0"

def test_myheritage_v1_format(temp_dir):
    source = temp_dir / "CombinedKit.txt"
    create_combined_kit(source)
    target_base = temp_dir / "output"
    head = "RSID,CHROMOSOME,POSITION,RESULT"
    body = ['"rs1","1","100",', '"rs2","1","200",']
    create_templates(temp_dir, "MyHeritage_V1", ".csv", head, body)
    res = run_aconv("MyHeritage_V1", source, target_base, temp_dir)
    assert res.returncode == 0
    output_file = temp_dir / "output_MyHeritage_V1.csv"
    with open(output_file, "r") as f:
        lines = f.readlines()
    assert lines[1].strip() == '"rs1","1","100","AA"'

def test_ldna_v1_format(temp_dir):
    source = temp_dir / "CombinedKit.txt"
    create_combined_kit(source)
    target_base = temp_dir / "output"
    head = "rsid\tchromosome\tposition\tgenotype"
    body = ["rs1\t1\t100", "rs2\t1\t200"]
    create_templates(temp_dir, "LDNA_V1", ".txt", head, body)
    res = run_aconv("LDNA_V1", source, target_base, temp_dir)
    assert res.returncode == 0
    output_file = temp_dir / "output_LDNA_V1.txt"
    with open(output_file, "r") as f:
        lines = f.readlines()
    assert lines[1].strip() == "rs1\t1\t100\tAA"

if __name__ == "__main__":
    pytest.main([__file__])
