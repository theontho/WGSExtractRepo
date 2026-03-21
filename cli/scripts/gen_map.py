import sys

len = int(sys.argv[1])
print(">chr21")
[sys.stdout.write("A" * 60 + "\n") for _ in range(len // 60)]
sys.stdout.write("A" * (len % 60) + "\n")
