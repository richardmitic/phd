from typing import Optional
import importlib
from git import Repo, Tree
from pathlib import Path
from hashlib import sha1

def _find_subtree(tree, name) -> Tree:
    for t in tree:
        if t.abspath.endswith(name):
            return t

def _get_git_status(module) -> Optional[str]:
    
    repo = Repo(search_parent_directories=True)
    repo_top = Path(repo.git.rev_parse("--show-toplevel"))
    changed_files = {repo_top / d.a_path for d in repo.index.diff(None)}
    
    if Path(module.__file__).name == "__init__.py":
        # This is a directory module
        toplevel = Path(module.__file__).parent.relative_to(repo_top)
        tree = repo.tree()
        for part in toplevel.parts:
            tree = _find_subtree(tree, part)
            algo_files = {Path(x.abspath) for x in tree}
        
        # If there are any files changed in this algorithm, compute a new hash
        if (algo_files & changed_files):
            module_hash = sha1()
            for blob in tree:
                module_hash.update(repo.git.hash_object(blob.abspath).encode('utf-8'))
            return module_hash.digest().hex()

    else:
        # This is a single file. If it has changed, compute a new hash
        toplevel = Path(module.__file__).relative_to(repo_top)
        if toplevel in changed_files:
            return repo.git.hash_object(toplevel.absolute)
    

def get_module_version(module) -> str:
    if isinstance(module, str):
        module = importlib.import_module(module)
    dirty_hash = _get_git_status(module)
    if dirty_hash:
        return f"{module.VERSION}-{dirty_hash}"
    else:
        return module.VERSION
    # if isinstance(module, str):
    #     return importlib.import_module(module).VERSION
    # else:
    #     return module.VERSION


    