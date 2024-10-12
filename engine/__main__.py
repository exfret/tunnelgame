import sys

from engine import config, view
from engine.gameloop import run

config.view = view.CLIView()

def main():
    if len(sys.argv) == 1:
        run("tunnel/03-abstract/intro.yaml", packaged=True)
    else:
        run(sys.argv[1], packaged=False)

if __name__ == "__main__":
    main()