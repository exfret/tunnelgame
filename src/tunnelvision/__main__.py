import sys

from tunnelvision.gameloop import run

def main():
    if len(sys.argv) == 1:
        run("tunnel/02-lemeny/intro.yaml", packaged=True)
    else:
        run(sys.argv[1], packaged=False)

if __name__ == "__main__":
    main()