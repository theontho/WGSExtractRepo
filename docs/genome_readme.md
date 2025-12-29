WGS Extract v4 Reference Library subsystem; Reference Genomes Directory

Do not worry if this folder (genomes/ is empty.  It just means you have not yet downloaded and
 installed a reference genome.  Once downloaded, it will be processed and additional index and 
 support files are stored here. You can install reference genomes either by the Library.*** 
 command or in the program when a required reference genome is found missing.

This folder can grow in size.  Each reference genome is about 1 GByte in size.  
 Indices needed for alignment take another 5 GB. As you add more reference genomes
 that are used for alignment, it quickly becomes the largest folder of the WGS Extract
 installation (sans your Output Directory, Source (BAMs) Directory, and the Temporary
 Files folder during big jobs.

Between upgrades of the tool, we work to preserve this folder and its content so you do
 not have to download and generate the index files again.

The whole reference library including this genomes/ folder can be relocated to another 
 disk where you may have more space. It is more a read-once folder by nature.  Wireless 
 network attached storage will not likely work but is feasible.  The installer and 
 program will pick up on your relocation setting during upgrades as well.  The relocation 
 setting is made inside the main WGS Extract program and stored in its settings file in
 your home directory.