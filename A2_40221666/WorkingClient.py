import socket
import argparse
from urllib.parse import urlparse
import ipaddress
from packet import Packet
from helpers import send_acks, send_packet, parse_http_request
class UDPClient:
    def __init__(self, target, met_name, router_host, router_port, server_host, server_port):
        self.target = target
        self.met_name = met_name
        self.router_host = router_host
        self.router_port = router_port
        self.server_host = server_host
        self.server_port = server_port
        self.total_packets = 100
        self.window_size = 3
        self.pending_packets = {}
        self.acknowledged_packets = set()
    def run_client(self, message, protocol_type, target_url, verbose_factor, o_file, o_filename,header,data):
        peer_ip = ipaddress.ip_address(socket.gethostbyname(self.server_host))
        conn = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        try:
            p = Packet(packet_type=1,
                       seq_num=1,
                       peer_ip_addr=peer_ip,
                       peer_port=self.server_port,
                       payload=message.encode("utf-8"))
            conn.sendto(p.to_bytes(), (self.router_host, self.router_port))
            print('Send "{}" to Router'.format(message))
            data, server = conn.recvfrom(1024)
            received_packet = Packet.from_bytes(data)
            if received_packet.packet_type != 2:
                print("Not valid")
                return
            else:
                print("Handshake successful")
                if protocol_type == "GET":
                    self.get_protocol(target_url, verbose_factor, o_file,
                                        o_filename,conn)
                if protocol_type == "POST":
                    self.post_protocol( target_url, verbose_factor, o_file, o_filename,conn,header,data)


        finally:
            conn.close()

    def get_protocol(self, target_url, verbose_factor, o_file, o_filename,conn):
        peer_ip = ipaddress.ip_address(socket.gethostbyname(self.server_host))

        target_content = urlparse(target_url)
        get_request = f"GET {target_content.path}?{target_content.query} HTTP/1.1\r\n" \
                      f"Host: {target_content.hostname}\r\n" \
                      "User-Agent: Concordia-HTTP/1.0\r\n" \
                      "\r\n"

        self.peer_ip = peer_ip
        try:
            self.send_request(conn, get_request)

        except socket.timeout:
            print("Timeout: No response received.")
        finally:
            conn.close()
    def post_protocol(self, target_url, verbose_factor, o_file, o_filename,conn,header,data):
        peer_ip = ipaddress.ip_address(socket.gethostbyname(self.server_host))

        target_content = urlparse(target_url)



        post_request=f"POST {target_content.path}?{target_content.query} HTTP/1.1\r\n"\
                     f"Host:{target_content.netloc}\r\n" \
                     "User-Agent: Concordia-HTTP/1.0\r\n" \
                     f"{header}\r\nContent-Length: {len(data)}\r\n\r\n{data}"
        self.peer_ip = peer_ip
        try:
            self.send_request(conn, post_request)

        except socket.timeout:
            print("Timeout: No response received.")
        finally:
            conn.close()


    def split_data_into_packets(self, data, max_packet_size):
        packets = []
        # print("split_data_into_packets ", self.peer_ip, self.peer_port)
        current_sequence=1
        for i in range(0, len(data), max_packet_size):
            payload = data[i:i + max_packet_size]
            packets.append(Packet(
                packet_type=0,
                seq_num=current_sequence+1,
                peer_ip_addr=self.peer_ip,
                peer_port=self.server_port,
                payload=payload.encode("utf-8")
            ))
            current_sequence=current_sequence+1
        # total_packets_packet = Packet(
        #     packet_type=1,
        #     seq_num=0,
        #     peer_ip_addr=self.peer_ip,
        #     peer_port=self.server_port,
        #     payload=str(len(packets)).encode("utf-8")
        # )
        # packets.insert(0, total_packets_packet)
        return packets

    def send_request(self, conn, request):
        ack_recieved=[]
        packets = self.split_data_into_packets(request, 1024)
        base = 1
        #print(base)
        #print(len(packets))
        while base <= len(packets):
            send_packet(conn, packets[base-1], (self.router_host, self.router_port))
            print("Sending packet",packets[base-1].seq_num)
            base += 1

        try:

            while True:
                conn.settimeout(5)


                response,sender=conn.recvfrom(1024)
                p = Packet.from_bytes(response)
                print(f"Received response from {p.peer_port}: {p.seq_num}")
                if p.seq_num not in ack_recieved:
                    ack_recieved.append(p.seq_num)
                if verbose_factor:
                    if o_file:
                        with open(o_filename, 'w') as file:
                            file.write(p.payload.decode())
                    else:
                        print(p.payload.decode("utf-8"))
                else:

                    if o_file:
                        with open(o_filename, 'w') as file:
                            file.write(p.payload.decode("utf-8"))
                    else:
                        print(p.payload.decode("utf-8"))
        except socket.timeout:
            for seq_num in range(2, len(packets)+2):
                if seq_num not in ack_recieved:
                    for i in packets:
                        if seq_num == i.seq_num:
                            conn.sendto(i.to_bytes(), (self.router_host, self.router_port))




if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--routerhost", help="router host", default="localhost")
    parser.add_argument("--routerport", help="router port", type=int, default=3000)
    parser.add_argument("--serverhost", help="server host", default="localhost")
    parser.add_argument("--serverport", help="server port", type=int, default=8007)
    parser.add_argument("protocol_type", help="Type of request")
    parser.add_argument("url", help="Real-time HTTP server url")
    parser.add_argument("-v", help="Verbose output from command-line", action="store_true")
    parser.add_argument("-d", help="POST data")
    parser.add_argument("-header", help="Headers")
    parser.add_argument("--f", help="Data in file")
    parser.add_argument("-o", help="Output file")
    args = parser.parse_args()
    protocol_type = args.protocol_type
    protocol_type = protocol_type.upper()
    target_url = args.url
    verbose_factor = args.v

    if args.o:
        o_file = True
    else:
        o_file = False
    o_filename = args.o

    print("Sender: ", args.routerhost, args.routerport)
    client = UDPClient(protocol_type, target_url, args.routerhost, args.routerport, args.serverhost, args.serverport)

    post_data=args.d
    client.run_client("HelloS", protocol_type, target_url, verbose_factor, o_file, o_filename,args.header,post_data)