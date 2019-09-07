/*
 * Chipmunk P4 Tofino Reference
 */
#include <tofino/intrinsic_metadata.p4>
#include <tofino/constants.p4>
#include "tofino/stateful_alu_blackbox.p4"
#include "tofino/lpf_blackbox.p4"


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
    fields {
        version : 4;
        ihl : 4;
        diffserv : 8;
        totalLen : 16;
        identification : 16;
        flags : 3;
        fragOffset : 13;
        ttl : 8;
        protocol : 8;
        hdrChecksum : 16;
        srcAddr : 32;
        dstAddr: 32;
    }
}

header ipv4_t ipv4;


field_list ipv4_field_list {
    ipv4.version;
    ipv4.ihl;
    ipv4.diffserv;
    ipv4.totalLen;
    ipv4.identification;
    ipv4.flags;
    ipv4.fragOffset;
    ipv4.ttl;
    ipv4.protocol;
    ipv4.srcAddr;
    ipv4.dstAddr;
}

field_list_calculation ipv4_chksum_calc {
    input {
        ipv4_field_list;
    }
    algorithm : csum16;
    output_width: 16;
}

calculated_field ipv4.hdrChecksum {
    update ipv4_chksum_calc;
}

header_type udp_t { // 8 bytes
    fields {
        srcPort : 16;
        dstPort : 16;
        hdr_length : 16;
        checksum : 16;
    }
}

header udp_t udp;


header_type metadata_t {
    fields {
        // Fill in Metadata with declarations
        condition : 32;
        value1 : 32;
        value2 : 32;
        value3 : 32;
        value4 : 32;
        result1 : 32;
        result2 : 32;
        result3 : 32;
        result4 : 32;
        index : 32;
        salu_flow : 8;
    }
}

metadata metadata_t mdata;

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
    set_metadata(mdata.condition, 1); // This is used for executing a control flow.
    set_metadata(mdata.index, 0);
    return ingress;
}

/** Registers ***/
#define MAX_SIZE 10
// Each register (Stateful ALU) can have many blackbox execution units.
// However, all blackbox units that operate on a SALU must be placed on the same stage.
// In most of my programs, I use two blackbox per SALU (one to update and other to read)
register salu1 {
    width : 32;
    instance_count : MAX_SIZE;
}

//  if (condition) {
//         salu1++;
//         result2 = 1;
//     } else {
//         salu = 0;
//         result2 = 0;
//     }
// }
blackbox stateful_alu salu1_exec1 {
    reg : salu1;
    condition_lo : mdata.condition == 1;
    condition_hi : mdata.condition == 1;
    update_lo_1_predicate : condition_lo;
    update_lo_1_value : register_lo + 1;
    update_lo_1_predicate : not condition_lo;
    update_lo_1_value : 0;
    update_hi_1_predicate : condition_hi;
    update_hi_1_value : 1;
    update_hi_1_predicate : not condition_hi;
    update_hi_2_value : 0;
    output_value : alu_hi;
    output_dst : mdata.result2;
}

// result2 = salu1
blackbox stateful_alu salu1_exec2 {
    reg : salu1;
    output_value : register_lo;
    output_dst : mdata.result2;
}

register salu2 {
    width : 32;
    instance_count : MAX_SIZE;
}

//  if (condition) {
//         salu1++;
//         result3 = 1;
//     } else {
//         salu = 0;
//         result3 = 0;
//     }
// }
blackbox stateful_alu salu2_exec1 {
    reg : salu2;
    condition_lo : mdata.condition == 1;
    condition_hi : mdata.condition == 1;
    update_lo_1_predicate : condition_lo;
    update_lo_1_value : register_lo + 1;
    update_lo_1_predicate : not condition_lo;
    update_lo_1_value : 0;
    update_hi_1_predicate : condition_hi;
    update_hi_1_value : 1;
    update_hi_1_predicate : not condition_hi;
    update_hi_2_value : 0;
    output_value : alu_hi;
    output_dst : mdata.result3;
}

// result2 = salu1
blackbox stateful_alu salu2_exec2 {
    reg : salu2;
    output_value : register_lo;
    output_dst : mdata.result3;
}
action action_0x0_1 () {
    modify_field(mdata.result1, mdata.value1);
}

action action_0x0_2 () {
    add(mdata.result1, mdata.value1, mdata.value2);
}

action action_0x0_3 () {
    subtract(mdata.result1, mdata.value1, mdata.value2);
}

action action_0x0_4 () {
    //result1 = value1 & value2
    bit_and(mdata.result1, mdata.value1, mdata.value2);
}

action action_0x0_5 () {
    //result1 = ~value1 & value2
    bit_andca(mdata.result1, mdata.value1, mdata.value2);
}

action action_0x0_6 () {
    //result1 = value1 & ~value2
    bit_andcb(mdata.result1, mdata.value1, mdata.value2);
}

action action_0x0_7 () {
    //result1 = ~(value1 & value2)
    bit_nand(mdata.result1, mdata.value1, mdata.value2);
}

action action_0x0_8 () {
    //result1 = ~(value1 | value2)
    bit_nor(mdata.result1, mdata.value1, mdata.value2);
}

action action_0x0_9 () {
    //result1 = ~value1
    bit_not(mdata.result1, mdata.value1);
}

action action_0x0_10 () {
    //result1 = value1 | value2
    bit_or(mdata.result1, mdata.value1, mdata.value2);
}

action action_0x0_11 () {
    //result1 = ~value1 | value2
    bit_orca(mdata.result1, mdata.value1, mdata.value2);
}

action action_0x0_12 () {
    //result1 = value1 | ~value2
    bit_orcb(mdata.result1, mdata.value1, mdata.value2);
}

action action_0x0_13 () {
    //result1 = ~(value1 ^ value2)
    bit_xnor(mdata.result1, mdata.value1, mdata.value2);
}

action action_0x0_14 () {
    //result1 = value1 ^ value2
    bit_xor(mdata.result1, mdata.value1, mdata.value2);
}

action action_0x0_15 () {
    //result1 = max(value1, value2)
    max(mdata.result1, mdata.value1, mdata.value2);
}

action action_0x0_16 () {
    //result1 = min(value1, value2)
    min(mdata.result1, mdata.value1, mdata.value2);
}

action action_0x0_17 () {
    //result1 = value1 - value2
    subtract(mdata.result1, mdata.value1, mdata.value2);
}

action action_0x0_18 () {
    //result1 -= value1
    subtract_from_field(mdata.result1, mdata.value1);
}

action action_0x0_19 () {
    //result1 = value1 << value2(immediate value)
    shift_left(mdata.result1, mdata.value1, 1);
}

action action_0x0_20 () {
    //result1 = value1 >> value2(immediate value)
    shift_right(mdata.result1, mdata.value1, 1);
}

action action_0x0_21 () {
    // value1,value2 = value2,value1
    swap(mdata.value1, mdata.value2);
}

// Action 0x3 for table 0x3
action action_0x3_1 () {
    //result4 =value1
    modify_field(mdata.result4, mdata.value3);
}

action action_0x3_2 () {
    //result4 = value1 + value2
    add(mdata.result4, mdata.value3, mdata.value4);
}

action action_0x3_3 () {
    //result4 +=value1
    add_to_field(mdata.result4, mdata.value3);
}

action action_0x3_4 () {
    //result4 = value1 & value2
    bit_and(mdata.result4, mdata.value3, mdata.value4);
}

action action_0x3_5 () {
    //result4 = ~value1 & value2
    bit_andca(mdata.result4, mdata.value3, mdata.value4);
}

action action_0x3_6 () {
    //result4 = value1 & ~value2
    bit_andcb(mdata.result4, mdata.value3, mdata.value4);
}

action action_0x3_7 () {
    //result4 = ~(value1 & value2)
    bit_nand(mdata.result4, mdata.value3, mdata.value4);
}

action action_0x3_8 () {
    //result4 = ~(value1 | value2)
    bit_nor(mdata.result4, mdata.value3, mdata.value4);
}

action action_0x3_9 () {
    //result4 = ~value1
    bit_not(mdata.result4, mdata.value3);
}

action action_0x3_10 () {
    //result4 = value1 | value2
    bit_or(mdata.result4, mdata.value3, mdata.value4);
}

action action_0x3_11 () {
    //result4 = ~value1 | value2
    bit_orca(mdata.result4, mdata.value3, mdata.value4);
}

action action_0x3_12 () {
    //result4 = value1 | ~value2
    bit_orcb(mdata.result4, mdata.value3, mdata.value4);
}

action action_0x3_13 () {
    //result4 = ~(value1 ^ value2)
    bit_xnor(mdata.result4, mdata.value3, mdata.value4);
}

action action_0x3_14 () {
    //result4 = value1 ^ value2
    bit_xor(mdata.result4, mdata.value3, mdata.value4);
}

action action_0x3_15 () {
    //result4 = max(value1, value2)
    max(mdata.result4, mdata.value3, mdata.value4);
}

action action_0x3_16 () {
    //result4 = min(value1, value2)
    min(mdata.result4, mdata.value3, mdata.value4);
}

action action_0x3_17 () {
    //result4 = value1 - value2
    subtract(mdata.result4, mdata.value3, mdata.value4);
}

action action_0x3_18 () {
    //result4 -= value1
    subtract_from_field(mdata.result4, mdata.value3);
}

action action_0x3_19 () {
    //result4 = value1 << value2(immediate value)
    shift_left(mdata.result4, mdata.value3, 1);
}

action action_0x3_20 () {
    //result4 = value1 >> value2(immediate value)
    shift_right(mdata.result4, mdata.value3, 1);
}

action action_0x3_21 () {
    // value1,value2 = value2,value1
    swap(mdata.value3, mdata.value4);
}

// Stateful ALU Action
action action_0x1_1 () {
    salu1_exec1.execute_stateful_alu(mdata.index);
}


action action_0x2_1 () {
    salu2_exec1.execute_stateful_alu(mdata.index);
}

action nop () {
    // Do nothing
}
// A table can optionally read some metadata, and execute an action of the listed ones.
// In case, there is no other conditions, mdata.condition should be set to 1
table table_0x0 {
    reads {
        mdata.condition : exact; // This is to be filled by the compiler.
        // Can be one or more of such PHV contents
    }
    actions {
        action_0x0_1; // action1 - assignment
        action_0x0_2; // action2 - add
        action_0x0_3; // action3 - subtract
        action_0x0_4;
        action_0x0_5;
        action_0x0_6;
        action_0x0_7;
        action_0x0_8;
        action_0x0_9;
        action_0x0_10;
        action_0x0_11;
        action_0x0_12;
        action_0x0_13;
        action_0x0_14;
        action_0x0_15;
        action_0x0_16;
        action_0x0_17;
        action_0x0_18;
        action_0x0_19;
        action_0x0_20;
        // action_0x0_21; // Swap has a problem now. TBFixed
        nop;
    }
    default_action: nop;
}

table table_0x1 {
    reads {
        mdata.condition : exact; // This is to be filled by the compiler.
        // Can be one or more of such PHV contents
    }
    actions {
        action_0x1_1; // action1 for SALU
        nop;
    }
    default_action: nop;
}

table table_0x2 {
    reads {
        mdata.condition : exact; // This is to be filled by the compiler.
        // Can be one or more of such PHV contents
    }
    actions {
        action_0x2_1; // action2 for SALU
        nop;
    }
    default_action: nop;
}

table table_0x3 {
    reads {
        mdata.condition : exact; // This is to be filled by the compiler.
        // Can be one or more of such PHV contents
    }
    actions {
        action_0x3_1; // action1 - assignment
        action_0x3_2; // action2 - add
        action_0x3_3; // action3 - subtract
        action_0x3_4;
        action_0x3_5;
        action_0x3_6;
        action_0x3_7;
        action_0x3_8;
        action_0x3_9;
        action_0x3_10;
        action_0x3_11;
        action_0x3_12;
        action_0x3_13;
        action_0x3_14;
        action_0x3_15;
        action_0x3_16;
        action_0x3_17;
        action_0x3_18;
        action_0x3_19;
        action_0x3_20;
        //action_0x3_21; // Swap has a problem now. TBFixed
        nop;
    }
    default_action: nop;
}

action set_egr(egress_spec) {
    modify_field(ig_intr_md_for_tm.ucast_egress_port, egress_spec);
}

table mac_forward {
    reads {
        ethernet.dstAddr : exact;
    }
    actions {
        set_egr;
        nop;
    }
    size:20;
}

control ingress {
    // Stage 0
    // 2 x 1 - 2 Stateless & 2 Stateful ALU, 1 Stage
    apply(table_0x0); // Stateless ALU
    apply(table_0x1); // Stateful  ALU
    apply(table_0x2); // Stateful  ALU
    apply(table_0x3); // Stateless ALU
    // Stage 1
    // To be similar to Stage 0
    // Mac Forwarding by default
    apply(mac_forward);
}

control egress {

}
