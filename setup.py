# Copyright Hybrid Logic Ltd.  See LICENSE file for details.
#
# Generate a Flocker package that can be deployed onto cluster nodes.
#

if __name__ == '__main__':
    from setup import main
    raise SystemExit(main())

import os
from setuptools import setup, find_packages
from distutils.core import Command
import versioneer
versioneer.vcs = "git"
versioneer.versionfile_source = "flocker/_version.py"
versioneer.versionfile_build = "flocker/_version.py"
versioneer.tag_prefix = ""
versioneer.parentdir_prefix = "flocker-"


def rpm_version(flocker_version):
    """
    Parse the Flocker version generated by versioneer into an RPM compatible
    version and a release version.
    See: http://fedoraproject.org/wiki/Packaging:NamingGuidelines#Pre-Release_packages
    """
    # E.g. 0.1.2-69-gd2ff20c-dirty
    # tag+distance+shortid+dirty
    parts = flocker_version.split('-')
    tag, remainder = parts[0], parts[1:]
    for suffix in ('pre', 'dev'):
        parts = tag.rsplit(suffix, 1)
        if len(parts) == 2:
            # A pre or dev suffix was present. ``version`` is the part before
            # the pre and ``suffix_number`` is the part after the pre, but
            # before the first dash.
            version = parts.pop(0)
            suffix_number = parts[0]
            if suffix_number.isdigit():
                # Given pre or dev number X create a 0 prefixed, `.` separated
                # string of version labels. E.g.
                # 0.1.2pre2  becomes
                # 0.1.2-0.2.pre
                release = ['0', suffix_number, suffix]
                if remainder:
                    # The version may also contain a distance, shortid which
                    # means that there have been changes since the last
                    # tag. Additionally there may be a ``dirty`` suffix which
                    # indicates that there are uncommitted changes in the
                    # working directory.  We probably don't want to release
                    # untagged RPM versions, and this branch should probably
                    # trigger and error or a warning. But for now we'll add
                    # that extra information to the end of release number.
                    release.extend(remainder)
            else:
                # Non-integer pre or dev number found.
                raise Exception(
                    'Non-integer value "{}" for "{}". '
                    'Supplied version {}'.format(
                        release, suffix, flocker_version))
            break
    else:
        # Neither of the expected suffixes was found, the tag can be used as
        # the RPM version
        version = tag
        release = '1'

    return version, release


class cmd_generate_spec(Command):
    description = "Generate python-flocker.spec with current version."
    user_options = []
    boolean_options = []
    def initialize_options(self):
        pass
    def finalize_options(self):
        pass
    def run(self):
        with open('python-flocker.spec.in', 'r') as source:
            spec = source.read()

        flocker_version = versioneer.get_version()
        version, release = rpm_version(flocker_version)
        with open('python-flocker.spec', 'w') as destination:
            destination.write(
                "%%global flocker_version %s\n" % (flocker_version,))
            destination.write(
                "%%global version %s\n" % (version,))
            destination.write(
                "%%global release %s\n" % (release,))
            destination.write(spec)


def main():
    cmdclass = {'generate_spec': cmd_generate_spec}
    # Let versioneer hook into the various distutils commands so it can rewrite
    # certain data at appropriate times.
    cmdclass.update(versioneer.get_cmdclass())

    # Hard linking doesn't work inside VirtualBox shared folders. This means that
    # you can't use tox in a directory that is being shared with Vagrant,
    # since tox relies on `python setup.py sdist` which uses hard links. As a
    # workaround, disable hard-linking if setup.py is a descendant of /vagrant.
    # See
    # https://stackoverflow.com/questions/7719380/python-setup-py-sdist-error-operation-not-permitted
    # for more details.
    if os.path.abspath(__file__).split(os.path.sep)[1] == 'vagrant':
        del os.link

    with open("README.rst") as readme:
        description = readme.read()

    setup(
        # This is the human-targetted name of the software being packaged.
        name="Flocker",
        # This is a string giving the version of the software being packaged.  For
        # simplicity it should be something boring like X.Y.Z.
        version=versioneer.get_version(),
        # This identifies the creators of this software.  This is left symbolic for
        # ease of maintenance.
        author="ClusterHQ Team",
        # This is contact information for the authors.
        author_email="support@clusterhq.com",
        # Here is a website where more information about the software is available.
        url="https://clusterhq.com/",

        # A short identifier for the license under which the project is released.
        license="Apache License, Version 2.0",

        # Some details about what Flocker is.  Synchronized with the README.rst to
        # keep it up to date more easily.
        long_description=description,

        # This setuptools helper will find everything that looks like a *Python*
        # package (in other words, things that can be imported) which are part of
        # the Flocker package.
        packages=find_packages(),

        package_data={
            'flocker.node.functional': ['sendbytes-docker/*', 'env-docker/*'],
        },

        entry_points = {
            # Command-line programs we want setuptools to install:
            'console_scripts': [
                'flocker-volume = flocker.volume.script:flocker_volume_main',
                'flocker-deploy = flocker.cli.script:flocker_deploy_main',
                'flocker-changestate = flocker.node.script:flocker_changestate_main',
                'flocker-reportstate = flocker.node.script:flocker_reportstate_main',
            ],
        },

        install_requires=[
            "eliot == 0.4.0",
            "zope.interface == 4.0.5",
            "pytz",
            "characteristic == 0.1.0",
            "Twisted == 14.0.0",

            "PyYAML == 3.10",

            "treq == 0.2.1",

            "netifaces >= 0.8",
            "ipaddr == 2.1.10",
            ],

        extras_require={
            # This extra allows you to build and check the documentation for
            # Flocker.
            "doc": [
                "Sphinx==1.2.2",
                "sphinx-rtd-theme==0.1.6",
                "pyenchant==1.6.6",
                "sphinxcontrib-spelling==2.1.1",
                ],
            # This extra is for developers who need to work on Flocker itself.
            "dev": [
                # flake8 is pretty critical to have around to help point out
                # obvious mistakes. It depends on PEP8, pyflakes and mccabe.
                "pyflakes==0.8.1",
                "pep8==1.5.7",
                "mccabe==0.2.1",
                "flake8==2.2.0",

                # Run the test suite:
                "tox==1.7.1",

                # versioneer is necessary in order to update (but *not* merely to
                # use) the automatic versioning tools.
                "versioneer==0.10",

                # Some of the tests use Conch:
                "PyCrypto==2.6.1",
                "pyasn1==0.1.7",

                # The test suite uses network namespaces
                "nomenclature >= 0.1.0",
                ],

            # This extra is for Flocker release engineers to set up their release
            # environment.
            "release": [
                "gsutil",
                "wheel",
                ],
            },

        cmdclass=cmdclass,

        # Some "trove classifiers" which are relevant.
        classifiers=[
            "License :: OSI Approved :: Apache Software License",
            ],
        )
