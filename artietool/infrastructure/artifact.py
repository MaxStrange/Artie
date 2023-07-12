from .. import docker
from .. import common
import abc
import os

class Artifact(abc.ABC):
    """
    Base class for all types of things produced by Tasks.

    Comparing Artifact objects to one another returns True if they
    both have the same name and producing_task_name.

    Comparing Artifact objects to a non-Artifact object returns
    True if the Artifact's item evaluates to the same as the other object.
    """
    def __init__(self, name: str, producing_task_name: str, item=None, built=False) -> None:
        """
        Args
        ----
        - name: The name of the Artifact, as referenced by dependent Tasks.
        - producing_task_name: The name of the Task that produces this Artifact.
        - item: If given, should be the Artifact value itself, the type of which depends on the subclass.
        - built: If True, this Artifact has already been built, and the `item` should not be None.
        """
        self.name = name
        self.producing_task_name = producing_task_name
        self.item = item
        self.built = built

    def __eq__(self, other: object) -> bool:
        if hasattr(other, 'name') and hasattr(other, 'producing_task_name'):
            return self.name == other.name and self.producing_task_name == other.producing_task_name
        else:
            return self.item == other

    def __hash__(self) -> int:
        return hash(f"{self.producing_task_name}:{self.name}:{self.item}")

    def __repr__(self) -> str:
        return str(self)

    def __str__(self) -> str:
        s = ""
        s += f"{str(type(self))}:"
        s += os.linesep + f"    name: {self.name}"
        s += os.linesep + f"    producing-task: {self.producing_task_name}"
        s += os.linesep + f"    item: {self.item}"
        s += os.linesep + f"    built: {self.built}"
        return s

    @abc.abstractmethod
    def fill_item(self, args, producing_job):
        """
        Fill in the value of `self.item` (but keep `self.built` untouched).
        """
        pass

    @abc.abstractmethod
    def mark_if_cached(self, args):
        """
        Mark `self.built = True` if we are already built (i.e., we can locate ourselves on disk).
        """
        pass

class YoctoImageArtifact(Artifact):
    """
    A Yocto Image binary file.
    """

    def fill_item(self, args, producing_job):
        if not hasattr(producing_job, 'binary_fname'):
            raise ValueError(f"YoctoImageArtifact is trying to configure itself, but its producing job does not have a 'binary_fname' attribute, so we don't know where to find the resulting Yocto image binary. Artifact: {self}; Producing Job: {producing_job}")

        self.item = os.path.join(args.artifact_folder, producing_job.binary_fname)

    def mark_if_cached(self, args):
        self.built = self.item is not None and os.path.isfile(self.item)

class DockerImageArtifact(Artifact):
    """
    A Docker image name.
    """

    def fill_item(self, args, producing_job):
        if not hasattr(producing_job, 'img_base_name'):
            raise ValueError(f"DockerImageArtifact is trying to configure itself, but its producing job does not have a 'img_base_name' attribute, so we don't know what the Docker image's name is. Artifact: {self}; Producing Job: {producing_job}")

        self._docker_image = docker.construct_docker_image_name(args, producing_job.img_base_name)
        self.item = str(self._docker_image)

    def mark_if_cached(self, args):
        self.built = self.item is not None and docker.check_if_docker_image_exists(args, self._docker_image)

class FilesArtifact(Artifact):
    """
    A collection of one or more files.

    self.item evaluates to a list of fw file paths found in the build directory.
    """

    def fill_item(self, args, producing_job):
        if not hasattr(producing_job, 'fw_fpaths_in_container'):
            raise ValueError(f"FilesArtifact is trying to configure itself, but its producing job does not have a 'fw_fpath_in_container' attribute, so we don't know where to get the files. Artifact: {self}; Producing Job: {producing_job}")

        self.item = []
        for fwfpath in producing_job.fw_fpaths_in_container:
            fwfname_no_ext, suf = os.path.splitext(os.path.basename(fwfpath))
            target = os.path.join(args.artifact_folder, fwfname_no_ext) + "-" + common.git_tag() + suf
            self.item.append(target)

    def mark_if_cached(self, args):
        if self.item is None:
            self.built = False
        else:
            self.built = all([os.path.isfile(fpath) for fpath in self.item])

def add_artifact(args, artifact: Artifact):
    """
    Adds the given `artifact` to the `args` for other tasks to retrieve it.
    If the artifact is already found in args, we replace it with this new one.

    NOTE: Make sure that `initialize(args)` has been called first.
    """
    if artifact.producing_task_name not in args._artifacts:
        args._artifacts[artifact.producing_task_name] = []

    # Replace an artifact if it already exists
    for art in args._artifacts[artifact.producing_task_name]:
        if art.name == artifact.name:
            art = artifact
            return

    # If we couldn't find it, just add it to the end of the list
    args._artifacts[artifact.producing_task_name].append(artifact)

def add_artifacts_from_result(args, result):
    """
    Adds the given `result`'s artifacts to `args` for other tasks to retrieve.

    NOTE: Make sure that `initialize(args)` has been called first.
    """
    for art in result.get_artifacts():
        add_artifact(args, art)

def initialize(args):
    """
    Initialize the `args` so that artifacts can be stored in it
    and retrieved from it.
    """
    # Internally, _artifacts is just a dict of the form {producing_task_name: [list of artifact objects]}
    setattr(args, "_artifacts", {})

def is_built(args, task_name: str, artifact_name: str) -> bool:
    """
    Returns `True` if the given artifact is built. `False` otherwise.

    NOTE: Make sure that `initialize(args)` has been called first.
    """
    if task_name not in args._artifacts:
        return False

    for a in args._artifacts[task_name]:
        if a.name == artifact_name and a.built:
            return True
        elif a.name == artifact_name and not a.built:
            return False
    return False

def retrieve_artifact(args, producing_task_name, artifact_name):
    """
    Attempts to get the specified artifact from the specified producing task.
    Errors out with useful error messaging.

    NOTE: Make sure that `initialize(args)` has been called first.
    """
    if producing_task_name not in args._artifacts:
        raise KeyError(f"Cannot find {producing_task_name} in _artifacts. The task either did not run, or it did not produce any artifacts.")

    for art in args._artifacts[producing_task_name]:
        if art.name == artifact_name:
            return art

    raise ValueError(f"Cannot find {artifact_name} in artifacts produced by {producing_task_name}. Artifacts produced: {args._artifacts[producing_task_name]}")
