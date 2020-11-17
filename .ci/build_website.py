#!/usr/bin/env python3

from distutils.dir_util import copy_tree
import git
import json
import os
import requests
import shutil
import subprocess
import tarfile
import tempfile

websiteGeneratorRepoDir = os.path.abspath(os.environ["SOURCE_PATH"])
hubRepoDir = os.path.abspath(os.environ["POTTER_HUB_PATH"])
controllerRepoDir = os.path.abspath(os.environ["POTTER_CONTROLLER_PATH"])
generatedWebsiteRepoDir = os.path.abspath(os.environ["POTTER_DOCS_PATH"])

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

def copyDocs(componentName, srcRepoDir):
    print(f"copy docs for {componentName}")
    
    with open(f"{websiteGeneratorRepoDir}/{componentName}-doc-versions.txt") as f:
        content = f.readlines()
    versions = [v.strip() for v in content]
    revisions = buildRevisions(componentName, versions)
    
    gitRepo = git.Repo(srcRepoDir)
    for revision in revisions:
        gitRepo.git.checkout(revision["version"])

        srcDir = f"{srcRepoDir}/docs"
        if not os.path.isdir(srcDir):
            print(f"skip version {revision['version']}: {srcDir} doesn't exist.")
            continue

        if not os.path.isfile(f"{srcDir}/_index.md"):
            print(f"skip version {revision['version']}: {srcDir}/_index.md doesn't exist.")
            continue

        print(f"copy version {revision['version']}")
        copy_tree(src=srcDir, dst=f"{websiteGeneratorRepoDir}/hugo/content/{revision['dirPath']}")

    with open(f"{websiteGeneratorRepoDir}/hugo/data/{componentName}-revisions.json", "w") as outfile:
        json.dump(revisions, outfile)

def buildWebsite():
    hugoClient = HugoClient()
    copyDocs("hub", hubRepoDir)
    copyDocs("controller", controllerRepoDir)
    hugoClient.runBuild()

def commitGeneratedWebsiteRepo():
    print(f"committing changes to {generatedWebsiteRepoDir}")
    generatedWebsiteRepo = git.Repo(generatedWebsiteRepoDir)
    generatedWebsiteRepo.git.add(".")
    generatedWebsiteRepo.git.commit("-m", "updates website")

def buildRevisions(componentName, docVersions):
    revisions = []
    currentRevision = {
        "version": f"{docVersions[0]}",
        "dirPath": f"{componentName}-docs",
        "url": f"/{componentName}-docs"
    }
    revisions.append(currentRevision)
    for docVersion in docVersions[1:]:
        revision = {
            "version": f"{docVersion}",
            "dirPath": f"{componentName}-docs-{docVersion}",
            "url": f"/{componentName}-docs-{docVersion}"
        }
        revisions.append(revision)
    return revisions

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
    commitGeneratedWebsiteRepo()
    print("finished website build")
