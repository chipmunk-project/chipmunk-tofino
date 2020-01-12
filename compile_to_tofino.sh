if [ $# -le 1 ]; then
  echo "Usage: $0 file_name depth width slice"
  exit 1
fi
set -e
set -x
set -v

file_name=$1
simpler_file_name=$(echo $file_name | sed "s/.*\///" | sed "s/\.sk//")
echo "simpler_file_name is $simpler_file_name"
depth=$2
width=$3
slice=$4

iterative_solver $file_name example_alus/stateful_alus/tofino.alu \
  example_alus/stateless_alus/stateless_alu_for_tofino.alu $depth $width \
  "0,1,2,3" 10 $slice --target-tofino
scp ${simpler_file_name}_tofino_stateless_alu_for_tofino_${depth}_${width}.p4 \
  root@tofino1.cs.nyu.edu:/tmp/autogen.p4
ssh root@tofino1.cs.nyu.edu "cd ~/bf-sde-8.2.0; ./p4_build.sh /tmp/autogen.p4;"
# echo "To test program, enter packet fields and state vars in the format field0 ... field4 [reg_0=x] [reg_1=y] ..."
# read test_input
# ssh root@tofino1.cs.nyu.edu "cd ~/tofino-boilerplate/CP; ./run.sh $test_input"
