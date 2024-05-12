import socket
import argparse
from packet import Packet
import os
import ipaddress
import traceback
import threading
import re
import urllib.parse
import time
from helpers import send_acks, send_packet, split_data_into_packets, parse_http_request, create_http_response

class UDPServer:
    
    def __init__(self, router_host, router_port):
        self.router_host = router_host
        self.router_port = router_port
        self.pending_packets = {}
        self.acknowledged_packets = set()
        self.request_packets = {}
        self.file_lock = threading.Lock()

    def send_acks(self, p, conn, sender):
        # TODO: Add repeated seq_nums here!
        # if p.seq_num not in self.acknowledged_packets:
        p.packet_type = 2
        print("Sending ACK for ", p.seq_num)
        conn.sendto(p.to_bytes(), sender)
        self.acknowledged_packets.add(p.seq_num)
    
    def receive_ack(self, conn, expected_seq_num, timeout):
        conn.settimeout(timeout)
        try:
            ack_data, _ = conn.recvfrom(1024)
            ack_packet = Packet.from_bytes(ack_data)
            if ack_packet.seq_num == expected_seq_num:
                return True
        except socket.timeout:
            pass
        return False
    
    def send_response(self, conn, p, response_body, status_code, headers,  sender):
        response = create_http_response(status_code, headers, response_body)
        response_arr = split_data_into_packets(response, p, sender, 1024)
        base = 1
        ack_received = set()
        pending_packets = set()
        try:
            while base <= len(response_arr):
                send_packet(conn, response_arr[base-1], (self.router_host, self.router_port))
                print(base-1, response_arr[base-1].seq_num)
                pending_packets.add(response_arr[base-1].seq_num)
                base += 1
            while len(pending_packets) != 0:
                # conn.settimeout(5)
                try:
                    response, sender = conn.recvfrom(1024)
                    p = Packet.from_bytes(response)
                    print(f"Received response from {p.peer_port}: {p.seq_num}")
                    if p.seq_num not in ack_received:
                        ack_received.add(p.seq_num)
                        pending_packets.remove(p.seq_num)
                        print("ack_received ", p.seq_num, ack_received)
                    if len(ack_received) == len(response_arr):
                        print("Response Recieved by Client!!")
                        self.pending_packets = {}
                        self.acknowledged_packets = set()
                        self.request_packets = {}
                        # conn.close()
                except socket.timeout:
                    for i in pending_packets:
                        send_packet(conn, response_arr[i-1], (self.router_host, self.router_port))
                        # conn.sendto(i.to_bytes(), (self.router_host, self.router_port))
        except Exception as e:
            print("Error in send_response:", e)

    
    def parse_http_request(self, request):
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

    def handle_client(self, conn, data, sender):
        try:
            p = Packet.from_bytes(data)
            print("Packet Seq Num:", p.seq_num, p.packet_type)

            if p.seq_num == 1:
                self.send_acks(p, conn, sender)
            elif p.packet_type == 3:
                total_packets = int(p.payload.decode("utf-8"))
                if len(self.request_packets) == total_packets:
                    self.send_acks(p, conn, sender)
                    body = b""
                    for x in self.request_packets:
                        body += self.request_packets[x]["body"]
                        
                    print("118!! ", body.decode())
                    
                    method, path, headers, body = self.parse_http_request(body.decode())
                    
                    if method == "GET":
                        return self.process_get(conn, dir, path, sender, p)
                    elif method == "POST":
                        return self.process_post(conn, dir, path, body, sender, p)
            elif p.packet_type == 0:
                self.send_acks(p, conn, sender)
                if p.seq_num not in self.request_packets:
                    self.request_packets[p.seq_num] = {"header": "", "body": b""}
                    self.request_packets[p.seq_num]["body"] += p.payload
                
        except Exception as e:
            print(traceback.format_exc())
            print("Error:", e)
        
    
    def print_response(self, status, content_type, content_disposition, response_body):
        header = {}
        content_length = len(response_body)
        header["Content-Length"] = content_length
        header["Content-Type"] = content_type
        header["Content-Disposition"] = content_disposition
        response = status + ''.join([f"{key}: {value}\r\n" for key, value in header.items()]) + "\r\n"
        return response, response_body

    def process_file(self, curr_dir_files, file_name, conn, dir,p,sender):
        flag = 0
        Content_type = "text/plain"
        Content_disposition = "inline"
        for f in curr_dir_files:
            if file_name in f:
                file_path = os.path.join(dir, f)
                flag = 1
                with open(file_path, 'r') as file:
                    content = file.read()
                status_code = "200 OK"

                if not content:
                    get_response, response_body = self.print_response("HTTP/1.1 404 Content Not Found\r\n",
                                                                      Content_type, Content_disposition,
                                                                      "HTTP/1.1 404 Content Not Found\r\n")
                    status_code = "404 Content Not Found"
                else:
                    get_response, response_body = self.print_response("HTTP/1.1 200 OK\r\n", Content_type,
                                                                  Content_disposition, content)
                    get_response += content
                
                self.send_response(conn, p, get_response, status_code, {}, sender)
                if debug:
                    print("HTTP/1.1 200 OK")
                break
        return flag

    def process_post(self,conn, dir, path, body, sender, p):
        header = {}
        if path == '/':
            response_body = "Bad Request\nFile not defined!"
            status_code = '400 Bad Request'
            content_length = len(response_body)
            header["Content-Length"] = content_length
            self.send_response(conn, p, response_body, status_code, header, sender)
        else:
            # Return the content of the requested file
            file_path = os.path.join(dir, path.lstrip('/'))
            try:
                self.file_lock.acquire()
                
                with open(file_path, "w") as file:
                    file.write(body)
                response_body = f"File '{path.lstrip('/')}' created/overwritten successfully"
                status_code = '200 OK'
                content_length = len(response_body)
                header["Content-Length"] = content_length
                print("File done!")
                self.file_lock.release()
                self.send_response(conn, p, response_body, status_code, header, sender)
            except Exception as e:
                response_body = f"Error creating or overwriting file: {str(e)}"
                status_code = "500 Internal Server Error"
                content_length = len(response_body)
                header["Content-Length"] = content_length
                self.send_response(conn, p, response_body, status_code, header, sender)
            # finally:
        # return response_body, status_code    

    def process_get(self, conn, dir, path, sender, p):
        header = {}

        if path.endswith('/'):
            curr_dir_files = os.listdir(dir)
            file_list = "File List:\n" + '\n'.join(curr_dir_files)

            response = "HTTP/1.1 200 OK\r\n"
            response += "Content-Type: text/plain\r\n"
            response += f"Content-Length: {len(file_list)}\r\n"
            response += file_list

            response_body = response
            status_code = '200 OK'
            content_length = len(response)
            header["Content-Length"] = content_length
            self.send_response(conn, p, response_body, status_code, header,  sender)
            
        elif re.search(r'[^/]+/(.*)', path):
            flag = 0
            match = re.search(r'[^/]+/(.*)', path)
            if match:
                extracted_path = match.group(1)
            filerequest_path = os.path.join(dir, extracted_path)

            if not (os.path.abspath(filerequest_path)).startswith(os.path.abspath(dir)):
                get_response, response_body = self.print_response("HTTP/1.1 403 Forbidden\r\n", "text/plain", "inline",
                                                                  "HTTP/1.1 403 Forbidden\r\n")
                status_code = '403 Forbidden'
                content_length = len(response_body)
                header["Content-Length"] = content_length
                self.send_response(conn, p, response_body, status_code, header, sender)
                if debug:
                    print("HTTP/1.1 403 Forbidden:Access Denied: Cannot access files outside the server directory")
            else:
                file_name = filerequest_path.split('/')[-1]
                file_name = file_name + "."
                if "/" in extracted_path:
                    parts = extracted_path.split('/')
                    dir_path = '/'.join(parts[:-1])
                    file_path = os.path.join(dir, dir_path)
                    if not os.path.exists(file_path):
                        get_response, response_body = self.print_response("HTTP/1.1 404 Not Found\r\n", "text/plain",
                                                                          "inline",
                                                                          "HTTP/1.1 404 Not Found\r\n")
                        status_code = '404 Not Found'
                        content_length = len(response_body)
                        header["Content-Length"] = content_length
                        self.send_response(conn, p, response_body, status_code, header, sender)
                        if debug:
                            print("HTTP/1.1 404 Path not found")
                    curr_dir_files = os.listdir(file_path)
                    flag = self.process_file(curr_dir_files, file_name, conn, file_path,p,sender)
                else:
                    curr_dir_files = os.listdir(dir)
                    flag = self.process_file(curr_dir_files, file_name, conn, dir,p,sender)
                if flag == 0:
                    get_response, response_body = self.print_response("HTTP/1.1 404 Not Found\r\n", "text/plain",
                                                                      "inline",
                                                                      "HTTP/1.1 404 Not Found\r\n")
                    status_code = '404 Not Found'
                    content_length = len(response_body)
                    header["Content-Length"] = content_length
                    if debug:
                        print("HTTP/1.1 404 Not Found:File not found")

    def run_server(self, host, port):
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        server_socket.bind(('', port))
        print('Echo server is listening at', port)

        try:
            while True:
                data, sender = server_socket.recvfrom(1024)
                print("Received data from", sender)
                p = Packet.from_bytes(data)
                self.send_acks(p, server_socket, sender)
                # conn = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                self.handle_client(server_socket, data, sender)
        except Exception as e:
            print("Error in server:", e)
        # finally:
        #     self.pending_packets = {}
        #     self.acknowledged_packets = set()
        #     self.request_packets = {}
            # server_socket.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--routerhost", help="router host", default="localhost")
    parser.add_argument("--routerport", help="router port", type=int, default=3000)
    parser.add_argument("--port", help="echo server port", type=int, default=8007)
    parser.add_argument("-v", action="store_true", help="Debugging", default=False)
    parser.add_argument("-p", action="store", help="PORT", default=80)
    parser.add_argument("-d", help="Directory to be used to read/write requested files", default="./")
    args = parser.parse_args()
    port = args.p
    if args.d:
        dir = args.d
    else:
        dir = os.path.dirname(os.path.realpath(__file__))
    debug = args.v
    args = parser.parse_args()
    server=UDPServer(args.routerhost, args.routerport)
    server.run_server("localhost", args.port)
