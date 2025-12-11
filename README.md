# PhD
Monorepo for PhD work


## Jupyter notebooks

This repo should ignore changes to the outputs of jupyter notebook cells, committing only code changes. This must be configured manually during checkout. Instructions originally from [StackOverflow](https://stackoverflow.com/a/58004619/3861922).

Create a `.gitattributes` file in the root directory containing `*.ipynb filter=strip-notebook-output`. This file is already committed to the repo.

Add a git filter to clean the outputs from a notebook when adding it
```
git config filter.strip-notebook-output.clean '`git rev-parse --show-toplevel`/.venv/jupyter nbconvert --ClearOutputPreprocessor.enabled=True --to=notebook --stdin --stdout --log-level=ERROR'
```

Now the outputs will be stripped when adding a notebook, but will remain unchanged locally.

To override and commit the outputs from a specific file, run `git -c filter.strip-notebook-output.clean= add <path to your notebook>`