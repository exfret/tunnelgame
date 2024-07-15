import sys

from tunnelvision.gameloop import run


def main():
    if len(sys.argv) == 1:
        run("tunnel/02-lemeny/intro.yaml", packaged=True)
        #run("demo.yaml", packaged=True)
    else:
        run(sys.argv[1], packaged=False)
