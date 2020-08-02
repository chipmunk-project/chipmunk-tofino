# Repository

This folder contains the documentation for Chipmunk compiler.

# Compiler source code organization

```
chipmunk-tofino
├── chipc
│   ├── lib                   -- library files including antlr version 4.7.2
│   └── templates             -- collection of jinja2 template files corresponds to alu communication in section 5.1 of final SIGCOMM paper
├── docs                      -- documentation
├── final_paper               -- final SIGCOMM paper
├── example_alus
│   ├── stateful_alus         -- stateful ALU file corresponds to alu computation section 5.1 in final SIGCOMM paper
│   └── stateless_alus        -- stateless ALU file corresponds to alu computation section 5.1 in final SIGCOMM paper
├── example_spec              -- example .sk benchmarks used for testing
└── tests                     -- test code
    └── data                  -- generated .smt, .sk and .dag file used for testing
```

# How to get specification file from Domino program

* Understand Domino language from [here] (http://web.mit.edu/domino/)
* Transform Domino program to .sk file as specification by running the binary code domino_to_chipmunk by [instruction] (https://github.com/chipmunk-project/domino-compiler)


# How to contribute

* do write unit test code
* code has to be reviewed before it is merged
* make sure all tests pass when you send a pull request
* write documentation

## Git usage
* After committing changes, create a pull request and merge it before being reviewed by other users (using the github web UI)
