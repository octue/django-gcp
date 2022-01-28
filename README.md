<!--- The following badges don't work because they're templated... uncomment when filled out
[![PyPI version](https://badge.fury.io/py/{{library_name}}.svg)](https://badge.fury.io/py/{{library_name}})
[![codecov](https://codecov.io/gh/{{codecov_username}}/{{library_name}}/branch/master/graph/badge.svg)](https://codecov.io/gh/{{codecov_username}}/{{library_name}})
[![Documentation Status](https://readthedocs.org/projects/{{library_name}}/badge/?version=latest)](https://{{library_name}}.readthedocs.io/en/latest/?badge=latest)
--->

[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/pre-commit/pre-commit)
[![black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/ambv/black)

> **NOTE: The checks/actions on this template repository WILL NEVER PASS. That's because they're templated ready for your variables, so they don't make sense to GitHub!**

# Rabid Armadillo (aka Django App Template)

This is a template repository for when you want to create a new django app. It gives you, out of the box:

- Template django app, with:

  - Example **websocket consumer** (and example of how to test it asynchronously)
  - Example **Abstract Model** (and example of how to test it)
  - Example **Concrete Model** (and example of how to test it)

- Preconfigured testing with coverage for a range of python, django versions using tox

- Preconfigured github actions CI

- Preconfigured style guide and other checks using pre-commit

- Preconfigured docs in .rst format (to publish to your_project.readthedocs.io)

- Complete `.devcontainer` setup for use in VSCode complete with a postgres database service

## How To Use This Template Repository

This is a template repository on GitHub. You can use it as a template when creating a new django app.

### Start a repo

Click the 'Use this Template' button (top right) on GitHub to create your own repository using this repo as a template.
Call it what you like, but we suggest the convention `django-your-library`.
In this example, let's say your github username is `armadillo-queen` and your new repository is called `django-rabid-armadillo`.

### Replace template items

Do find and replace throughout, working your way through this list of replacements

| Search               | Replace (Example)        | Description                                                                                                                                                                                                        |
| -------------------- | ------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| <your_repo_name>     | `django-rabid-armadillo` | The github repository name. Convention for django apps seems to be hyphenating rather than using snake case, but do what you want. Easiest thing is to make the package name on PyPi the same as the gh repo name. |
| <your_github_handle> | `armadillo-queen`        | Your github handle                                                                                                                                                                                                 |
| <copyright_owner>    | Tom Clark                | The copyright owner's name. Probably you, or your company                                                                                                                                                          |
| `rabid_armadillo`    | `rabid_armadillo`        | The module name of your app, which is importable in python (ie hyphens don't work. Stick to snake case!). Search and replace the whole of everything!                                                              |
| `RabidArmadillo`     |                          | Replace with the capitalised camel case version of your app name                                                                                                                                                   |
| `Rabid Armadillo`    | Rabid Armadillo          | Human-readable, capitalised, app name                                                                                                                                                                              |

### Update pyproject.toml

Add library requirements using poetry. If you don't know how to use it, yes it's a bit more painful than pip at first, but it's short term pain, medium term massive gains.

### Update `LICENSE` file and `docs/source/license.rst`

Change the contents to an appropriate license for your project. Don't delete the LICENSE file, because it's bundled on the manifest onto the pypi deployment.

License is currently MIT. Do what you like, I guess, but I humbly beg you to keep it open and permissive. There's
nothing more frustrating than finding a library that does what you need, and that you could contribute to, then not
being able to use it because it's GPL'd.

## Begin development

You should use poetry. It's easier and better than pip and pyenv. Open the project in codespace, a vscode .devcontainer or your favourite IDE or editor, then:

```
poetry install
```

Run the tests (nb the postgres ones might not work unless you have postgres set up locally, but sqlite should work)

```
tox
```

## Publish your app

We assume that you'll use github actions so see the `.github/workflows` folder for the process.

As background information, the Hitchiker's guide to python provides [an excellent, standard, method for creating python packages](http://docs.python-guide.org/en/latest/writing/structure/) and there's a good [set of instructions on PYPI](https://packaging.python.org/tutorials/distributing-packages/#uploading-your-project-to-pypi). You'll see in the workflows that we circumvent those processes and use poetry to do it for us.
