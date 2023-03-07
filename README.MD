# Introduction
This rate limiter is implemented with the combination of fixed window algorithm and sliding window algorithm. It limits the number of requests sent from an IP address       

example:        
upper_time_span_in_second = 60     
upper_request_allowance = 5     
lower_time_span_in_second = 1     
lower_request_allowance = 3

condition above tells us that:         
only 3 requests are allowed in one second time span     
only 5 requests are allowed in one minute time span

the number of request record in `1000000~1000060` time span in redis will look like:    
`127.0.0.1: { 1000000: 3, 1000001: 2 }`     
The sixth request comes in 1000001 time span will be blocked even though there are only 2 requests in 1000001 time span (lower_request_allowance is 3)


# Quick Start

install package management CLI(https://github.com/jazzband/pip-tools):
```
pip install pip-tools
```

generate `requirements.dev.txt`, `requirements.txt`:
```
pip-compile requirements.dev.in 
pip-compile requirements.in
```

install packages:
```
pip-sync requirements.txt requirements.dev.txt
```
run application:
```
make redis
make dev
```
go to browser and type:
```
http://localhost:8000/
```