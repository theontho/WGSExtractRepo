from core.common import WGSE_FP, OSTYPE, get_reflib_dir, rmx, cpx, BASHX, ver_comp
from core.logging import echo_tee, askyesno
from core.genomes import get_and_process_refgenome, read_genomes_file

def library_menu():
    """Interactive menu for reference genome management."""
    reflibdir = get_reflib_dir()
    genomes = read_genomes_file()
    
    if not genomes:
        echo_tee("Error: No genomes found in library.")
        return

    echo_tee("\n" + "-"*80)
    echo_tee("WGS Extract Reference Library REFERENCE GENOME Installation and Update")
    echo_tee("-"*80)
    echo_tee(f"Located at {reflibdir}")
    echo_tee("[See the Users Manual for more information about these Reference Genomes]")
    echo_tee("You can run the WGS Extract program while a Reference Genome is downloading.\n")

    options = ["Exit", "Recommended (@US NIH)", "Recommended (@EU EBI)"]
    for g in genomes:
        options.append(g.get("Library command menu string", "Unknown"))

    while True:
        for i, opt in enumerate(options):
            print(f"{i+1}) {opt}")
        
        try:
            choice_idx = int(input(f"Choose which Reference Genome(s) to process now (1 to Exit): ")) - 1
        except (ValueError, EOFError):
            continue

        if choice_idx < 0 or choice_idx >= len(options):
            echo_tee("Invalid option.")
            continue

        choice = options[choice_idx]
        if choice == "Exit":
            echo_tee("Exiting the WGS Extract Reference Genome Library script.")
            break
        
        elif choice == "Recommended (@US NIH)":
            recs = ["hs38 (Nebula) (@NIH) (Rec)", "hs37d5 (Dante) (@NIH) (Rec)", "T2T_v2.0 (PGP/HPP chrN) (Rec)"]
            for g in genomes:
                if g.get("Library command menu string") in recs:
                    get_and_process_refgenome(g)
            echo_tee("Finished with Recommended (@US NIH).")
        
        elif choice == "Recommended (@EU EBI)":
            recs = ["hs38 (Nebula) (@EBI) (Rec)", "hs37d5 (Dante) (@EBI) (Rec)", "T2T_v2.0 (PGP/HPP chrN) (Rec)"]
            for g in genomes:
                if g.get("Library command menu string") in recs:
                    get_and_process_refgenome(g)
            echo_tee("Finished with Recommended (@EU EBI).")
        
        else:
            # Matches specific genome
            for g in genomes:
                if g.get("Library command menu string") == choice:
                    get_and_process_refgenome(g)
                    break
        
        echo_tee("")

if __name__ == "__main__":
    library_menu()
