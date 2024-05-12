import threading

from httpc import Httpc
from threading import Thread

def read_file(file, index):
    request = Httpc("GET", 'http://localhost/get?course=networking&assignment=1/' + file + str(index))
    request.get_protocol('http://localhost/get?course=networking&assignment=1/' + file, False,False, False)

def write_file(file,index):
    with file_lock:
        request=Httpc("POST",'http://localhost/post/'+ file + str(index))
        request.post_protocol('http://localhost/post/'+ file,{"Assignment": 1},'Content-Type:application/json',False,False,True)

print("READING THE FILES")
for i in range(0, 5):
    print("Reading to file by client", i)
    Thread(target=read_file, args=("hello", i)).start()

file_lock = threading.Lock()

print("WRITING THE FILES")
for i in range(0, 5):
    with file_lock:
        print("Writing to file by client",i)
        Thread(target=write_file, args=("hello", i)).start()

print("READ/WRITE CONCURRENTLY")
for i in range(0, 5):
    print("Reading to file by client",i)
    Thread(target=read_file, args=("hello", i)).start()
    print("Writing to file by client", i)
    Thread(target=write_file, args=("hello", i)).start()
