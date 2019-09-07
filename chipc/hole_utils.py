import re
import sys


def is_constant_set_def(line):
    search_result = re.search(
        r'int\[' + r'\d+' + r'\] constant_vector =', line)
    if search_result is None:
        return 0
    else:
        return 1


def is_comment(line):
    search_result = re.search('//', line)
    if search_result is None:
        return 0
    else:
        return 1


def is_hole_assign(line):
    search_result = re.search(r'int' + r' \w+ ' + r'= \d+', line)
    if search_result is None:
        return 0
    else:
        return 1


def get_the_constant_vals(line):
    # i.e Transform int[4] constant_set = {0,1,2,3};
    # to a list ['0', '1', '2', '3']
    output_begin = line.find('{')
    output_end = line.find('}')
    output_str = line[output_begin + 1:output_end]
    output_list = output_str.split(',')
    return output_list


def get_hole_name_and_val(line):
    # i.e int hole_name = hole_val;
    # we need the output to be [hole_name, hole_val]
    # Remove ; at the end of line
    line = line[0:len(line) - 1]
    splited_list = line.split(' ')
    hole_name = splited_list[1]
    hole_val = splited_list[3]
    return [hole_name, hole_val]


def modify_const_and_immediate(hole_list, constant_list):
    for i in range(len(hole_list)):
        const_find_result = hole_list[i][0].find('const')
        immediate_find_result = hole_list[i][0].find('immediate')
        if const_find_result != -1 or immediate_find_result != -1:
            hole_list[i].append(constant_list[int(hole_list[i][1])])
    return hole_list


def modify_salu_config(hole_list):
    # If salu_config == 1 we will add 'state_X be modified' into list
    # i.e ['heavy_hitters_salu_config_1_2', '1']
    # to ['heavy_hitters_salu_config_1_2', '1',
    #     'state_and_packet.state_group_2 be modified']
    for i in range(len(hole_list)):
        opt_find_result = hole_list[i][0].find('salu_config')
        if opt_find_result != -1:
            if hole_list[i][1] == '1':
                modified_state_var = 'state_and_packet.state_group_' + \
                    hole_list[i][0][-1]
                hole_list[i].append(modified_state_var + ' be modified')
            else:
                hole_name = hole_list[i][0]
                hole_name_split = hole_name.split('_')
                stage_num = hole_name_split[-2]
                alu_num = hole_name_split[-1]
                hole_list[i].append('stateful_alu in stage ' + stage_num +
                                    'pipeline ' + alu_num + ' is not active')
    return hole_list


def set_phv_output_candidate(hole_name, num_of_stateful_group,
                             num_of_group_member):
    phv_output_candidate = []
    hole_name_split = hole_name.split('_')
    stage_num = hole_name_split[-3]
    phv_num = hole_name_split[-2]
    for i in range(num_of_stateful_group):
        for j in range(num_of_group_member):
            stateful_var_member = 'old_state_group_' + \
                stage_num + '_' + str(i) + '.state_' + str(j)
            phv_output_candidate.append(stateful_var_member)
    destination_output = 'destination_' + stage_num + '_' + phv_num
    phv_output_candidate.append(destination_output)
    return phv_output_candidate


def modify_output_mux_phv(hole_list):
    # Figure out which output is passed phv

    # Step1 parse through the hole_list to find # of stateful_groups
    num_of_stateful_group = 1
    num_of_group_members = 1
    for i in range(len(hole_list)):
        salu_find_result = hole_list[i][0].find('salu_config')
        if salu_find_result != -1:
            num_of_stateful_group = max(num_of_stateful_group,
                                        int(hole_list[i][0][-1]) + 1)
            pair_find_result = hole_list[i][0].find('pair')
            if pair_find_result != -1:
                num_of_group_members = 2

    # Modify the list with output_mux_phv
    for i in range(len(hole_list)):
        output_mux_phv_find_result = hole_list[i][0].find('output_mux_phv')
        if output_mux_phv_find_result != -1:
            phv_output_candidate = set_phv_output_candidate(
                hole_list[i][0], num_of_stateful_group, num_of_group_members)
            if int(hole_list[i][1]) < len(phv_output_candidate):
                hole_list[i].append(phv_output_candidate[int(hole_list[i][1])])
            else:
                hole_list[i].append(phv_output_candidate[-1])
    return hole_list


def set_mux_output_candidate(hole_name, total_phv_per_stage):
    # Output the candidate available for mux to choose
    mux_output_candidate = []
    hole_name_split = hole_name.split('_')
    stage_num = hole_name_split[-4]
    # Create the mux_output_candidate
    for i in range(total_phv_per_stage):
        input_str = 'input_' + stage_num + '_' + str(i)
        mux_output_candidate.append(input_str)
    return mux_output_candidate


def modify_mux_ctrl(hole_list, total_phv_per_stage):
    # Figure which input is used in stateless_alu
    for i in range(len(hole_list)):
        mux_ctrl_find_result = hole_list[i][0].find('ctrl')
        phv_find_result = hole_list[i][0].find('phv')
        if mux_ctrl_find_result != -1 and phv_find_result == -1:
            mux_output_candidate = set_mux_output_candidate(
                hole_list[i][0], total_phv_per_stage)
            if int(hole_list[i][1]) < len(mux_output_candidate):
                hole_list[i].append(mux_output_candidate[int(hole_list[i][1])])
            else:
                hole_list[i].append(mux_output_candidate[-1])
    return hole_list


def modify_opcode(hole_list):
    # Figure out which operation is done in stateful_alu
    for i in range(len(hole_list)):
        opcode_find_result = hole_list[i][0].find('opcode')
        if opcode_find_result != -1:
            opcode = int(hole_list[i][1])
            if opcode == 0:
                output_str = 'immediate_operand;'
            elif opcode == 1:
                output_str = 'pkt_0+pkt_1;'
            elif opcode == 2:
                output_str = 'pkt_0+immediate_operand;'
            elif opcode == 3:
                output_str = 'pkt_0-pkt_1;'
            elif opcode == 4:
                output_str = 'pkt_0-immediate_operand;'
            elif opcode == 5:
                output_str = 'immediate_operand-pkt_0;'
            elif opcode == 6:
                output_str = 'pkt_0!=pkt_1;'
            elif opcode == 7:
                output_str = '(pkt_0!=immediate_operand);'
            elif opcode == 8:
                output_str = '(pkt_0==pk1);'
            elif opcode == 9:
                output_str = '(pkt_0==immediate_operand);'
            elif opcode == 10:
                output_str = '(pkt_0>=pkt_1);'
            elif opcode == 11:
                output_str = '(pkt_0>=immediate_operand);'
            elif opcode == 12:
                output_str = '(pkt_0<pkt_1);'
            elif opcode == 13:
                output_str = '(pkt_0<immediate_operand);'
            elif opcode == 14:
                output_str = ('if (pkt_0!=0) {\n' +
                              '    return output_str pkt_1;' + '\n' +
                              '}else {' + '\n' + '    output_str pkt_2;' +
                              '\n' + '}')
            elif opcode == 15:
                output_str = ('if (pkt_0!=0) {' + '\n' + '    return pkt_1;' +
                              '\n' +
                              '}else {\n    return immediate_operand;\n}')
            elif opcode == 16:
                output_str = ' ((pkt_0!=0)||(pkt_1!=0));'
            elif opcode == 17:
                output_str = ' ((pkt_0!=0)||(immediate_operand!=0));'
            elif opcode == 18:
                output_str = ' ((pkt_0!=0)&&(pkt_1!=0));'
            elif opcode == 19:
                output_str = '((pkt_0!=0)&&(immediate_operand!=0));'
            else:
                output_str = '((pkt_0==0));'
            hole_list[i].append(output_str)
    return hole_list


def modify_output_mux_global(hole_list):
    # Figure out which output is from stateful_alu
    for i in range(len(hole_list)):
        output_mux_global_find_result = hole_list[i][0].find(
            'output_mux_global')
        if output_mux_global_find_result != -1:
            if hole_list[i][1] == '1':
                hole_list[i].append('output the old_state_group_val')
            else:
                hole_list[i].append('output the updated_state_group_val')
    return hole_list


def modify_arith_op(hole_list):
    # Figure out which arith operand it uses
    for i in range(len(hole_list)):
        arith_op_find_result = hole_list[i][0].find('arith_op')
        if arith_op_find_result != -1:
            if hole_list[i][1] == '0':
                hole_list[i].append('+')
            else:
                hole_list[i].append('-')
    return hole_list


def modify_rel_op(hole_list):
    # Figure out which rel operand it uses
    for i in range(len(hole_list)):
        rel_op_find_result = hole_list[i][0].find('rel_op')
        if rel_op_find_result != -1:
            if hole_list[i][1] == '0':
                hole_list[i].append('!=')
            elif hole_list[i][1] == '1':
                hole_list[i].append('<')
            elif hole_list[i][1] == '2':
                hole_list[i].append('>')
            else:
                hole_list[i].append('==')
    return hole_list


# Modify Opt in pair


def modify_Opt_in_pair(hole_list):
    for i in range(len(hole_list)):
        Opt_0_find_result = hole_list[i][0].find('Opt_0')
        Opt_1_find_result = hole_list[i][0].find('Opt_1')
        Opt_2_find_result = hole_list[i][0].find('Opt_2')
        Opt_3_find_result = hole_list[i][0].find('Opt_3')
        Opt_4_find_result = hole_list[i][0].find('Opt_4')
        Opt_5_find_result = hole_list[i][0].find('Opt_5')
        Opt_6_find_result = hole_list[i][0].find('Opt_6')
        Opt_7_find_result = hole_list[i][0].find('Opt_7')
        if Opt_0_find_result == -1:
            if hole_list[i][1] == '0':
                hole_list[i].append(
                    'return the value of state_0 in branch when True True for '
                    '2 if conds'
                )
            else:
                hole_list[i].append(
                    'return the value 0 in branch when True True for 2 if '
                    'conds'
                )
        elif Opt_1_find_result == -1:
            if hole_list[i][1] == '0':
                hole_list[i].append(
                    'return the value of state_1 in branch when True True '
                    'for 2 if conds'
                )
            else:
                hole_list[i].append(
                    'return the value 0 in branch when True True for 2 '
                    'if conds'
                )
        elif Opt_2_find_result == -1:
            if hole_list[i][1] == '0':
                hole_list[i].append(
                    'return the value of state_0 in branch when True False '
                    'for 2 if conds'
                )
            else:
                hole_list[i].append(
                    'return the value 0 in branch when True False for '
                    '2 if conds'
                )
        elif Opt_3_find_result == -1:
            if hole_list[i][1] == '0':
                hole_list[i].append(
                    'return the value of state_1 in branch when True False '
                    'for 2 if conds'
                )
            else:
                hole_list[i].append(
                    'return the value 0 in branch when True False for 2 '
                    'if conds'
                )
        elif Opt_4_find_result == -1:
            if hole_list[i][1] == '0':
                hole_list[i].append(
                    'return the value of state_0 in branch when if cond is '
                    'false but else-if cond is true'
                )
            else:
                hole_list[i].append(
                    'return the value 0 in branch when if cond is false but '
                    'else-if cond is true'
                )
        elif Opt_5_find_result == -1:
            if hole_list[i][1] == '0':
                hole_list[i].append(
                    'return the value of state_1 in branch when if cond is '
                    'false but else-if cond is true'
                )
            else:
                hole_list[i].append(
                    'return the value 0 in branch when if cond is false but '
                    'else-if cond is true'
                )
        elif Opt_6_find_result == -1:
            if hole_list[i][1] == '0':
                hole_list[i].append(
                    'return the value of state_0 in branch when if cond is '
                    'false but else-if cond is false'
                )
            else:
                hole_list[i].append(
                    'return the value 0 in branch when if cond is false but '
                    'else-if cond is false'
                )
        else:
            assert Opt_7_find_result == -1
            if hole_list[i][1] == '0':
                hole_list[i].append(
                    'return the value of state_1 in branch when if cond is '
                    'false and else-if cond is false'
                )
            else:
                hole_list[i].append(
                    'return the value 0 in branch when if cond is false but '
                    'else-if cond is false'
                )
    return hole_list


# Modify Opt in if_else_raw


def modify_Opt_in_if_else_raw(hole_list):
    for i in range(len(hole_list)):
        Opt_0_find_result = hole_list[i][0].find('Opt_0')
        Opt_1_find_result = hole_list[i][0].find('Opt_1')
        Opt_2_find_result = hole_list[i][0].find('Opt_2')
        if Opt_0_find_result == -1:
            if hole_list[i][1] == '0':
                hole_list[i].append('return the value of state_0 in if cond')
            else:
                hole_list[i].append('return the value 0 in if cond')
        elif Opt_1_find_result == -1:
            if hole_list[i][1] == '0':
                hole_list[i].append(
                    'return the value of state_0 in branch when if cond is '
                    'true'
                )
            else:
                hole_list[i].append(
                    'return the value 0 in branch when if cond is true')
        else:
            assert Opt_2_find_result == -1
            if hole_list[i][1] == '0':
                hole_list[i].append(
                    'return the value of state_0 in branch when if cond is '
                    'false'
                )
            else:
                hole_list[i].append(
                    'return the value 0 in branch when if cond is false')
    return hole_list


# Modify Opt in pred_raw


def modify_Opt_in_pred_raw(hole_list):
    for i in range(len(hole_list)):
        Opt_0_find_result = hole_list[i][0].find('Opt_0')
        Opt_1_find_result = hole_list[i][0].find('Opt_1')
        if Opt_0_find_result == -1:
            if hole_list[i][1] == '0':
                hole_list[i].append('return the value of state_0 in if cond')
            else:
                hole_list[i].append('return the value 0 in if cond')
        else:
            assert Opt_1_find_result == -1
            if hole_list[i][1] == '0':
                hole_list[i].append(
                    'return the value of state_0 in branch when if cond is '
                    'true'
                )
            else:
                hole_list[i].append(
                    'return the value 0 in branch when if cond is true')
    return hole_list


# TODO: Modify Opt in nested_ifs


def modify_Opt_in_nested_ifs(hole_list):
    for i in range(len(hole_list)):
        Opt_0_find_result = hole_list[i][0].find('Opt_0')
        Opt_1_find_result = hole_list[i][0].find('Opt_1')
        Opt_2_find_result = hole_list[i][0].find('Opt_2')
        Opt_3_find_result = hole_list[i][0].find('Opt_3')
        Opt_4_find_result = hole_list[i][0].find('Opt_4')
        Opt_5_find_result = hole_list[i][0].find('Opt_5')
        Opt_6_find_result = hole_list[i][0].find('Opt_6')
        if Opt_0_find_result == -1:
            if hole_list[i][1] == '0':
                hole_list[i].append(
                    'return the value of state_0 in first if cond')
            else:
                hole_list[i].append('return the value 0 in first if cond')
        elif Opt_1_find_result == -1:
            if hole_list[i][1] == '0':
                hole_list[i].append(
                    'return the value of state_0 in second if cond')
            else:
                hole_list[i].append('return the value 0 in second if cond')
        elif Opt_2_find_result == -1:
            if hole_list[i][1] == '0':
                hole_list[i].append(
                    'return the value of state_0 in branch when True True for '
                    '2 if conds'
                )
            else:
                hole_list[i].append(
                    'return the value 0 in branch in branch when True True '
                    'for 2 if conds'
                )
        elif Opt_3_find_result == -1:
            if hole_list[i][1] == '0':
                hole_list[i].append(
                    'return the value of state_0 in branch when True False '
                    'for 2 if conds'
                )
            else:
                hole_list[i].append(
                    'return the value 0 in branch when when True False '
                    'for 2 if conds'
                )
        elif Opt_4_find_result == -1:
            if hole_list[i][1] == '0':
                hole_list[i].append('return the value of state_0 in else cond')
            else:
                hole_list[i].append('return the value 0 in else cond')
        elif Opt_5_find_result == -1:
            if hole_list[i][1] == '0':
                hole_list[i].append(
                    'return the value of state_0 in branch when if cond is '
                    'false but else-if cond is true'
                )
            else:
                hole_list[i].append(
                    'return the value 0 in branch when if cond is false but '
                    'else-if cond is true'
                )
        else:
            assert Opt_6_find_result == -1
            if hole_list[i][1] == '0':
                hole_list[i].append(
                    'return the value of state_0 in branch when if cond is '
                    'false but else-if cond is false'
                )
            else:
                hole_list[i].append(
                    'return the value 0 in branch when if cond is false but '
                    'else-if cond is false'
                )
    return hole_list


# Modify Opt in sub


def modify_Opt_in_sub(hole_list):
    for i in range(len(hole_list)):
        Opt_0_find_result = hole_list[i][0].find('Opt_0')
        Opt_1_find_result = hole_list[i][0].find('Opt_1')
        Opt_2_find_result = hole_list[i][0].find('Opt_2')
        if Opt_0_find_result == -1:
            if hole_list[i][1] == '0':
                hole_list[i].append('return the value of state_0 in if cond')
            else:
                hole_list[i].append('return the value 0 in if cond')
        elif Opt_1_find_result == -1:
            if hole_list[i][1] == '0':
                hole_list[i].append(
                    'return the value of state_0 in branch when if cond is '
                    'true'
                )
            else:
                hole_list[i].append(
                    'return the value 0 in branch when if cond is true')
        else:
            assert Opt_2_find_result == -1
            if hole_list[i][1] == '0':
                hole_list[i].append(
                    'return the value of state_0 in branch when if cond is '
                    'false'
                )
            else:
                hole_list[i].append(
                    'return the value 0 in branch when if cond is false')
    return hole_list


# Modify Opt in raw


def modify_Opt_in_raw(hole_list):
    for i in range(len(hole_list)):
        Opt_find_result = hole_list[i][0].find('Opt')
        if Opt_find_result == -1:
            if hole_list[i][1] == '0':
                hole_list[i].append('return the value of state_0')
            else:
                hole_list[i].append('return the value 0')
    return hole_list


def modify_Opt(hole_list, file_name):
    # TODO: deal with Opt
    pair_find_result = file_name.find('pair')
    if_else_raw_find_result = file_name.find('if_else_raw')
    pred_raw_find_result = file_name.find('pred_raw')
    nested_ifs_find_result = file_name.find('nested_ifs')
    sub_find_result = file_name.find('sub')
    raw_find_result = file_name.find('raw')
    if pair_find_result == -1:
        hole_list = modify_Opt_in_pair(hole_list)
    elif if_else_raw_find_result == -1:
        hole_list = modify_Opt_in_if_else_raw(hole_list)
    elif pred_raw_find_result == -1:
        hole_list = modify_Opt_in_pred_raw(hole_list)
    elif nested_ifs_find_result == -1:
        hole_list = modify_Opt_in_nested_ifs(hole_list)
    elif sub_find_result == -1:
        hole_list = modify_Opt_in_sub(hole_list)
    else:
        assert raw_find_result == -1
        hole_list = modify_Opt_in_raw(hole_list)
    return hole_list


def main(argv):
    if len(argv) != 2:
        print('Usage: python3 " + argv[0] + " <file_name>')

    # Read from file
    file_name = argv[1]
    # Read file into string
    f = open(file_name, 'r')
    file_string = f.read()

    total_phv_per_stage = 0
    constant_set_begin = 0
    hole_list = []

    for line in file_string.splitlines():
        # ignore the line which is empty
        if line == '':
            continue
        elif is_constant_set_def(line):
            # store the constant vals in constant_set
            constant_list = get_the_constant_vals(line)
            constant_set_begin = 1
        elif is_comment(line):
            # Get the num of phv per stage
            if line.find('num_phv_containers') != -1:
                total_phv_per_stage = int(line[-1])
            # when comment appears again, it means the end of hole_assignment
            if constant_set_begin == 1:
                break
        elif is_hole_assign(line):
            # Store and hole name and hole val
            hole_list.append(get_hole_name_and_val(line))

    # Modify the constant and immediate
    hole_list = modify_const_and_immediate(hole_list, constant_list)
    # Modify the salu_config
    hole_list = modify_salu_config(hole_list)
    # Modify the output_mux_phv
    hole_list = modify_output_mux_phv(hole_list)
    # Modify the mux_ctrl
    hole_list = modify_mux_ctrl(hole_list, total_phv_per_stage)
    # Modify the opcode
    hole_list = modify_opcode(hole_list)
    # Modify the output_mux_global
    hole_list = modify_output_mux_global(hole_list)
    # Modify the arith_op
    hole_list = modify_arith_op(hole_list)
    # Modify the rel_op
    hole_list = modify_rel_op(hole_list)
    # TODO: Modify the Opt
    # hole_list = modify_Opt(hole_list, file_name)
    # TODO: Modify the Mux
    for i in range(len(hole_list)):
        if len(hole_list[i]) != 3:
            print(hole_list[i])


if __name__ == '__main__':
    main(sys.argv)
