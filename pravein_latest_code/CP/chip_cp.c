/*
 * Control Plane program for Tofino-based Chipmunk template program.
 * Compile using following command : make ARCH=Target[tofino|tofinobm]
 * To Execute, Run: ./run.sh
 *
 */

// Superset of all includes
#include <stdio.h>
#include <stdlib.h>
#include <stddef.h>
#include <stdint.h>
#include <sched.h>
#include <string.h>
#include <time.h>
#include <assert.h>
#include <unistd.h>
#include <pthread.h>
#include <unistd.h>
#include <bfsys/bf_sal/bf_sys_intf.h>
#include <dvm/bf_drv_intf.h>
#include <lld/lld_reg_if.h>
#include <lld/lld_err.h>
#include <lld/bf_ts_if.h>
#include <knet_mgr/bf_knet_if.h>
#include <knet_mgr/bf_knet_ioctl.h>
#include <bf_switchd/bf_switchd.h>
#include <pkt_mgr/pkt_mgr_intf.h>
#include <tofino/pdfixed/pd_common.h>
#include <tofino/pdfixed/pd_mirror.h>
#include <tofino/pdfixed/pd_conn_mgr.h>
#include <pcap.h>
#include <arpa/inet.h>

// #include <tofinopd/snaprr_topo/pd/pd.h>
#include <tofino/pdfixed/pd_common.h>
#include <tofino/pdfixed/pd_conn_mgr.h>

#define THRIFT_PORT_NUM 7777

// Session Handle, initialized by bf_switchd
p4_pd_sess_hdl_t sess_hdl;

// Declarations for UDP Packet
typedef struct __attribute__((__packed__)) udp_packet_t {
  uint8_t dstAddr[6];
  uint8_t srcAddr[6];
  uint16_t ethtype;
  uint8_t version_ihl;
  uint8_t diffserv;
  uint16_t totalLen;
  uint32_t identification;
  uint8_t ttl;
  uint8_t protocol;
  uint16_t ipchecksum;
  uint32_t ipsrcAddr;
  uint32_t ipdstAddr;
  uint16_t srcPort;
  uint16_t dstPort;
  uint16_t len;
  uint16_t udpchecksum;
  uint8_t payload[16];
} udp_packet;

// Packet definitions
udp_packet udp_pkt;
size_t udp_pkt_sz  = sizeof(udp_packet);
bf_pkt *upkt = NULL;
uint8_t *udp_pkt_8;

// bfswitchd initialization. Needed for all programs
void init_bf_switchd() {
  bf_switchd_context_t *switchd_main_ctx = NULL;
  char *install_dir;
  char target_conf_file[100];
  int ret;
	p4_pd_status_t status;
  install_dir = getenv("SDE_INSTALL");
  sprintf(target_conf_file, "%s/share/p4/targets/tofino/chip.conf", install_dir);

  /* Allocate memory to hold switchd configuration and state */
  if ((switchd_main_ctx = malloc(sizeof(bf_switchd_context_t))) == NULL) {
    printf("ERROR: Failed to allocate memory for switchd context\n");
    return;
  }

  memset(switchd_main_ctx, 0, sizeof(bf_switchd_context_t));
  switchd_main_ctx->install_dir = install_dir;
  switchd_main_ctx->conf_file = target_conf_file;
  switchd_main_ctx->skip_p4 = false;
  switchd_main_ctx->skip_port_add = false;
  switchd_main_ctx->running_in_background = true;
  switchd_main_ctx->dev_sts_port = THRIFT_PORT_NUM;
  switchd_main_ctx->dev_sts_thread = true;

  ret = bf_switchd_lib_init(switchd_main_ctx);
  printf("Initialized bf_switchd, ret = %d\n", ret);

	status = p4_pd_client_init(&sess_hdl);
	if (status == 0) {
		printf("Successfully performed client initialization.\n");
	} else {
		printf("Failed in Client init\n");
	}

}

void init_tables() {
    system("bfshell -f commands-newtopo-tofino1.txt");
}

// This callback function needed for sending a packet. Does nothing
static bf_status_t switch_pktdriver_tx_complete(bf_dev_id_t device,
                                                bf_pkt_tx_ring_t tx_ring,
                                                uint64_t tx_cookie,
                                                uint32_t status) {

  //bf_pkt *pkt = (bf_pkt *)(uintptr_t)tx_cookie;
  //bf_pkt_free(device, pkt);
  return 0;
}

// Packet is received from Port 192 (dataplane)
bf_status_t rx_packet_callback (bf_dev_id_t dev_id, bf_pkt *pkt, void *cookie, bf_pkt_rx_ring_t rx_ring) {
  int i;
  p4_pd_dev_target_t p4_dev_tgt = {0, (uint16_t)PD_DEV_PIPE_ALL};
  printf("Packet received:\n");
  for (i=0;i<pkt->pkt_size;i++) {
      printf("%X ", pkt->pkt_data[i]);
  }
  printf("\n\n\n\n");
  bf_pkt_free(dev_id, pkt);
  return BF_SUCCESS;
}

void switch_pktdriver_callback_register(bf_dev_id_t device) {

  bf_pkt_tx_ring_t tx_ring;
  bf_pkt_rx_ring_t rx_ring;

  /* register callback for TX complete */
  for (tx_ring = BF_PKT_TX_RING_0; tx_ring < BF_PKT_TX_RING_MAX; tx_ring++) {
    bf_pkt_tx_done_notif_register(
        device, switch_pktdriver_tx_complete, tx_ring);
  }
  /* register callback for RX */
  for (rx_ring = BF_PKT_RX_RING_0; rx_ring < BF_PKT_RX_RING_MAX; rx_ring++) {
    if (bf_pkt_rx_register(device, rx_packet_callback, rx_ring, NULL) != BF_SUCCESS) {
      printf("rx reg failed for ring %d (**unregister other handler)\n", rx_ring);
    }
  }
}

// UDP packet initialization.
void udppkt_init () {
  int i=0;
  if (bf_pkt_alloc(0, &upkt, udp_pkt_sz, BF_DMA_CPU_PKT_TRANSMIT_0) != 0) {
    printf("Failed bf_pkt_alloc\n");
  }
  uint8_t dstAddr[] = {0x3c, 0xfd, 0xfe, 0xad, 0x82, 0xe0};
  uint8_t srcAddr[] = {0x00, 0x00, 0x00, 0x00, 0x00, 0x11};
  memcpy(udp_pkt.dstAddr, dstAddr, 6);
  memcpy(udp_pkt.srcAddr, srcAddr, 6);
  udp_pkt.ethtype = htons(0x0800);
  udp_pkt.identification = htonl(0xDEADFACE);

  udp_pkt_8 = (uint8_t *) malloc(udp_pkt_sz);
  memcpy(udp_pkt_8, &udp_pkt, udp_pkt_sz);

  if (bf_pkt_is_inited(0)) {
    printf("Precord packet is initialized\n");
  }

  if (bf_pkt_data_copy(upkt, udp_pkt_8, udp_pkt_sz) != 0) {
    printf("Failed data copy\n");
  }

  printf("\n");
}

bf_pkt_tx_ring_t tx_ring = BF_PKT_TX_RING_1;
// Send UDP packets regularly by injecting from Control Plane.
void* send_udp_packets(void *args) {
  int sleep_time = 1000000;
  bf_status_t stat;
  while (1) {
      stat = bf_pkt_tx(0, upkt, tx_ring, (void *)upkt);
      if (stat  != BF_SUCCESS) {
       printf("Failed to send packet, status=%s\n", bf_err_str(stat));
     } else {
       printf("Packet sent!\n");
       int i = 0;
       for (i=0;i<upkt->pkt_size;i++) {
           printf("%X ", upkt->pkt_data[i]);
       }
       printf("\n\n\n");
     }
      usleep(sleep_time);
  }
}

int main (int argc, char **argv) {
	init_bf_switchd();
	init_tables();

  pthread_t udp_thread;

	printf("Starting chip Control Plane Unit ..\n");
  // Register TX & RX callback
	switch_pktdriver_callback_register(0);
  // UDP Packet initialization
  udppkt_init();
  // Sleep to wait for ASIC to finish initialization before sending packet
  sleep(3);
  // Now, send packets forever.
  pthread_create(&udp_thread, NULL, send_udp_packets, NULL);

  // Never hit
	pthread_join(udp_thread, NULL);
	return 0;
}
