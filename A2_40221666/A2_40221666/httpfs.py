import socket
import argparse
import threading
import re
import os


class httpfs:
    # run_server is to run the server. The server listens to the client who wants to connect.
    # Server can accept multiple clients by threading. Server would handle client in handle_client function
    def run_server(self, host, port, dir, debug):
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            listener.bind((host, port))
            listener.listen(10)
            if debug:
                print("Server is listening at port", port)
            while True:
                conn, addr = listener.accept()
                threading.Thread(target=self.handle_client, args=(conn, addr, dir)).start()
        except socket.error as e:
            print(f"Socket Error:{e}")
        finally:
            listener.close()

    ##handle_client recieves the data from requested by the client. It separates the body as well as the header.
    ##From header the handle_client function extracts the method and the path requested by the client.
    # Based on the request client calls specific methods
    def handle_client(self, conn, addr, dir):
        if debug:
            print("Client connected from", addr)
        try:
            while True:
                data = conn.recv(1024)
                if not data:
                    break
                data = data.decode('utf-8')
                header_full, body = data.split("\r\n\r\n")
                header = header_full.split("\r\n")
                method, path, _ = header[0].split()
                if method == 'GET':
                    self.process_get(conn, dir, path)
                elif method == "POST":
                    self.process_post(conn, dir, path, body)
        finally:
            conn.close()

    def print_response(self, status, content_type, content_disposition, response_body):
        header = {}
        content_length = len(response_body)
        header["Content-Length"] = content_length
        header["Content-Type"] = content_type
        header["Content-Disposition"] = content_disposition
        response = status + ''.join([f"{key}: {value}\r\n" for key, value in header.items()]) + "\r\n"
        return response, response_body

    def process_file(self, curr_dir_files, file_name, conn, dir):
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
                    conn.sendall(get_response.encode())
                    if debug:
                        print("HTTP/1.1 404 Content Not Found")
                    break
                get_response, response_body = self.print_response("HTTP/1.1 200 OK\r\n", Content_type,
                                                                  Content_disposition, content)
                conn.sendall(get_response.encode() + content)
                if debug:
                    print("HTTP/1.1 200 OK")
                break
        return flag

    ##If path ends with "/" then all the files are extracted from the current working directory and gets displayed.
    ##If filename present at end then filename would be extracted and the content of the file.
    def process_get(self, conn, dir, path):
        if path.endswith('/'):
            header={}
            if path.endswith('/'):
                curr_dir_files = os.listdir(dir)
                file_list = "File List:\n" + '\n'.join(curr_dir_files)

                response = "HTTP/1.1 200 OK\r\n"
                response += "Content-Type: text/plain\r\n"
                response += f"Content-Length: {len(file_list)}\r\n"
                response += "\r\n" + file_list


            if debug:
                "HTTP/1.1 200 OK"
            conn.sendall(response.encode())
        elif re.search(r'[^/]+/(.*)', path):
            flag = 0
            match = re.search(r'[^/]+/(.*)', path)
            if match:
                extracted_path = match.group(1)
            filerequest_path = os.path.join(dir, extracted_path)

            if not (os.path.abspath(filerequest_path)).startswith(os.path.abspath(dir)):
                get_response, response_body = self.print_response("HTTP/1.1 403 Forbidden\r\n", "text/plain", "inline",
                                                                  "HTTP/1.1 403 Forbidden\r\n")
                conn.sendall(get_response.encode())
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
                        conn.sendall(get_response.encode())
                        if debug:
                            print("HTTP/1.1 404 Path not found")
                    curr_dir_files = os.listdir(file_path)
                    flag = self.process_file(curr_dir_files, file_name, conn, file_path)
                else:
                    curr_dir_files = os.listdir(dir)
                    flag = self.process_file(curr_dir_files, file_name, conn, dir)
                if flag == 0:
                    get_response, response_body = self.print_response("HTTP/1.1 404 Not Found\r\n", "text/plain",
                                                                      "inline",
                                                                      "HTTP/1.1 404 Not Found\r\n")
                    conn.sendall(get_response.encode())
                    if debug:
                        print("HTTP/1.1 404 Not Found:File not found")

    def process_post(self, conn, dir, path, body):
        header = {}
        extract_filename = re.search(r'post/(.*)(\?)', path)
        ex_filepath = extract_filename.group(1)
        if not os.path.abspath(ex_filepath).startswith(os.path.abspath(dir)):
            post_response, response_body = self.print_response("HTTP/1.1 403 Forbidden\r\n", "text/plain", "inline",
                                                               "HTTP/1.1 403 Forbidden\r\n")

            conn.send(post_response.encode())
            print("HTTP/1.1 403 Forbidden:Access Denied: Cannot access files outside the server directory")

        else:
            if "/" not in ex_filepath:
                with open(ex_filepath, 'wb') as file:
                    file.write(body.encode())
                post_response, response_body = self.print_response("HTTP/1.1 200 OK\r\n", "text/plain", "inline",
                                                                   "File updated/created\n" + body)
                conn.sendall(post_response.encode())
                if debug:
                    print("HTTP/1.1 200 OK")
            else:
                parts = ex_filepath.split('/')
                dir_path = '/'.join(parts[:-1])
                if not os.path.exists(dir_path):
                    post_response, response_body = self.print_response("HTTP/1.1 404 Not Found\r\n", "text/plain",
                                                                       "inline",
                                                                       "HTTP/1.1 404 Not Found Path does not exist\r\n")
                    conn.sendall(post_response.encode())
                else:
                    file_path = os.path.join(dir, ex_filepath)
                    with open(file_path, 'wb') as file:
                        file.write(body.encode())
                    post_response, response_body = self.print_response("HTTP/1.1 200 OK\r\n", "text/plain",
                                                                       "inline",
                                                                       "File updated/created\n" + body)

                    conn.sendall(post_response.encode())
                    if debug:
                        print("HTTP/1.1 200 OK")


##Main function would take arguments. ALl of the arguments are optional.
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="HTTP Server")
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
    server = httpfs()
    server.run_server('', port, dir, debug)