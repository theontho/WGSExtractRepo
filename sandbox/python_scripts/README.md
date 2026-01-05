The goal of this project is to replace the functionality of the `scripts/` folder with a python version of the scripts, this removes the need for bash as a dependency in this project, which tends to be more fragile than python in a cross platform and coding context.  

We will still need some sort of script to `bootstrap/` the python install although.  We might embed python in the future, use `pyinstaller`, who knows.

Since this is an AI translation of the bash scripts to python, it aims to be nearly 1:1 functionality wise, unlike most rewrites.  This will hopefully make it fast to deliver. 