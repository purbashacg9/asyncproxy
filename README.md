# Notes 

## Asynchronous proxy based on python's Tornado framework.

1. It accepts GET requests and passes them on to origin
servers. 
2. If the requests have byte ranges and they are validated for correctness. 
3. Accepts byte ranges as query params. If byte range in header does not
match the byte range in query param, 416 request is returned. 
4. Uses Tornado's asynchronous IO loops and coroutines for asyn behavior. 

## Configuration 
settings.conf contains config settings.  

## Dependencies 
1. tornado 4.3 
2. python 2.7 