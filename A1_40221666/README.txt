Execution Details:

GET COMMAND WITHOUT VERBOSE:  ./httpc get 'http://httpbin.org/get?course=networking&assignment=1'
 
GET COMMAND WITH VERBOSE: ./httpc get -v 'http://httpbin.org/get?course=networking&assignment=1'

POST COMMAND WITHOUT VERBOSE: ./httpc post -h Content-Type:application/json --d '{"Assignment": 1}' http://httpbin.org/post

POST COMMAND(ERROR CHECKING FOR --D AND --F): ./httpc post -h Content-Type:application/json --d '{"Assignment": 1}' --f Post_query.txt http://httpbin.org/post  

FILE OUTPUT COMMAND: ./httpc post -h Content-Type:application/json --d '{"Assignment": 1}'  http://httpbin.org/post -o hello.txt   

REDIRECT COMMAND: ./httpc get -v "http://httpbin.org/redirect/4"

