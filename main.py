"""Used to start the game."""
from model import worlds
from gui import simple_gui
from control.main import GameControl


def main():
    world = worlds.Multiverse.create_debug_world()
    control = GameControl(world)
    gui = simple_gui.GUI(world, control)
    gui.run()


if __name__ == "__main__":
    main()
