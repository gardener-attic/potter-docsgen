#!/usr/bin/env python3

import argparse
from collections import deque
from distutils.dir_util import copy_tree
from distutils.version import LooseVersion
import git
import json
import os
import requests
import semver
import shutil
import subprocess
import tarfile
import tempfile

websiteGeneratorRepoDir = os.path.abspath(os.environ["SOURCE_PATH"])
hubRepoDir = os.path.abspath(os.environ["POTTER_HUB_PATH"])
controllerRepoDir = os.path.abspath(os.environ["POTTER_CONTROLLER_PATH"])
generatedWebsiteRepoDir = os.path.abspath(os.environ["POTTER_DOCS_PATH"])

parser = argparse.ArgumentParser()
parser.add_argument("--includedReleases", type=int, default=3, help="number of releases to build the docs")
args = parser.parse_args()

class HugoClient:
    def __init__(self):
        self.binURL = "https://github.com/gohugoio/hugo/releases/download/v0.78.1/hugo_extended_0.78.1_Linux-64bit.tar.gz"
        self.binPath = "hugo"
        self.sourcePath = f"{websiteGeneratorRepoDir}/hugo"
        self.outPath = f"{generatedWebsiteRepoDir}/docs"
        if not self.isHugoInstalled():
            self.installHugo()
        
        print("sourcePath", self.sourcePath)
        print("outPath", self.outPath)

    def isHugoInstalled(self):
        try:
            command = [self.binPath, "version"]
            result = subprocess.run(command, capture_output=True, text=True)
            print(f"command {command} returned with result: {result}")
            return result.returncode == 0
        except OSError:
            return False

    def installHugo(self):
        tempdir = tempfile.gettempdir()
        print(f"hugo not found in path, installing it to {tempdir}")
        self.binPath = f"{tempdir}/hugo"
        res = requests.get(self.binURL, stream=True)
        with tarfile.open(fileobj=res.raw, mode='r|*') as tar:
            res.raw.seekable = False
            for member in tar:
                if not member.name == "hugo":
                    continue

                fileobj = tar.extractfile(member)
                with open(self.binPath, "wb") as outfile:
                    outfile.write(fileobj.read())
                os.chmod(self.binPath, 744)

    def runBuild(self):
        print("starting hugo build")

        if os.path.exists(self.outPath):
            shutil.rmtree(self.outPath)

        command = [self.binPath, "--source", self.sourcePath, "--destination", self.outPath]
        result = subprocess.run(command, capture_output=True)
        if result.returncode != 0:
            raise Exception(f"website build failed: hugo returned {result}")

def getLatestReleaseTags(gitRepo, numberOfIncludedReleases):
    tags = gitRepo.tags

    # filter out tags that start with "v". these aren't from us but came in from the kubeapps merge
    tags = [tag.name for tag in tags if not tag.name.startswith("v")]
    
    # remove tags where higher patch releases are available
    # [0.0.1, 0.1.0, 0.1.1. 0.1.2, 0.2.0] --> [0.0.1, 0.1.2, 0.2.0]
    tags = removePatchedVersions(tags)

    return tags[-numberOfIncludedReleases:]

def copyDocs(componentName, srcRepoDir):
    print(f"processing component {componentName} in repo {srcRepoDir}")

    gitRepo = git.Repo(srcRepoDir)
    latestReleaseTags = getLatestReleaseTags(gitRepo, args.includedReleases)
    revisions = []
    docsDir = f"{srcRepoDir}/docs"

    for releaseTag in latestReleaseTags[:-1]:
        print(f"processing version {releaseTag}")
        gitRepo.git.checkout(releaseTag)

        if not os.path.isdir(docsDir):
            print(f"skip copy: {docsDir} doesn't exist.")
            continue

        if not os.path.isfile(f"{docsDir}/_index.md"):
            print(f"skip copy: {docsDir}/_index.md doesn't exist.")
            continue

        revision = {
            "version": f"{releaseTag}",
            "dirPath": f"{componentName}-docs-{releaseTag}",
            "url": f"/{componentName}-docs-{releaseTag}",
        }
        revisions.append(revision)

        print(f"copy {docsDir}")
        copy_tree(src=docsDir, dst=f"{websiteGeneratorRepoDir}/hugo/content/{revision['dirPath']}")

    # latest revision must be in special directory
    latestRevision = {
        "version": f"{latestReleaseTags[-1]}",
        "dirPath": f"{componentName}-docs",
        "url": f"/{componentName}-docs",
    }
    gitRepo.git.checkout(latestRevision["version"])
    copy_tree(src=docsDir, dst=f"{websiteGeneratorRepoDir}/hugo/content/{latestRevision['dirPath']}")
    revisions.append(latestRevision)

    # include docs from main branch
    gitRepo.git.checkout("master")
    with open(f"{srcRepoDir}/VERSION") as f:
        content = f.readlines()
    if len(content) != 1:
        raise Exception(f"{srcRepoDir}/VERSION is invalid. the file must only contain one line with the current version.")
    mainBranchVer = content[0].strip()
    mainBranchRevision = {
        "version": f"{mainBranchVer}",
        "dirPath": f"{componentName}-docs-{mainBranchVer}",
        "url": f"/{componentName}-docs-{mainBranchVer}",
    }
    copy_tree(src=docsDir, dst=f"{websiteGeneratorRepoDir}/hugo/content/{mainBranchRevision['dirPath']}")
    revisions.append(mainBranchRevision)

    with open(f"{websiteGeneratorRepoDir}/hugo/data/{componentName}-revisions.json", "w") as outfile:
        json.dump(revisions[-args.dropdownVersions-1:-1], outfile)

def buildWebsite():
    hugoClient = HugoClient()
    copyDocs("hub", hubRepoDir)
    copyDocs("controller", controllerRepoDir)
    hugoClient.runBuild()

def commitChangesToGeneratedWebsiteRepo():
    print(f"committing changes to {generatedWebsiteRepoDir}")
    generatedWebsiteRepo = git.Repo(generatedWebsiteRepoDir)
    generatedWebsiteRepo.git.add(".")
    generatedWebsiteRepo.git.commit("-m", "updates website")

def removePatchedVersions(tags): 
    tags.sort(key=LooseVersion)
    tags = deque(tags)

    filteredTags = []
    while tags:
        currentTag = tags.popleft()
        currentVer = semver.VersionInfo.parse(currentTag)

        if tags:
            nextTag = tags[0]
            nextVer = semver.VersionInfo.parse(nextTag)

            if not (currentVer.major == nextVer.major and currentVer.minor == nextVer.minor):
                filteredTags.append(currentTag)
        else:
            filteredTags.append(currentTag)
    return filteredTags

# hugo_extended doesn't run on a vanilla Alpine Linux (which is the base image of the CI/CD pipeline containers).
# We therefore must install additional packages when running inside a container of the CI/CD pipeline.
def installAdditionalLinuxPackages():
    print("installing additional packages")
    command = ["apk", "add", "--update", "libc6-compat", "libstdc++"]
    result = subprocess.run(command, capture_output=True, text=True)
    print(f"command {command} returned with result: {result}")
    if result.returncode != 0:
        raise Exception(f"command {command} failed")

def isRunningInCICDPipelineContainer():
    return os.getenv("CONCOURSE_CURRENT_TEAM") != None

if __name__ == "__main__":
    print("starting website build")
    if isRunningInCICDPipelineContainer():
        installAdditionalLinuxPackages()
    buildWebsite()
    commitChangesToGeneratedWebsiteRepo()
    print("finished website build")
