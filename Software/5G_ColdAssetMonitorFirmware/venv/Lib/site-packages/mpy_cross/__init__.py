import subprocess
from glob import glob
from os.path import join, dirname, abspath

__all__ = ['mpy_cross', 'run']

mpy_cross = abspath(glob(join(dirname(__file__), 'mpy-cross*'))[0])


def run(*args, **kwargs):
    return subprocess.Popen([mpy_cross] + list(args), **kwargs)
