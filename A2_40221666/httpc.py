import socket
import argparse
import time
from urllib.parse import urlparse,urlunparse
import sys

class Httpc:
    #Created a class httpc. Passing the target url and the method name(such as GET, POST, HELP) as arguments
    def __init__(self, target, met_name):
        self.target = target
        self.met_name = met_name

    #Bonus Question: In case a redirection code is recieved. The url would be redirected
    def reddirection(self,get_reply):
        header=get_reply.split("\r\n")
        print(header)
        #Extracting the header with rediirection code
        split_header=header[0].split(" ")
        if len(split_header) < 2 or not split_header[1].isdigit():
            return None
        status_code=int(split_header[1])

        loc=None
        #Redirection only done if status code between 300 and 400
        if status_code>=300 and status_code<=400:
            #Finding the location towhere the url is supposed to be sent.
            for h in header:
                if(("Location: ") in h) or(("location: ") in h) :
                    head_split=h.split(": ")
                    loc=head_split[1]
            if(loc):
                print("Redirected to ",loc)

                return loc

    #Function to get the input from the file
    def read_file(self,filename):
        with open(filename,'r') as file:
            content=file.read()
            return content

    #Creating help method to print the way GET/POST can be used
    def help_method(self,p_arg):

        p_arg=p_arg.upper()
        if p_arg == "GET":
            print("usage: httpc get [-v] [-h key:value] URL \n")
            print("Get executes a HTTP GET request for a given URL.\n")
            print("-v                  Print the details of the response such as protocol, status and header\n")
            print("-h key:value        Associates headers to HTTP requests with the format 'key:value\n")
        elif p_arg == "POST":
            print("usage: httpc post [-v] [-h key:value] [-d inline-data] [-f file] URL \n")
            print("Post executes a HTTP POST request for a given URL with inline data or from file.\n")
            print("-v                  Print the details of the response such as protocol, status and header\n")
            print("-h key:value        Associates headers to HTTP requests with the format 'key:value\n")
            print("-d string           Associates an inline data to the body HTTP POST request\n")
            print("-f file             Associates the content of a file to the body HTTP POST\n")
        elif p_arg==None:
            print("httpc is a curl-like application but supports HTTP protocol only. ")
            print("Usage:\n")
            print("    httpc command [arguments]\n")
            print("The commands are: \n")
            print("    get     executes a HTTP GET request and prints the response. \n")
            print("    post    executes a HTTP POST request and prints the response.\n")
            print("    help    prints this screen.")



    #Function to handle GET request
    #Socket connection is being made.
    #A GET request is created with all the relevant parameters such as path, query parameters and host name
    #After response being recieved , the output is formated beased on options selected
    def get_protocol(self, target,v_factor,o_file,o_filename):
        target_content = urlparse(target)
        target_port = target_content.port if target_content.port is not None else 80
        conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        conn.connect((target_content.netloc, 80))
        get_request = f"GET {target_content.path}?{target_content.query} HTTP/1.1\r\n" \
                      f"Host: {target_content.hostname}\r\n" \
                      "User-Agent: Concordia-HTTP/1.0\r\n" \
                      "\r\n"
        conn.sendall(get_request.encode())
        time.sleep(2)
        get_respone = (conn.recv(4096))
        loc = self.reddirection(get_respone.decode())
        if loc:
            url = urlunparse(target_content._replace(path=loc))

            return self.get_protocol(url, v_factor, o_file, o_filename)
        if v_factor:
            if o_file:
                with open(o_filename, 'w') as file:
                    file.write(get_respone.decode())
            else:
                print(get_respone.decode())
        else:
            header, bpdy = get_respone.split(b"\r\n\r\n", 1)
            if o_file:
                with open(o_filename, 'w') as file:
                    file.write(bpdy.decode("utf-8"))
            else:
                print(bpdy.decode("utf-8"))

    #Following is code to send a POST request
    #A socket connection is developed and then POST request is being created and sent
    #Based on the format requirements the response would be printed

    def post_protocol(self, target,data,header,o_file,o_filename,v_factor):
        target_content = urlparse(target)
        target_port = target_content.port if target_content.port is not None else 80
        print(target_content.netloc)
        print(target_port)

        conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        conn.connect((target_content.netloc, 80))
        post_request=f"POST {target_content.path}?{target_content.query} HTTP/1.1\r\n"\
                     f"Host:{target_content.netloc}\r\n" \
                     "User-Agent: Concordia-HTTP/1.0\r\n" \
                     f"{header}\r\nContent-Length: {len(data)}\r\n\r\n{data}"

        conn.sendall(post_request.encode())
        time.sleep(2)
        post_response = (conn.recv(4096))
        if v_factor:
            if o_file:
                with open(o_filename,"w") as f:
                   f.write(post_response.decode())
            else:
                print(post_response.decode())
        else:
            header, bpdy = post_response.split(b"\r\n\r\n", 1)
            if o_file:
                with open(o_filename, 'w') as file:
                    file.write(bpdy.decode())
            else:
                print(bpdy.decode())
            conn.close()


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="HTTP POST/GET requests")
    #print(sys.argv)
    if len(sys.argv)==1 and sys.argv[0].upper()=="HELP":
        print("httpc is a curl-like application but supports HTTP protocol only. ")
        print("Usage:\n")
        print("    httpc command [arguments]\n")
        print("The commands are: \n")
        print("    get     executes a HTTP GET request and prints the response. \n")
        print("    post    executes a HTTP POST request and prints the response.\n")
        print("    help    prints this screen.")
        sys.exit()

    for i in range(len(sys.argv)):
        if sys.argv[i]=='-h':
            sys.argv[i]='-header'




    #Accepting all the arguments.
    parser.add_argument("protocol_type", help="Type of request")
    parser.add_argument("url", help="Real-time HTTP server url")
    parser.add_argument("-v",help="Verbose output from command-line",action="store_true")
    parser.add_argument("--d", help="POST data")
    parser.add_argument("-header", help="Headers")
    parser.add_argument("--f",help="Data in file")
    parser.add_argument("-o",help="Output file")


    args = parser.parse_args()
    protocol_type = args.protocol_type
    protocol_type=protocol_type.upper()

    target_url = args.url


    #print(args.v)
    #print(target_url)
    verbose_factor=args.v

    if args.o:
        o_file=True
    else:
        o_file=False
    o_filename=args.o


    #try:
    client = Httpc(protocol_type, target_url)

    if protocol_type == "HELP":
        print(target_url)
        if target_url:
            client.help_method(target_url)
        else:
            client.help_method(None)
    elif protocol_type == "GET":
        client.get_protocol(target_url, verbose_factor, o_file, o_filename)
    elif protocol_type == "POST":
        if args.d and args.f:
            client.help_method("POST")
            print("Either [-d] or [-f] can be used but not both.")
        elif args.d:
            data = args.d
            # print(data)
            headers = args.header if args.header else 'Content-Type: application/json'
            client.post_protocol(target_url, data, headers, o_file, o_filename, verbose_factor)
        elif args.f:
            filename = args.f
            data = client.read_file(filename)
            headers = args.header if args.header else 'Content-Type: application/json'
            client.post_protocol(target_url, data, headers, o_file, o_filename, verbose_factor)

    # except Exception as e:
    #       print("httpc is a curl-like application but supports HTTP protocol only. ")
    #       print("Usage:\n")
    #       print("    httpc command [arguments]\n")
    #       print("The commands are: \n")
    #       print("    get     executes a HTTP GET request and prints the response. \n")
    #       print("    post    executes a HTTP POST request and prints the response.\n")
    #       print("    help    prints this screen.")




