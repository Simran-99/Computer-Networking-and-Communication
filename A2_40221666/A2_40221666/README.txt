RUN SERVER: ./httpfs

TEST COMMANDS:

GET ALL FILES IN THE WORKING DIRECTORY:

CURL: curl -v 'http://localhost:80/get?course=networking&assignment=1/'
httpc: python httpc.py GET 'http://localhost/get?course=networking&assignment=1/'

GET CONTENT OF FILE:
curl -v 'http://localhost:80/get?course=networking&assignment=1/helloworld'
httpc: python httpc.py GET 'http://localhost/get?course=networking&assignment=1/helloworld'

GET CONTENT OF FILE IN SUBDIRECTORY:
curl: curl -v 'http://localhost:80/get?course=networking&assignment=1/exapledir/foo'
httpc: python httpc.py GET 'http://localhost/get?course=networking&assignment=1/exapledir/foo'

REQUESTING PATH OUTSIDE SERVER WORKING DIRECTORY:
curl:curl -v 'http://localhost:80/get?course=networking&assignment=1/D:/Ineuron/Python/exapledir/foo'
httpc:python httpc.py GET -v 'http://localhost/get?course=networking&assignment=1/D:/Ineuron/exapledir/foo'

REQUESTING A FILE THAT DOES NOT EXIST:
httpc:python httpc.py GET -v 'http://localhost/get?course=networking&assignment=1/somefile'

POST A FILE: python httpc.py POST -h Content-Type:application/json --d '{"Assignment": 1}'-v http://localhost/post/la 

POST A FILE OUTSIDE DIRECTORY: python httpc.py POST -h Content-Type:application/json --d '{"Assignment": 1}'-v http://localhost/post/D:/Ineuorn/python/foo

CONCURRENT REQUEST:python Concurrentrequests.py


