The goal of this test suite is to test the installer & launching the program in the 6 different install OS environment targets we have.  Since it's multi OS, this adds a lot of complexity.  

We have noticed testing from a host on a VM adds a lot of subtle bugs that wouldn't be there if you tested on bare metal.  There is a good chance we will abandon VM testing beyond WSL.