import os
import socket
import threading

moved_302 = {"/imgs/abstract.jpg": "/imgs/ghostboi.jpg"}

exit_all = False

PORT = 80
PROTOCOL = 'HTTP/1.1'


def http_send(s, reply, reply_headers, reply_body):
    """ add Content-Length header if needed and send reply """
    if reply_body:
        reply_headers += b"Content-Length: " + str(len(reply_body)).encode() + b"\r\n"
    reply_headers += b"\r\n"
    reply = reply + reply_headers + reply_body
    s.send(reply)
    print('SENT:', reply[:100])
    print()


def recv_size(sock, size):
    """ receive size with socket, returns data or b'' if client disconnected"""
    data = sock.recv(size)
    while len(data) < size:
        new_data = sock.recv(size - len(data))
        if new_data == b'':
            return b''
        data += new_data
    return data


def http_recv(sock):
    """
    receive the request from the client
    :param sock: the client socket
    :return: the command + URL, the headers, the body | b'', b'', b'' if an error has occurred/client disconnected
    """
    data = b''
    try:
        while data[-4:] != b"\r\n\r\n":  # receive command and headers
            new_data = sock.recv(1)
            if new_data == b'':
                print('[http_recv] seems client disconnected, client socket will close')
                return b'', b'', b''
            data += new_data
        print('Received:', data[:100])
        print()
        request = data.split(b"\r\n")[0].decode().split(" ")
        headers = data.decode()

        body = b''
        if "Content-Length: " in headers:  # receive body
            start_header = headers.find("Content-Length: ") + len("Content-Length: ")
            end_header = [index for index in range(start_header, len(headers)) if headers.startswith("\r\n", index)][0]
            body = recv_size(sock, int(headers[start_header:end_header]))
            if body == b'':
                print('[http_recv] seems client disconnected, client socket will close')
                return b'', b'', b''

        headers = headers.split("\r\n")[1:-2]
        return request, headers, body

    except socket.timeout:
        print("[http_recv] Socket timeout; client socket will close")
        return b'', b'', b''
    except Exception:
        print("[http_recv]: Error; client socket will close")
        return b'', b'', b''


def validate_request(request):
    """ Check if request is a valid HTTP request and returns TRUE / FALSE """

    if request[0] != 'GET' and request[0] != 'POST':  # checking if command is ok
        print("[validate_request] command type missing or not supported")
        return False
    elif request[2] != PROTOCOL:  # checking if same protocol
        print("[validate_request] Protocol name missing or different")
        return False

    return True


def get_type_header(file):
    """ return the Content-Type header according to the type of file, if type not supported return b'' """
    end = file.split(".")[-1]
    header = b"Content-Type: "
    if end == "txt" or end == "html":
        return header + b"text/html; charset=utf-8"
    elif end == "jpg":
        return header + b"image/jpeg"
    elif end == "js":
        return header + b"text/javascript; charset=UTF-8"
    elif end == "css":
        return header + b"text/css"
    elif end == "ico":
        return header + b"image/x-icon"
    elif end == "gif":
        return header + b"image/gif"
    print("[get_type_header] Error: doesn't support file")
    return b''


def get_file_data(file):
    """ read file and return data, if error return b'' """
    try:
        with open(file[1:], "rb") as f:
            return f.read()
    except Exception:
        print("[get_file_data] Error: failed to read file")
        return b''
    

def calculate_next(url):
    """ return the reply + status, headers and body (= num in URL + 1 or b'' if error) """
    try:
        if url[1][:4] == "num=":
            num = url[1][4:]
            headers = b"Content-Type: text/plain\r\n"
            return PROTOCOL.encode() + b" 200 OK\r\n", headers, str(int(num) + 1).encode()
        print("[calculate_next] Error: invalid URL")
        return PROTOCOL.encode() + b" 500 Internal Server Error\r\n", b'', b''
    except Exception as e:
        print("[calculate_next] Error:", e)
        return PROTOCOL.encode() + b" 500 Internal Server Error\r\n", b'', b''


def calculate_area(url):
    """ return the reply + status, headers and body (= height * width / 2 or b'' if error) """
    try:
        if ("height=" in url[1] and "&width=" in url[1]) or ("&height=" in url[1] and "width=" in url[1]):
            s1 = int(url[1].split("&")[0].split("=")[1])
            s2 = int(url[1].split("&")[1].split("=")[1])
            area = s1 * s2 / 2
            headers = b"Content-Type: text/plain\r\n"
            return PROTOCOL.encode() + b" 200 OK\r\n", headers, str(area).encode()
        print("[calculate_area] Error: invalid URL")
        return PROTOCOL.encode() + b" 500 Internal Server Error\r\n", b'', b''
    except Exception as e:
        print("[calculate_area] Error:", e)
        return PROTOCOL.encode() + b" 500 Internal Server Error\r\n", b'', b''


def image(url):
    """ return the reply + status, headers and body (= image bytes or b'' if error) """
    try:
        f_name = url[1][11:]
        if url[1][:11] == "image-name=":
            if os.path.isfile("uploads\\" + f_name):
                with open("uploads\\" + f_name, "rb") as f:
                    body = f.read()
                headers = f"Content-Type: {get_type_header(f_name)}\r\n".encode()
                return PROTOCOL.encode() + b" 200 OK\r\n", headers, body
            print("[image] Error: file not found")
            return PROTOCOL.encode() + b" 404 Not Found\r\n", b'', b''
        print("[image] Error: invalid URL")
        return PROTOCOL.encode() + b" 500 Internal Server Error\r\n", b'', b''
    except Exception as e:
        print("[image] Error:", e)
        return PROTOCOL.encode() + b" 500 Internal Server Error\r\n", b'', b''


def handle_get(request):
    """ handle the GET command and return the appropriate reply"""
    file = request[1]
    if request[1] == "/":
        file += "index.html"

    url = request[1].split("?")
    if len(url) == 2:
        if url[0] == "/calculate-next":
            return calculate_next(url)
        if url[0] == "/calculate-area":
            return calculate_area(url)
        if url[0] == "/image":
            return image(url)
    if file in moved_302.keys():
        return PROTOCOL.encode() + b" 302 Found\r\n", f"Location: {moved_302[file]}\r\n".encode(), b''

    status = b" 200 OK"
    headers = b''
    body = b''

    file = file.replace("/", "\\")
    if os.path.isfile(file[1:]):
        if not os.access(file[1:], os.R_OK):
            print("[handle_get] Error: no access to file")
            return PROTOCOL.encode() + b" 403 Forbidden\r\n", b'', b''
        f_data = get_file_data(file)
        type_header = get_type_header(file)
        if f_data == b'' or type_header == b'':
            status = b''
        else:
            body = f_data
    else:
        print("[handle_get] Error: file not found")
        status = b" 404 Not Found"

    return PROTOCOL.encode() + status + b"\r\n", headers, body


def handle_post(request, request_headers, body):
    """ handle the POST command and return the appropriate reply"""
    try:
        file_name = "uploads\\" + request[1].split("=")[1]
        with open(file_name, "wb") as f:
            f.write(body)
        headers = '\r\n'.join(request_headers) + '\r\n'
        start = headers.find("Content-Type: ") + len("Content-Type: ")
        end = [index for index in range(start, len(headers)) if headers.startswith("\r\n", index)][0]
        reply = PROTOCOL.encode() + b" 200 OK " + headers[start:end].encode() + b"\r\n"
        msg = b"Created"
        reply_headers = b"Content-Type: text/plain\r\n"
        return reply, reply_headers, msg

    except Exception as e:
        print("[handle_post] Error:", e)
        return PROTOCOL.encode() + b" 500 Internal Server Error\r\n", b'', b''


def handle_request(request, request_headers, body):
    """ generate proper HTTP response and return it """
    if request[0] == "GET":  # handle GET
        return handle_get(request)

    elif request[0] == "POST" and request[1].startswith("/upload?file-name="):  # handle POST
        return handle_post(request, request_headers, body)

    else:  # unrecognized command
        print("[handle_request] Error: unrecognized command")
        return PROTOCOL.encode() + b" 500 Internal Server Error\r\n", b'', b''
    

def handle_client(cli_sock, tid, addr):
    """ generate proper HTTP response and send to client """
    global exit_all
    print('new client arrive', tid, addr)
    try:
        while not exit_all:
            request, request_headers, body = http_recv(cli_sock)
            if request == b'' or not validate_request(request):
                break
            reply, reply_headers, body = handle_request(request, request_headers, body)
            if reply == b'':
                break
            if PROTOCOL == "HTTP/1.0":
                reply_headers += b"Connection': close\r\n"
            else:
                reply_headers += b"Connection: keep-alive\r\n"
            http_send(cli_sock, reply, reply_headers, body)
            if reply.decode() == PROTOCOL + " 302 Found\r\n":
                print("Found: closing client")
                break
            if PROTOCOL == "HTTP/1.0":
                break
    except Exception as e:
        print("[handle_client] Error:", e)

    print("Client", tid, "Closing")
    cli_sock.close()


def main():
    global exit_all
    # Open a socket and loop forever while waiting for clients
    server_socket = socket.socket()
    server_socket.bind(('0.0.0.0', PORT))
    server_socket.listen(5)
    threads = []
    tid = 1
    print(f"Listening for connections on port {PORT}")

    while True:
        client_socket, addr = server_socket.accept()
        t = threading.Thread(target=handle_client, args=(client_socket, tid, addr))
        t.start()
        threads.append(t)
        tid += 1
    exit_all = True

    for t in threads:
        t.join()

    server_socket.close()
    print('Server is shutting down.')


if __name__ == "__main__":
    # Call the main handler function
    main()
