# Chipmunk

[![Build status](https://ci.appveyor.com/api/projects/status/060fwhaq3vfvt22n/branch/master?svg=true)](https://ci.appveyor.com/project/anirudhSK/chipmunk-hhg5f/branch/master)

## Installation
- Install [antlr](https://www.antlr.org/)
- Install [sketch](https://people.csail.mit.edu/asolar/sketch-1.7.5.tar.gz)
- `pip3 install .`(from this directory)
(Add sudo if you want to install system wide.)

## How to

### Develop

If you have installed it as above, first re-install via following command.

```shell
pip3 install -e .
```

Note that there is `-e` in install command. It will install this package in
development mode, and simply link actual chipc directory to your Python's
site-packages directory.

1. Make changes to python code
2. Consider implementing tests and run tests `python3 -m unittest`
3. Run your desired binary like `python chipc/chipmunk.py ...`

This way you don't have to keep installing and uninstalling whenever you make a
change and test. However, still you have to run via `python3 chipc/chipmunk.py`
instead of using the installed binary.

Also consider using [venv](https://docs.python.org/3/library/venv.html),
[virtualenv](https://virtualenv.pypa.io/en/latest/) or
[pipenv](https://pipenv.readthedocs.io/en/latest/) to create an isolated Python
development environment.


### Codegen

```shell
direct_solver example_specs/simple.sk example_alus/raw.stateful_alu 2 2
```

or
```shell
direct_solver example_specs/simple.sk example_alus/raw.stateful_alu 2 2 --parallel-sketch
```

### Parallel codegen

```shell
direct_solver example_specs/simple.sk example_alus/raw.stateful_alu 2 2 --parallel --parallel-sketch
```

### Iterative solver
```shell
iterative_solver example_specs/simple.sk example_alus/raw.stateful_alu 2 2 --hole-elimination
```

```shell
iterative_solver example_specs/simple.sk example_alus/raw.stateful_alu 2 2 --parallel --parallel-sketch --hole-elimination
```


### Optimization Verification

```shell
optverify_stub_generator example_specs/simple.sk example_alus/raw.stateful_alu 1 1 sample1
optverify_stub_generator example_specs/simple.sk example_alus/raw.stateful_alu 1 1 sample2
optverify sample1 sample2 example_transforms/very_simple.transform
```

### Test

Run:

```shell
antlr4 chipc/stateful_alu.g4 -Dlanguage=Python3 -visitor -package chipc
python3 -m unittest
```

If you want to add a test, add a new file in [tests](tests/) directory or add
test cases in existing `test_*.py` file.
