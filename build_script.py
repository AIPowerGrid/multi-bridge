import PyInstaller.__main__
import os
import shutil

def create_binary():
    PyInstaller.__main__.run([
        'main.py',
        '--onefile',
        '--name=openai_grid_bridge',
        '--add-data=bridgeData.yaml:.',
    ]) 