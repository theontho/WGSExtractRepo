## WGS Extract Beta v4 Installation & Reference Library Scripts subdirectory

Full source code and documentation at https://wgse.bio/

These are support scripts for the Installation and management of the
WGS Extract release.

Those starting with 'z' should not be called directly.  They are only
sourced internally by other scripts here and in the main installation
directory above. They support common script functions used by multiple
scripts as well as support the install and uninstall main OS scipts in
the main installation folder above.

Non-'z' scripts are delivered with the program package. They are there
for manipulating the reference genome library. And are called
instead of sourced.  library_common.sh is called from the OS specific
Library wrappers and implements the command-line level library command.
*refgenome are called from library_common and the python reference library
code to get and process the reference genomes in the reference library.

The `make_release*` files are for making a WGS Extract distribution and
normally deleted during install so the user never sees them.  But are
including in the installer package to make the packages complete.

Eventually all (or most) of this code should be moved to python. That is
when a Bioconda / Miromamba can be applied to all platforms.
