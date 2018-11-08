spec_program = '''
// Spec for Sketch
|StateAndPacket| program (|StateAndPacket| state_and_packet) {
  state_and_packet.pkt_0 = state_and_packet.pkt_0 + 1;
  state_and_packet.pkt_1 = state_and_packet.pkt_0 + state_and_packet.pkt_1;
  state_and_packet.state_0 = state_and_packet.state_0 + 1;
  state_and_packet.state_1 = state_and_packet.state_0 + state_and_packet.state_1;
  state_and_packet.pkt_0 = state_and_packet.state_0 + state_and_packet.pkt_1;
  return state_and_packet;
}

'''
