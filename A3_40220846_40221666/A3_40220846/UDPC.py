import socket
import argparse
from urllib.parse import urlparse, urlencode, parse_qs, urlunparse
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
        self.timeout_duration = 5

    def split_data_into_packets(self, data, max_packet_size):
        packets = []
        # print("split_data_into_packets ", self.peer_ip, self.peer_port)
        current_sequence = 1
        for i in range(0, len(data), max_packet_size):
            payload = data[i:i + max_packet_size]
            packets.append(Packet(
                packet_type=0,
                seq_num=current_sequence + 1,
                peer_ip_addr=self.peer_ip,
                peer_port=self.server_port,
                payload=payload.encode("utf-8")
            ))
            current_sequence = current_sequence + 1
        packets.append(Packet(
            packet_type=3,
            seq_num=current_sequence + 1,
            peer_ip_addr=self.peer_ip,
            peer_port=self.server_port,
            payload=str(len(packets)).encode("utf-8")
        ))
        return packets
    
    def receive_response(self, conn):
        response_packets = {}
        
        while True:
            try:
                conn.settimeout(self.timeout_duration * 10)
                response_packet, server = conn.recvfrom(1024)
                p = Packet.from_bytes(response_packet)
                print(f"Received response from {p.peer_port}: {p.seq_num}, {p.packet_type}")
                # print(f"packet {p}")
                
                if p.packet_type == 3:
                    total_packets = int(p.payload.decode("utf-8"))
                    keys = list(response_packets.keys())
                    print(len(keys), total_packets)
                    if len(keys) == total_packets:
                        send_acks(self, p, conn, (self.router_host, self.router_port))
                        body = b""
                        for x in response_packets:
                            body += response_packets[x]["body"]
                        # method, path, headers, body = parse_http_request(body.decode())   
                        print("80!! ", body.decode())
                        break
                
                elif p.packet_type == 0:
                    send_acks(self, p, conn, (self.router_host, self.router_port))
                
                    if p.seq_num not in response_packets:
                        response_packets[p.seq_num] = {"body": b""}
                        response_packets[p.seq_num]["body"] += p.payload
                        
            except socket.timeout:
                break
            except Exception as e:
                print("Error:", e)
        
       
        
        # if verbose_factor:
        #     if o_file:
        #         with open(o_filename, 'w') as file:
        #             file.write(p.payload.decode())
        #     else:
        #         print(p.payload.decode("utf-8"))
        # else:
        #     if o_file:
        #         with open(o_filename, 'w') as file:
        #             file.write(p.payload.decode("utf-8"))
        #     else:
        #         print("160  ",p.payload.decode("utf-8"))
    
    def send_request(self, conn, request):
        ack_received = set()
        packets = self.split_data_into_packets(request, 1024)
        base = 1

        while base <= len(packets):
            send_packet(conn, packets[base - 1], (self.router_host, self.router_port))
            print("Sending packet", packets[base - 1].seq_num)
            base += 1
        
        
        try:
            while True:
                conn.settimeout(self.timeout_duration)
                response, sender = conn.recvfrom(1024)
                p = Packet.from_bytes(response)
                # print(f"Received response from {p.peer_port}: {p.seq_num}")
                if p.seq_num not in ack_received:
                    ack_received.add(p.seq_num)
                    print("ack_received ", p.seq_num, ack_received)
                if len(ack_received) == len(packets):
                    break
            
            self.receive_response(conn)

        except socket.timeout:
            for seq_num in range(2, len(packets) + 2):
                if seq_num not in ack_received:
                    for i in packets:
                        if seq_num == i.seq_num:
                            conn.sendto(i.to_bytes(), (self.router_host, self.router_port))

    def get_protocol(self,target_url, verbose_factor, o_file,
                                      o_filename, conn):
        peer_ip = ipaddress.ip_address(socket.gethostbyname(self.server_host))
        conn = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
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
        # finally:
            # conn.close()

    def post_protocol(self, target_url, verbose_factor, o_file, o_filename, conn, header, data):
        peer_ip = ipaddress.ip_address(socket.gethostbyname(self.server_host))
        target_content = urlparse(target_url)

        post_request = f"POST {target_content.path} HTTP/1.1\r\n" \
                       f"Host: {target_content.hostname}\r\n" \
                       "User-Agent: Concordia-HTTP/1.0\r\n" \
                       f"Content-Length: {len(post_data)}\r\n" \
                       "\r\n" \
                       f"{post_data}\r\n"

        self.peer_ip = peer_ip
        try:
            self.send_request(conn, post_request)
        except socket.timeout:
            print("Timeout: No response received.")
        # finally:
            # conn.close()

    def run_client(self, message, protocol_type, target_url, verbose_factor, o_file, o_filename, header, data):
        peer_ip = ipaddress.ip_address(socket.gethostbyname(self.server_host))
        conn = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        max_retries = 4

        try:
            p = Packet(packet_type=1,
                    seq_num=1,
                    peer_ip_addr=peer_ip,
                    peer_port=self.server_port,
                    payload=message.encode("utf-8"))
            
            # Set a timeout for the socket
            
            # Initialize retry count
            retry_count = 0

            while retry_count < max_retries:
                conn.settimeout(self.timeout_duration)
                try:
                    conn.sendto(p.to_bytes(), (self.router_host, self.router_port))
                    print('Send "{}" to Router'.format(message))
                    data, server = conn.recvfrom(1024)
                    received_packet = Packet.from_bytes(data)

                    if received_packet.packet_type == 2:
                        # Break out of the loop if the handshake is successful
                        retry_count += 1
                        break
                    else:
                        print("Not a valid acknowledgment. Retrying...")
                        retry_count += 1

                except socket.timeout:
                    # Handle timeout
                    print("Timeout: No response received. Retrying...")
                    retry_count += 1

            if retry_count == max_retries:
                print("Maximum retries reached. Aborting.")
            else:
                print("Handshake successful ", protocol_type)
                if protocol_type == "GET":
                    self.get_protocol(target_url, verbose_factor, o_file, o_filename, conn)
                elif protocol_type == "POST":
                    self.post_protocol(target_url, verbose_factor, o_file, o_filename, conn, header, data)                        

        finally:
            print("CLOSING CONNECTION!!")
            # conn.close()



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
