import sys

path = '/var/www/http/CampusDyIP'
if path not in sys.path:
    sys.path.append(path)
import PServer, os

def application(environ, start_response):
    server = PServer.pserver(os.path.join('.','gpu_server_database.db'))
    return server(environ, start_response)


if __name__=='__main__':
    print('start debug...')
    from wsgiref.simple_server import make_server
    httpd = make_server('', 8080, application)
    print('Serving on port 8080...')
    httpd.serve_forever()