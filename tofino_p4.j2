#include <tofino/intrinsic_metadata.p4>
#include "tofino/stateful_alu_blackbox.p4"

/* Declare Header */
header_type ethernet_t {
    fields {
        dstAddr : 48;
        srcAddr : 48;
        etherType : 16;
    }
}

header ethernet_t ethernet;

header_type ipv4_t {
    fields { // Variable: can use these fields for output from packet processing program.
             // Note: this is just for ease of prototyping. In practice, we would use a separate header for this.
        field1 : 32;
        field2 : 32;
        field3 : 32; 
        field4 : 32;
        field5 : 32;
    }
}

header ipv4_t ipv4;

/* Declare Parser */
parser start {
	return select(current(96,16)){
		0x0800: parse_ethernet;
	}
}

parser parse_ethernet {
    extract(ethernet);
    return select(latest.etherType) {
        /** Fill Whatever ***/
        0x0800     : parse_ipv4;
        default: ingress;
    }
}
parser parse_ipv4 {
    extract(ipv4);
    return ingress;
}

/** Registers ***/
// A P4 register corresponds 1-to-1 with a Domino state variable.
// If the Domino state variable is a scalar, the instance_count of the register is 1.
// If the Domino state variable is an array, the instance_count of the register is the size of the array.

// Note on paired configurations:
// register_hi or register_lo can be 8, 16, or 32 bits wide each.  A register
// can either be single (uses only one of register_hi/register_lo) or paired
// (uses both).  The Tofino compiler decides whether register is single or
// paired based on whether both register_hi and register_lo are used in the P4
// code of blackbox stateful_alu, or whether only one of the two is used.
// Instead of relying on the compiler's detection algorithm, we can force a
// paired configuration by setting the register width to 64.
#define MAX_SIZE 10
register salu1 {
    width : 64;
    instance_count : MAX_SIZE;
}

blackbox stateful_alu salu1_exec1 {
    reg : salu1; // Variable, but can associate a stateful ALU blackbox with only one state variable (register)
    condition_lo : 1 == 1; // Variable, condition for triggerring ALU_LO1 (needs to be a predicate)
    condition_hi : 1 == 1; // Variable, predicate
    update_lo_1_predicate : condition_lo; // Variable, predicate TODO: figure out how this relates to conditon_lo 
    update_lo_1_value : register_lo + 7;  // Variable, arithmetic expression
    update_lo_2_predicate : not condition_lo; // Variable predicate
    update_lo_2_value : 0; // Variable arithmetic expression
    update_hi_1_predicate : condition_hi; // Variable predicate
    update_hi_1_value : register_hi + 7; // Variable arithmetic expression
    update_hi_2_predicate : not condition_hi; // Variable predicate
    update_hi_2_value : 0; // Variable arithmetic expression
    output_value : alu_lo; // Variable: either alu_lo or register_lo or alu_hi or register_hi
    output_dst : ipv4.field5; // Variable: any PHV container or packet field
    initial_register_lo_value : 0xFFFFFFF1; // Variable: any number
    initial_register_hi_value : 10; // Variable: any number
}

// Stateful ALU Action
action action_0x1_1 () {
    salu1_exec1.execute_stateful_alu(0);
    // Replace 0 with appropriate value for array-based registers.
}

// Stateful ALU table
// (use pragmas to enforce table placement in certain stages)
@pragma stage 0
table table_0x1 {
    actions {
        action_0x1_1; // action1 for SALU
    }
    default_action: action_0x1_1;
}

// Stateless ALU action
action action_0x0() {
    modify_field(ipv4.field1, 0xDEADFA11);
    modify_field(ipv4.field2, 0xFACEFEED); 
    modify_field(ipv4.field3, 0xDEADFEED);
    modify_field(ipv4.field4, 0xCAFED00D);
}

// Stateless ALU table
@pragma stage 0
table table_0x0 {
    actions {
        action_0x0;
    }
    default_action: action_0x0;
}

// Variable: Create as many stateful and stateless tables as required depending on the grid size.

// Required: mac_forward table for forwarding to switch CPU.
action set_egr(egress_spec) {
    modify_field(ig_intr_md_for_tm.ucast_egress_port, egress_spec);
}
table mac_forward {
    reads {
        ethernet.dstAddr : exact;
    }
    actions {
        set_egr;
    }
    size:1;
}

control ingress {
    // Stage 0
    // 1 Stateless & 1 Stateful ALU
    // Call as many tables as required depending on the grid size.
    apply(table_0x0); // Stateless ALU
    apply(table_0x1); // Stateful  ALU
    // MAC Forwarding by default
    apply(mac_forward);
}

control egress {

}
