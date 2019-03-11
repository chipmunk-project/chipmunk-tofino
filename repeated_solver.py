"""Repeated Solver"""
from pathlib import Path
import re
import subprocess
import sys
import time

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from sketch_generator import SketchGenerator
from utils import get_num_pkt_fields_and_state_groups, get_hole_value_assignments
from sol_verify import sol_verify
from counter_example_generator import counter_example_generator
from compiler import Compiler

if (len(sys.argv) != 8):  # This part may need change with the chipmunk.py file
    print(
        "Usage: python3 " + sys.argv[0] +
        " <program file> <alu file> <number of pipeline stages> " + \
        "<number of stateless/stateful ALUs per stage> " + \
        "<sketch_name (w/o file extension)> <parallel/serial> " + \
        "<cex_mode/hole_elimination_mode>"
    )
    sys.exit(1)
else:
    start = time.time()
    program_file = str(sys.argv[1])
    (num_fields_in_prog,
     num_state_groups) = get_num_pkt_fields_and_state_groups(
         Path(program_file).read_text())
    alu_file = str(sys.argv[2])
    num_pipeline_stages = int(sys.argv[3])
    num_alus_per_stage = int(sys.argv[4])
    num_phv_containers = num_alus_per_stage
    sketch_name = str(sys.argv[5])
    parallel_or_serial = str(sys.argv[6])
    mode = str(sys.argv[7])
    assert (mode == "cex_mode") or (mode == "hole_elimination_mode")

compiler = Compiler(program_file, alu_file, num_pipeline_stages,
                    num_alus_per_stage, sketch_name, parallel_or_serial)
(ret_code, output, _) = compiler.codegen()

if (ret_code != 0):
    print("failed")
    end = time.time()
    print("total time in seconds: ", end - start)
    sys.exit(1)
else:
    # Generate the result file
    with open("/tmp/" + sketch_name + "_result.holes", "w") as result_file:
        result_file.write(output)
    # Step2: run sol_verify.py
    ret_code = sol_verify(sketch_name + "_codegen.sk",
                          "/tmp/" + sketch_name + "_result.holes")
    if (ret_code == 0):
        print("success")
        end = time.time()
        print("total time in seconds: ", end - start)
        sys.exit(0)
    else:
        print("failed for larger size and need repeated testing by sketch")
        # start to repeated run sketch until get the final result
        original_sketch_file_string = Path(sketch_name +
                                           "_codegen.sk").read_text()
        count = 0
        while (1):
            if (mode == "hole_elimination_mode"):
                hole_value_file_string = Path("/tmp/" + sketch_name +
                                              "_result.holes").read_text()
                begin_pos = hole_value_file_string.find('int')
                end_pos = hole_value_file_string.rfind(';')
                hole_value_file_string = hole_value_file_string[begin_pos:
                                                                end_pos + 1]
                #rearrange the format (int x=1; int y=2;) to (x==1 && y==2 && 1)
                hole_value_file_string = hole_value_file_string.replace(
                    "int", "")
                hole_value_file_string = hole_value_file_string.replace(
                    "=", "==")
                hole_value_file_string = hole_value_file_string.replace(
                    ";", "&&")
                hole_value_file_string = hole_value_file_string + "1"
                #find the position of harness
                begin_pos = original_sketch_file_string.find('harness')
                begin_pos = original_sketch_file_string.find(
                    'assert', begin_pos)
                original_sketch_file_string = original_sketch_file_string[
                    0:
                    begin_pos] + "assert(!(" + hole_value_file_string + "));\n" + original_sketch_file_string[
                        begin_pos:]
            else:
                # Find the position of harness
                begin_pos = original_sketch_file_string.find('harness')
                begin_pos = original_sketch_file_string.find(
                    'assert', begin_pos)

                # Add function assert here
                if (count == 0):
                    filename = sketch_name + "_codegen_with_hole_value.sk"
                else:
                    filename = "/tmp/" + sketch_name + "_new_sketch_with_hole_value.sk"
                counter_example_assert = ""
                counter_example_definition = ""
                #Add multiple counterexample range from 2 bits to 10 bits
                for bits in range(2, 10):
                    output_with_counter_example = counter_example_generator(
                        bits, filename, num_fields_in_prog, num_state_groups)
                    print("Bit: %d" % bits)
                    if (output_with_counter_example == ""):
                        continue
                    else:
                        #Grap the counterexample by using regular expression
                        pkt_group = re.findall(
                            "input (pkt_\d+)\w+ has value \d+= \((\d+)\)",
                            output_with_counter_example)
                        state_group = re.findall(
                            "input (state_group_\d+_state_\d+)\w+ has value \d+= \((\d+)\)",
                            output_with_counter_example)
                        print(pkt_group, "  ", bits)
                        print(state_group, " ", bits)
                        # print(pkt_group, "len= ", len(pkt_group), "actual value", str(int(pkt_group[0][1]) + 2**bits))
                        # print(state_group, "len= ", len(state_group), "actual value", int(state_group[0][1]) + 2**bits)
                        # Check if all packet fields are included in pkt_group as part of the counterexample.
                        # If not, set those packet fields to a default (0) since they don't matter for the counterexample.
                        for i in range(int(num_fields_in_prog)):
                            if ("pkt_" + str(i) in [
                                    regex_match[0] for regex_match in pkt_group
                            ]):
                                continue
                            else:
                                pkt_group.append(("pkt_" + str(i), str(0)))

                        # Check if all state vars are included in state_group as part of the counterexample.
                        # If not, set those state vars to a default (0) since they don't matter for the counterexample.
                        for i in range(int(num_state_groups)):
                            if ("state_group_0_state_" + str(i) in [
                                    regex_match[0]
                                    for regex_match in state_group
                            ]):
                                continue
                            else:
                                state_group.append(
                                    ("state_group_0_state_" + str(i), str(0)))
                        counter_example_definition += "|StateAndPacket| x_" + str(
                            count) + "_" + str(bits) + " = |StateAndPacket|(\n"
                        for i in range(len(pkt_group)):
                            counter_example_definition += pkt_group[i][
                                0] + " = " + str(
                                    int(pkt_group[i][1]) + 2**bits) + ',\n'
                        for i in range(len(state_group)):
                            if (i < len(state_group) - 1):
                                counter_example_definition += state_group[i][
                                    0] + " = " + str(
                                        int(state_group[i][1]) +
                                        2**bits) + ',\n'
                            else:
                                counter_example_definition += state_group[i][
                                    0] + " = " + str(
                                        int(state_group[i][1]) +
                                        2**bits) + ");\n"
                        counter_example_assert += "assert (pipeline(" + "x_" + str(
                            count) + "_" + str(
                                bits) + ")" + " == " + "program(" + "x_" + str(
                                    count) + "_" + str(bits) + "));\n"
                original_sketch_file_string = original_sketch_file_string[
                    0:
                    begin_pos] + counter_example_definition + counter_example_assert + original_sketch_file_string[
                        begin_pos:]

            new_sketch = open("/tmp/" + sketch_name + "_new_sketch.sk", "w")
            new_sketch.write(original_sketch_file_string)
            new_sketch.close()
            (ret_code1, output) = subprocess.getstatusoutput(
                "sketch -V 3 --bnd-inbits=2 " + new_sketch.name)
            print("Iteration #" + str(count))
            hole_value_string = ""
            #Failed      print("Hello1")
            print("ret_code1: ", ret_code1)
            if (ret_code1 == 0):
                hole_value_file = open("/tmp/" + sketch_name + "_result.holes",
                                       "w")
                holes_to_values = get_hole_value_assignments(
                    compiler.sketch_generator.hole_names_, output)
                for hole, value in holes_to_values.items():
                    hole_value_string += "int " + hole + " = " + value + ";"
                hole_value_file.write(hole_value_string)
                hole_value_file.close()
                ret_code = sol_verify("/tmp/" + sketch_name + "_new_sketch.sk",
                                      "/tmp/" + sketch_name + "_result.holes")
                if (ret_code == 0):
                    print("finally succeed")
                    end = time.time()
                    print("total time in seconds: ", end - start)
                    exit(0)
                else:
                    count = count + 1
                    continue
            else:
                print("finally failed")
                end = time.time()
                print("total time in seconds: ", end - start)
                print("total while loop: ", count)
                sys.exit(1)
