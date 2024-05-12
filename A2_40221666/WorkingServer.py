import socket
import argparse
from packet import Packet
import os
import ipaddress
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
        self.file_lock = threading.Lock()

    def run_server(self, host, port):
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        server_socket.bind(('', port))
        print('Echo server is listening at', port)

        try:
            while True:
                data, sender = server_socket.recvfrom(1024)
                print("Received data from", sender)
                print("Data:", data)
                self.handle_client(server_socket, data, sender)
        except Exception as e:
            print("Error in server:", e)
        finally:
            server_socket.close()

    def send_acks(self, p, conn, sender):
        # TODO: Add repeated seq_nums here!
        if p.seq_num not in self.acknowledged_packets:
            p.packet_type = 2
            print("Sending ACK for ", p.seq_num)
            conn.sendto(p.to_bytes(), sender)
            self.acknowledged_packets.add(p.seq_num)

        # Check if all ACKs have been received
        # if len(self.acknowledged_packets) == self.total_packets + 1:
        #     # Clear arrays when all ACKs are received
        #     self.acknowledged_packets.clear()
        #     self.pending_packets = {}
        #     return
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
                with open(file_path, 'rb') as file:
                    content = file.read()
                if ".html" in file_path:
                    Content_type = "text/html"
                    Content_disposition = "inline"
                elif ".json" in file_path:
                    Content_type = "application/json"
                    Content_disposition = "attachment;filename='example.json'"
                elif ".png" in file_path:
                    Content_type = "image/png"
                    Content_disposition = "attachment;filename='example.png'"
                else:
                    Content_type = "text/plain"
                    Content_disposition = "inline"

                if not content:
                    get_response, response_body = self.print_response("HTTP/1.1 404 Content Not Found\r\n",
                                                                      Content_type, Content_disposition,
                                                                      "HTTP/1.1 404 Content Not Found\r\n")
                    p.payload = get_response.encode()
                    conn.sendto(p.to_bytes(), sender)
                    if debug:
                        print("HTTP/1.1 404 Content Not Found")
                    break
                get_response, response_body = self.print_response("HTTP/1.1 200 OK\r\n", Content_type,
                                                                  Content_disposition, content)

                p.payload = get_response.encode()+content
                conn.sendto(p.to_bytes(), sender)
                if debug:
                    print("HTTP/1.1 200 OK")
                break
        return flag

    def process_get(self, conn, dir, path, sender, p):
        if path.endswith('/'):
            curr_dir_files = os.listdir(dir)
            file_list = "File List:\n" + '\n'.join(curr_dir_files)

            response = "HTTP/1.1 200 OK\r\n"
            response += "Content-Type: text/plain\r\n"
            response += f"Content-Length: {len(file_list)}\r\n"
            response += "\r\n" + file_list
            p.payload = response.encode()
            #p.packet_type = 2
            #print("Sending ACK for ", p.seq_num)
            self.send_acks(p,conn,sender)
            #conn.sendto(p.to_bytes(), sender)
        elif re.search(r'[^/]+/(.*)', path):
            flag = 0
            match = re.search(r'[^/]+/(.*)', path)
            if match:
                extracted_path = match.group(1)
            filerequest_path = os.path.join(dir, extracted_path)

            if not (os.path.abspath(filerequest_path)).startswith(os.path.abspath(dir)):
                get_response, response_body = self.print_response("HTTP/1.1 403 Forbidden\r\n", "text/plain", "inline",
                                                                  "HTTP/1.1 403 Forbidden\r\n")
                p.payload = get_response.encode()
                conn.sendto(p.to_bytes(), sender)
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
                        p.payload = get_response.encode()
                        conn.sendto(p.to_bytes(), sender)
                        if debug:
                            print("HTTP/1.1 404 Path not found")
                    curr_dir_files = os.listdir(file_path)
                    flag = self.process_file(curr_dir_files, file_name, conn, file_path, p, sender)
                else:
                    curr_dir_files = os.listdir(dir)
                    flag = self.process_file(curr_dir_files, file_name, conn, dir, p, sender)
                if flag == 0:
                    get_response, response_body = self.print_response("HTTP/1.1 404 Not Found\r\n", "text/plain",
                                                                      "inline",
                                                                      "HTTP/1.1 404 Not Found\r\n")
                    p.payload = get_response.encode()
                    conn.sendto(p.to_bytes(), sender)
                    if debug:
                        print("HTTP/1.1 404 Not Found:File not found")

    def process_post(self, conn, dir, path, body,sender,p):

        header = {}
        extract_filename = re.search(r'post/(.*)(\?)', path)
        ex_filepath = extract_filename.group(1)
        if not os.path.abspath(ex_filepath).startswith(os.path.abspath(dir)):
            post_response, response_body = self.print_response("HTTP/1.1 403 Forbidden\r\n", "text/plain", "inline",
                                                               "HTTP/1.1 403 Forbidden\r\n")
            p.payload=post_response.encode()
            conn.sendto(p.to_bytes(), sender)


        else:
            if "/" not in ex_filepath:
                with open(ex_filepath, 'wb') as file:
                    file.write(body.encode())
                post_response, response_body = self.print_response("HTTP/1.1 200 OK\r\n", "text/plain", "inline",
                                                                   "File updated/created\n" + body)
                p.payload=post_response.encode()
                conn.sendto(p.to_bytes(), sender)
                if debug:
                    print("HTTP/1.1 200 OK")
            else:
                parts = ex_filepath.split('/')
                dir_path = '/'.join(parts[:-1])
                if not os.path.exists(dir_path):
                    post_response, response_body = self.print_response("HTTP/1.1 404 Not Found\r\n", "text/plain",
                                                                       "inline",
                                                                       "HTTP/1.1 404 Not Found Path does not exist\r\n")
                    p.payload = post_response.encode()
                    conn.sendto(p.to_bytes(), sender)
                else:
                    file_path = os.path.join(dir, ex_filepath)
                    with open(file_path, 'wb') as file:
                        file.write(body.encode())
                    post_response, response_body = self.print_response("HTTP/1.1 200 OK\r\n", "text/plain",
                                                                       "inline",
                                                                       "File updated/created\n" + body)

                    p.payload = post_response.encode()
                    conn.sendto(p.to_bytes(), sender)
                    if debug:
                        print("HTTP/1.1 200 OK")

    def process_request(self, conn, sender, p):
        try:
            body = b""
            for x in self.pending_packets:
                body += self.pending_packets[x]["body"]

            print("80!! ", body.decode())

            method, path, headers, body = parse_http_request(body.decode())
            path = urllib.parse.unquote(path)
            print("Method:", method)
            print("Path:", path)
            print("Body:", body)
            print("Sender: ", sender[0], sender[1])

            if method == "GET":
                # self.process_get(conn, dir, path, sender, p)
                response_body = "router.exe UDPclient.py httpfs.py UDPC.py __pycache__ UDPServer.py router.log Shalvi_Simran.py CC.txt"
                status_code = '200 OK'
                content_type = 'text/plain'
                content_len = len(response_body)
                headers = {'Content-Type': content_type, 'Content-Deposition': 'inline', 'Content-Length': content_len}
                self.send_response(conn, p, response_body, status_code, headers, sender)
            elif method == "POST":
                response_body, status_code = self.process_post(path, body)
                content_type = 'text/plain'
                content_len = len(response_body)
                headers = {'Content-Type': content_type, 'Content-Deposition': 'inline', 'Content-Length': content_len}
                self.send_response(conn, p, response_body, status_code, headers, sender)

        except Exception as e:
            print("Error processing request:", e)
        finally:
            self.acknowledged_packets.clear()
            self.pending_packets = {}

    def send_response(self, conn, p, response_body, status_code, headers, sender):
        response = create_http_response(status_code, headers, response_body)
        print("49  ", response)
        response_arr = split_data_into_packets(response, p, sender, 1024)

        base = 1
        while base <= len(response_arr):
            send_packet(conn, response_arr[base - 1], (self.router_host, self.router_port))
            p.packet_type = 2
            print("Sending ACK for ", p.seq_num)
            conn.sendto(p.to_bytes(), sender)
            base += 1
            # ack_received = False
            # while not ack_received:
            #     ack_received = self.receive_ack(conn, base, 5
    def handle_client(self, conn, data, sender):
        try:
            p = Packet.from_bytes(data)
            print("Packet Seq Num:", p.seq_num)

            if p.seq_num == 1:
                self.send_acks(p, conn, sender)
            else:
                header_full, body = p.payload.decode().split("\r\n\r\n")
                header = header_full.split("\r\n")
                method, path, _ = header[0].split()
                if method=="GET":
                    self.process_get(conn, dir, path,sender,p)
                elif method=="POST":
                    self.process_post(conn, dir, path, body,sender,p)


            #elif p.packet_type == 0:
                #send_acks(self, p, conn, sender)

                # if p.seq_num not in self.pending_packets:
                #     self.pending_packets[p.seq_num] = {"header": "", "body": b""}
                #     self.pending_packets[p.seq_num]["body"] += p.payload
                #
                # if len(self.pending_packets) == self.total_packets:
                #     self.process_request(conn, sender, p)

        except Exception as e:
            print("Error:", e)
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
    server = UDPServer(args.routerhost, args.routerport)
    server.run_server("localhost", args.port)