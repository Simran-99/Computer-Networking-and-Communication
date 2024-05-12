
from packet import Packet

def split_data_into_packets(data, p, sender, max_packet_size):
    packets = []
    print("split_data_into_packets ", sender)
    for i in range(0, len(data), max_packet_size):
        payload = data[i:i + max_packet_size]
        packets.append(Packet(
            packet_type=0,
            seq_num=i // max_packet_size + 1,
            peer_ip_addr=p.peer_ip_addr,
            peer_port=p.peer_port,
            payload=payload.encode("utf-8")
        ))
    print("len(packets)  ", len(packets))
    packets.append(Packet(
            packet_type=3,
            seq_num=(i+max_packet_size) // max_packet_size + 1,
            peer_ip_addr=p.peer_ip_addr,
            peer_port=p.peer_port,
            payload=str(len(packets)).encode("utf-8")
        ))

    return packets

def create_http_response(status_code, headers, body):
    response = f'HTTP/1.1 {status_code}\r\n'    
    for key, value in headers.items():
        response += f'{key}: {value}\r\n'
    response += '\r\n'
    # if headers['Content-Type'] == 'image/jpeg':
    #     response = response.encode('utf-8') +body
    # else:
    response += body
    return response

def create_http_response(status_code, headers, body):
    response = f'HTTP/1.1 {status_code}\r\n'    
    for key, value in headers.items():
        response += f'{key}: {value}\r\n'
    response += '\r\n'
    response += body
    return response
    
def parse_http_request(request):
    print("******")
    print(request)
    lines = request.split('\r\n')
    method, path, _ = lines[0].split(' ')
    headers = {}
    body = ''
    parsing_body = False
    for line in lines[1:]:
        if not parsing_body:
            if line:
                key, value = line.split(': ')
                headers[key] = value
            else:
                parsing_body = True
        else:
            body += line
    return method, path, headers, body

def send_packet(conn, packet, router_address):
    conn.sendto(packet.to_bytes(), router_address)
    print(f'Send Packet {packet.seq_num} to Router')

def send_acks(self, p, conn, sender):
    # TODO: Add repeated seq_nums here!
    # if p.seq_num not in self.acknowledged_packets:
    p.packet_type = 2
    print("Sending ACK for ", p.seq_num)
    conn.sendto(p.to_bytes(), sender)
    self.acknowledged_packets.add(p.seq_num)


    
