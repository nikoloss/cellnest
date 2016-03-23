class HttpMethodNotAllowed(Exception):
    state = '405'
    content = '(405): method is forbidden'