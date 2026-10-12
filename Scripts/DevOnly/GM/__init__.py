import importlib

from . import SurvivorCommands


def register():
    SurvivorCommands.register()


def reload_commands():
    global SurvivorCommands
    SurvivorCommands = importlib.reload(SurvivorCommands)
    SurvivorCommands.register()
