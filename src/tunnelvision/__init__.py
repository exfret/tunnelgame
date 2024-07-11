import sys

from tunnelvision.gameloop import run


def main():
    if len(sys.argv) == 1:
        run("tunnel/01-railroaded/intro.yaml", packaged=True)
        #run("demo.yaml", packaged=True)
    else:
        run(sys.argv[1], packaged=False)
