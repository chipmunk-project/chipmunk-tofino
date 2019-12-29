# Debugging —target-tofino

## Compiling and loading the P4 program onto tofino

First compile the target benchmark with following flags
```shell
iterative_solver \
    example_specs/rcp.sk example_alus/stateful_alus/tofino.alu \
    example_alus/stateless_alus/stateless_alu_for_tofino.alu \
    1 3 '0,1,2,3' 10 --target-tofino
```

Then look for a .p4 file in the directory you ran above command, for example there will be a file named rcp_tofino_stateless_alu_for_tofino_1_3.p4.

Then transfer the p4 file to tofino using following command.
```shell
scp rcp_tofino_stateless_alu_for_tofino_1_3.p4 \
    root@tofino1.cs.nyu.edu:/tmp/autogen.p4
```

Make sure to verify that the file indeed is what you just transferred by opening it.

Now navigate to Barefoot SDE directory
```shell
cd ~/bf-sde-8.2.0
```

Set the environment variables
```shell
. ./set_sde.bash
```

Build the P4 program using following command
```shell
./p4_build.sh /tmp/autogen.p4
```

Load the control plane program
```shell
cd ~/tofino-boilerplate/CP
./run.sh
```

Then, after few debug messages, it will say "Finished sending 10 packets; press ctrl-c to see results." In another shell, load the environment variables, and run bfshell.

```shell
cd ~/bf-sde-8.2.0
. ./set_sde.bash
bfshell
```

Within the bfshell run following commands to read register 0 index 0

```shell
bfshell> pd-autogen
bfshell> pd register_read reg_0 index 0
```

If you press ctrl-c on the other screen where you ran the control plane program, you can also see the input packet and output packet values.

## Control Plane Program

In tofino-boilerplate we have very simple control plane program sending 10 packets. First few lines of the file defines the UDP packet that's being used, lines [52-61](https://github.com/chipmunk-project/tofino-boilerplate/blob/0c1428e9e28870158566803d1e9a9a1c7c003b08/CP/chip_cp.c#L52).

```C
// Declarations for UDP Packet
typedef struct __attribute__((__packed__)) udp_packet_t {
    uint8_t dstAddr[6];
    uint8_t srcAddr[6];
    uint16_t ethtype;
    uint32_t field0;
    uint32_t field1;
    uint32_t field2;
    uint32_t field3;
    uint32_t field4;
} udp_packet;
```

Currently, there isn't much meaning to each field of the struct.

Function [`udppkt_init()`](https://github.com/chipmunk-project/tofino-boilerplate/blob/0c1428e9e28870158566803d1e9a9a1c7c003b08/CP/chip_cp.c#L177) sets initial values of the packets. Feel free to change these values to trigger specific branches of the P4 program.

## Verifying P4 program == spec

1. Compile the spec and load it to Tofino
2. Run the control plane program
3. Load bfshell and check the register values, which are state variables in the original programs.
4. After checking the state variables look at the packet field variables are mutated as intended by pressing ctrl-c and showing them in the terminal where you loaded control plane program.

## Resources

bf-sde-8.2.0/pkgsrc/tofinobm/src/extern/stateful_alu.cpp

stateful_alu.cpp file in the Barefoot SDE directory has implementation of what's described in the page 13 of [stateful_alu.pdf](https://github.com/chipmunk-project/chipmunk-tofino/blob/master/salu_notes/stateful_alu.pdf). Make sure that our implementation of tofino code generator is in sync with the actual implementation in cpp file.

---
