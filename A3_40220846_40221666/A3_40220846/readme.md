python3 UDPC.py GET 'http://localhost/get?course=networking&assignment=1/'
python3 UDPC.py POST -d 'ABCDS XYZ ABCDS XYZ ABCDS XYZ ABCDS XYZ ABCDS XYZ ABCDS XYZ ABCDS XYZ ABCDS XYZ ABCDS XYZ ABCDS XYZ ABCDS XYZ ABCDS XYZ ABCDS XYZ ABCDS XYZ ABCDS XYZ ABCDS XYZ ABCDS XYZ ABCDS XYZ ABCDS XYZ ABCDS XYZ ABCDS XYZ ABCDS XYZ ABCDS XYZ ABCDS XYZ ABCDS XYZ' 'http://localhost/Shel.txt'
python3 UDPC.py POST -d 'ABCDS' 'http://localhost/Shel.txt'

python3 ./old\ code/UDPclient.py POST -d 'ABCDS XYZ ABCDS XYZ ABCDS XYZ ABCDS XYZ ABCDS XYZ ABCDS XYZ ABCDS XYZ ABCDS XYZ ABCDS XYZ ABCDS XYZ ABCDS XYZ ABCDS XYZ ABCDS XYZ ABCDS XYZ ABCDS XYZ ABCDS XYZ ABCDS XYZ ABCDS XYZ ABCDS XYZ ABCDS XYZ ABCDS XYZ ABCDS XYZ ABCDS XYZ ABCDS XYZ ABCDS XYZ' 'http://localhost/Shel.txt'

python3 ./old\ code/UDPclient.py GET 'http://localhost/get?course=networking&assignment=1/'

## Helpful Commands to test

### To make python file executable run to following
- chmod +x UDPC.py
- export PATH=$PATH:$(pwd)
- UDPS

### To test run to following
- Get
    - python3 UDPC.py GET -v 'http://localhost/get?course=networking&assignment=1/Shel'
    - python3 UDPC.py GET -v 'http://localhost/get?course=networking&assignment=1/'

- Post
    - python3 UDPC.py POST -d 'ABCDS XYZ ABCDS XYZ ABCDS XYZ ABCDS XYZ ABCDS XYZ ABCDS XYZ ABCDS XYZ ABCDS XYZ ABCDS XYZ ABCDS XYZ ABCDS XYZ ABCDS XYZ ABCDS XYZ ABCDS XYZ ABCDS XYZ ABCDS XYZ ABCDS XYZ ABCDS XYZ ABCDS XYZ ABCDS XYZ ABCDS XYZ ABCDS XYZ ABCDS XYZ ABCDS XYZ ABCDS XYZ' 'http://localhost/Shel.txt'
    - python3 UDPC.py POST -d 'ABCDS' 'http://localhost/Shel.txt'