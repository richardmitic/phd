import importlib
from git import Repo

def get_git_status(module):
    if isinstance(module, str):
        module = importlib.import_module(module)
    repo = Repo.init()
    print(module.__file__)
    changed_files = [d.a_path for d in repo.index.diff(None)]
    # repo.untracked_files
    

def get_module_version(module) -> str:
    if isinstance(module, str):
        return importlib.import_module(module).VERSION
    else:
        return module.VERSION


    