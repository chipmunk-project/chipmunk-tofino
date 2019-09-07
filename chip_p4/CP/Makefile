#
# PROGNAME : Things to be changed according to program.
# ARCH: vther it is tofinobm or tofino or bmv2.
#
PROGNAME := chip
ARCH := tofino
SOURCES := chip_cp.c
ifeq ($(ARCH), tofinobm)
	TOFINO_BUILD_DIR = /home/tofino/tofino-workbench/bf-sde-8.2.0/install
else
	TOFINO_BUILD_DIR = /root/bf-sde-8.2.0/install
endif
TOFINO_SDE_INCLUDE := -I$(TOFINO_BUILD_DIR)/include
TOFINO_LIBS := /usr/local/lib/libthrift-0.9.2.so \
/usr/lib/x86_64-linux-gnu/libpthread.so \
$(TOFINO_BUILD_DIR)/lib/libbf_switchd_lib.so \
$(TOFINO_BUILD_DIR)/lib/libbfutils.so \
$(TOFINO_BUILD_DIR)/lib/libtofinopdfixed_thrift.so \
$(TOFINO_BUILD_DIR)/lib/$(ARCH)pd/$(PROGNAME)/libpd.so \
$(TOFINO_BUILD_DIR)/lib/$(ARCH)pd/$(PROGNAME)/libpdthrift.so \
$(TOFINO_BUILD_DIR)/lib/libdriver.so \


all: $(PROGNAME)_cp

$(PROGNAME)_cp:
	@echo 'gcc $(TOFINO_SDE_INCLUDE) $(SOURCES) -o $(PROGNAME)_cp $(TOFINO_LIBS)'
	@gcc  $(TOFINO_SDE_INCLUDE) $(SOURCES) -o $(PROGNAME)_cp $(TOFINO_LIBS)

	@echo ' Finished successfully building.'

clean:
	@rm $(PROGNAME)_cp
