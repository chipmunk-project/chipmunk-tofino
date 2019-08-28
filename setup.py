import glob
import os
import subprocess
from distutils import log
from pathlib import Path

from setuptools import find_packages
from setuptools import setup
from setuptools.command.build_py import build_py
from setuptools.command.develop import develop

_PACKAGE_NAME = 'chipc'


def _generate_parser():
    """Generates chipmunk grammar parser using chipmunk/stateful_alu.g4
    file. Assumes the user has java binary."""

    grammar_name = 'alu'
    antlr_ext = '.g4'

    alu_filepath = _PACKAGE_NAME + '/' + grammar_name + antlr_ext
    assert os.access(alu_filepath,
                     os.R_OK), "Can't find grammar file: %s" % alu_filepath

    antlr_jar = Path(_PACKAGE_NAME, 'lib', 'antlr-4.7.2-complete.jar')
    run_args = [
        'java', '-jar',
        str(antlr_jar), alu_filepath, '-Dlanguage=Python3', '-visitor',
        '-package', _PACKAGE_NAME
    ]

    subprocess.run(run_args, check=True)
    generated_files = glob.glob(_PACKAGE_NAME + '/' + grammar_name + '*.py')
    # Check whether Antlr actually generated any file.
    assert generated_files, 'Antlr4 failed to generate Parser/Lexer.'
    log.info('Antlr generated Python files: %s' % ', '.join(
        [str(f) for f in generated_files]))


class DevelopWrapper(develop):
    def run(self):
        _generate_parser()
        develop.run(self)


class BuildPyWrapper(build_py):
    def run(self):
        _generate_parser()
        build_py.run(self)


setup(
    name=_PACKAGE_NAME,
    version='0.1',
    description='A switch code generator based on end-to-end program ' +
    'synthesis.',
    url='https://github.com/anirudhSK/chipmunk',
    author='Chipmunk Contributors',
    packages=find_packages(exclude=['tests*', '*.interp', '*.tokens']),
    # This will let setuptools to copy ver what"s listed in MANIFEST.in
    include_package_data=True,
    install_requires=[
        'antlr4-python3-runtime>=4.7.2', 'Jinja2>=2.10', 'ordered_set>=3.1.1',
        'overrides>=1.9', 'psutil>=5.6.1', 'z3-solver>=4.8.0.0'
    ],
    cmdclass={
        'build_py': BuildPyWrapper,
        'develop': DevelopWrapper
    },
    entry_points={
        'console_scripts': [
            'iterative_solver=' + _PACKAGE_NAME + '.iterative_solver:run_main'
        ]
    })
