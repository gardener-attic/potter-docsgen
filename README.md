# Potter Docs Generator

This repository contains the build tools, configuration, web framework, etc. for the generating the Potter docs. For site source content including documentation, see the `/docs` directory in the [/gardener/potter-hub](https://github.com/gardener/potter-hub) and [/gardener/potter-controller](https://github.com/gardener/potter-controller) repos. The repository of the generated website is [/gardener/potter-docs](https://github.com/gardener/potter-docs). It is served via [GitHub Pages](https://pages.github.com/).

## Dev Setup

**Prerequisites**

- Python 3.8
- [Hugo](https://gohugo.io/) (should be installed in the same version as in the CI/CD container, see the [website build script](./.ci/build_website.py) for the correct version)

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

Depending on whether you want to work on the actual CI script or want to run the website with local changes, perform the actions described in the following sections.

**Running the website with local changes** 

When you want to run the website with local changes in the potter-hub or potter-controller repos, you should run the website build script via the following command:

```
./build_website.py --skip-build-and-commit=True --include-current-version-only=True
```

This will copy the `/docs` directories from the local potter-hub and potter-controller repos into `<potter-docsgen-repo-path>/hugo/content` and generate some metadata for Hugo. It will only include the current version of the `docs` directories on your filesystem.

Now execute the following commands:

```
cd $SOURCE_PATH/hugo
hugo serve
```

This will startup a local HTTP server which Hugo uses to serve the website.

When perfoming changes in the `/docs` folder of the local potter-hub and potter-controller repos, you must rerun the website build script in order to sync the changes into the `/hugo/content` directory. 

Sometimes it might also be necessary to stop `hugo serve`, manually delete the `/docs` directories from `/hugo/content`, rerun the website build script, and restart `hugo serve`.

**Working on the website build script** 

When you want to work on the website build script, you should run the website build script via the following command:

```
./build_website.py
```

This will build the website, write the build output to the `$POTTER_DOCS_PATH` repo, and actually commit all changes to the repo. ***You therefore shouldn't push the `$POTTER_DOCS_PATH` repo to origin.***
