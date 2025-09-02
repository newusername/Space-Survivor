from data import model
from gui import simple_gui
from data.control import GameControl

def main():
    world = model.Multiverse.create_debug_world()
    control = GameControl(world)
    gui = simple_gui.GUI(world, control)
    gui.run()


if __name__ == "__main__":
    main()
