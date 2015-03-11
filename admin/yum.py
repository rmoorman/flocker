# Copyright Hybrid Logic Ltd.  See LICENSE file for details.

"""
Effectful interface to RPM tools.
"""

import os
from urlparse import urlparse

from twisted.python.filepath import FilePath
from characteristic import attributes
from effect import Effect, sync_performer, TypeDispatcher
from effect.do import do
from subprocess import check_call
from textwrap import dedent


@attributes([
    "source_repo",
    "target_path",
    "packages",
])
class DownloadPackagesFromRepository(object):
    """
    Download a given set of RPMs from a repository.

    :ivar bytes source_repo: Location of repoisitory.
    :ivar FilePath target_path: Directory to download packages to.
    :ivar list packages: List of bytes, package names to download.
    """


@sync_performer
def perform_download_packages_from_repository(dispatcher, intent):
    """
    See :class:`DownloadPackagesFromRepository`.
    """
    # TODO don't use yum tools. Just download files.
    # yum_repo_config = intent.target_path.child(b'build.repo')
    # yum_repo_config.setContent(dedent(b"""
    #      [flocker]
    #      name=flocker
    #      baseurl=%s
    #      """) % (intent.source_repo,))
    #
    # check_call([
    #     b'yum',
    #     b'--config', yum_repo_config.path,
    #     b'--disablerepo=*',
    #     b'--enablerepo=flocker',
    #     b'--quiet',
    #     b'clean',
    #     b'metadata'])
    #
    # check_call([
    #     b'yumdownloader',
    #     b'--config', yum_repo_config.path,
    #     b'--disablerepo=*',
    #     b'--enablerepo=flocker',
    #     b'--quiet',
    #     b'--destdir', intent.target_path.path] + intent.packages)
    #
    # yum_repo_config.remove()


@attributes([
    "repository_path",
])
class CreateRepo(object):
    """
    Create repository metadata.

    Note that this returns a list with the prefixes stripped.

    :ivar FilePath repository_path: Location of rpm files to create a
        repository from.
    """


@sync_performer
def perform_create_repository(dispatcher, intent):
    """
    See :class:`CreateRepo`.

    :return: List of new and modified rpm metadata filenames.
    """
    check_call([
        b'createrepo',
        b'--update',
        b'--quiet',
        intent.repository_path.path])


@attributes([
    "repository_path",
])
class ListPackages(object):
    """
    List the filenames of repository packages.

    Note that this returns a set with the prefixes stripped.

    :ivar FilePath repository_path: Location of repository to list repository
         packages from.
    """


@sync_performer
def perform_list_downloaded_packages(dispatcher, intent):
    """
    See class:`ListPackages`.
    """
    return set([os.path.basename(path.path) for path in
                intent.repository_path.walk() if path.isfile()])


@attributes([
    "repository_path",
])
class ListMetadata(object):
    """
    List the filenames of repository metadata.

    Note that this returns a set with the prefixes stripped.

    :ivar FilePath repository_path: Location of repository to list repository
         metadata from.
    """


@sync_performer
def perform_list_metadata(dispatcher, intent):
    """
    See class:`ListMetadata`.
    """
    return set([os.path.basename(path.path) for path in
                intent.repository_path.child('repodata').walk()])

yum_dispatcher = TypeDispatcher({
    DownloadPackagesFromRepository: perform_download_packages_from_repository,
    ListPackages: perform_list_downloaded_packages,
    ListMetadata: perform_list_metadata,
    CreateRepo: perform_create_repository,
})


class FakeYum(object):
    """
    Enough of a fake implementation of yum utilities to test
    :func:`admin.release.upload_rpms`.
    """
    @sync_performer
    def _perform_download_packages_from_repository(self, dispatcher, intent):
        """
        See :class:`DownloadPackagesFromRepository`.
        """
        # Source repository must be a URI for repodownloader so tests use
        # the file:// scheme.
        source_repo_directory = FilePath(urlparse(intent.source_repo).path)
        for path in source_repo_directory.walk():
            filename = os.path.basename(path.path)
            if path.isfile() and filename.startswith(tuple(intent.packages)):
                with path.open() as source_file:
                    intent.target_path.child(filename).setContent(
                        source_file.read())

    @sync_performer
    @do
    def _perform_create_repository(self, dispatcher, intent):
        """
        See :class:`CreateRepo`.
        """
        metadata_directory = intent.repository_path.child('repodata')
        metadata_directory.createDirectory()
        packages = yield Effect(ListPackages(
            repository_path=intent.repository_path))
        for filename in ['repomd.xml', 'filelists.xml.gz', 'other.xml.gz',
                         'primary.xml.gz']:
            metadata_directory.child(filename).setContent(
                'metadata content for: ' + ','.join(packages))

    def get_dispatcher(self):
        """
        Get an :module:`effect` dispatcher for interacting with this
        :class:`FakeYum`.
        """
        return TypeDispatcher({
            DownloadPackagesFromRepository:
                self._perform_download_packages_from_repository,
            ListPackages: perform_list_downloaded_packages,
            ListMetadata: perform_list_metadata,
            CreateRepo: self._perform_create_repository,
        })