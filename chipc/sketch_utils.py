import re
import subprocess
from pathlib import Path

SYN_TIME_MINS = 30
SLV_TIMEOUT_MINS = 0.1


def check_syntax(sketch_file_name):
    # Check syntax of given sketch file.
    (return_code, output) = subprocess.getstatusoutput(
        'sketch ' + sketch_file_name + ' --slv-timeout=0.001')
    if (return_code == 0):
        print(sketch_file_name + ' passed syntax check. ')
        assert(output.rfind('Program Parse Error:') == -1)
    else:
        if (output.rfind('Program Parse Error:') != -1):
            raise Exception(
                sketch_file_name + ' contains a syntax error.' +
                'Output pasted below:\n\n' + output)


def synthesize(sketch_file_name, bnd_inbits, slv_seed, slv_parallel=False):
    assert(slv_parallel in [True, False])
    check_syntax(sketch_file_name)
    par_string = ' --slv-parallel' if slv_parallel else ''
    # Consider switching to subprocess.run as subprocess.getstatusoutput is
    # considered legacy.
    # https://docs.python.org/3.5/library/subprocess.html#legacy-shell-invocation-functions
    (return_code, output) = subprocess.getstatusoutput('time sketch -V 12 ' +
                                                       '--slv-nativeints ' +
                                                       sketch_file_name +
                                                       ' --bnd-inbits=' +
                                                       str(bnd_inbits) +
                                                       ' --slv-seed=' +
                                                       str(slv_seed) +
                                                       par_string +
                                                       ' --slv-timeout=' +
                                                       str(SYN_TIME_MINS))
    assert(output.rfind('Program Parse Error:') == -1)
    return (return_code, output)


def generate_smt2_formula(sketch_file_name, smt_file_name, bit_range):
    check_syntax(sketch_file_name)
    (return_code, output) = subprocess.getstatusoutput('sketch ' +
                                                       sketch_file_name +
                                                       ' --bnd-inbits=' +
                                                       str(bit_range) +
                                                       ' --slv-timeout=' +
                                                       str(SLV_TIMEOUT_MINS) +
                                                       ' --beopt:writeSMT ' +
                                                       smt_file_name)


def generate_ir(sketch_file_name):
    """Given a sketch file, returns its IR (intermediate representation).

    This function calls sketch and generates a .dag file having IR for the
    sketch file. Then reads the .dag file and returns its content."""
    check_syntax(sketch_file_name)
    # Generate the dag filename by replacing sk extension with dag.
    dag_file_name = re.sub('sk$', 'dag', sketch_file_name)
    subprocess.run([
        'sketch',
        '-V', '3',
        sketch_file_name,
        '--debug-output-dag', dag_file_name,
        # We only want the dag and sketch output is irrelevant here. So quickly
        # return from it using --slv-timeout.
        '--slv-seed', '1',
        '--slv-timeout', str(SLV_TIMEOUT_MINS)
    ],
        # Pipe stdout and stderr to /dev/null as we don't need them.
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL)

    return Path(dag_file_name).read_text()
