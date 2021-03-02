# Potter Docs Generator

This repository contains the build tools, configuration, web framework, etc. for the generating the Potter docs. For site source content including documentation, see the `/docs` directory in the [/gardener/potter-hub](https://github.com/gardener/potter-hub) and [/gardener/potter-controller](https://github.com/gardener/potter-controller) repos. The repository of the generated website is [/gardener/potter-docs](https://github.com/gardener/potter-docs). It is served via [GitHub Pages](https://pages.github.com/).

## Dev Setup

**Prerequisites**

- Python 3.8
- [Hugo](https://gohugo.io/)

**Step 1**

Clone all involved GitHub repositories to your local machine. Export the repo root directories via the corresponding environment variables.

```bash
$ git clone https://github.com/gardener/potter-hub
$ git clone https://github.com/gardener/potter-controller
$ git clone https://github.com/gardener/potter-docs
$ git clone https://github.com/gardener/potter-docsgen

export SOURCE_PATH="<path-to-potter-docsgen-repo>"
export POTTER_HUB_PATH="<path-to-potter-hub-repo>"
export POTTER_CONTROLLER_PATH="<path-to-potter-controller-repo>"
export POTTER_DOCS_PATH="<path-to-potter-docs-repo>"
```

**Step 2** 

Create a Python virtual environment in the `.ci` directory and activate it. Then install the Python package `gardener-cicd-libs` via pip.

```bash
$ cd <path-to-potter-docsgen-repo>/.ci
$ virtualenv -p <path-to-python-3.8> env
$ source env/bin/activate
$ pip install gardener-cicd-libs
```

**Step 3** 

Run the website build script via `python ./build_website.py`. This will copy the `/docs` directories from the local potter-hub and potter-controller repos into `<potter-docsgen-repo-path>/hugo/content`, for the last 3 releases (can be changed via the parameter `--includedReleases`). After that, the script runs the Hugo build to generate the website and commits the build output to the local potter-docs repo. ***It will not automatically push these changes into the remote repo.***

**Step 4** 

Run `hugo serve` in the `<potter-docsgen-repo-path>/hugo` directory. When perfoming changes in the `/docs` folder of the local potter-hub and potter-controller repos, you must reperform *Step 3* in order to sync the changes into the `/hugo/content` directory. 

Sometimes it might also be necessary to stop `hugo serve`, manually delete the `/docs` directories from `/hugo/content`, rerun the website build script, and restart `hugo serve`.

