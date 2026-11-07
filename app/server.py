"""Controladores HTTP REST e entrega do frontend; somente biblioteca padrao Python."""
import json
import mimetypes
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from . import service
from .db import initialize

WEB=Path(__file__).resolve().parents[1]/'web'
ROUTES = {
 ('GET','/api/departments'): service.all_departments,
 ('POST','/api/departments'): service.department_create,
 ('GET','/api/service-points'): service.all_points,
 ('POST','/api/service-points'): service.point_create,
 ('GET','/api/tickets'): service.tickets_list,
 ('POST','/api/tickets'): service.ticket_create,
 ('GET','/api/dashboard'): service.dashboard,
 ('GET','/api/health'): lambda: {'status':'ok'},
}
SINGLES = [
 (re.compile(r'^/api/departments/(\d+)$'),{'PUT':service.department_update,'DELETE':service.department_delete}),
 (re.compile(r'^/api/service-points/(\d+)$'),{'PUT':service.point_update,'DELETE':service.point_delete}),
 (re.compile(r'^/api/tickets/(\d+)$'),{'GET':service.ticket_get,'PUT':service.ticket_update,'DELETE':service.ticket_delete}),
 (re.compile(r'^/api/tickets/(\d+)/status$'),{'PATCH':service.ticket_transition}),
 (re.compile(r'^/api/tickets/(\d+)/events$'),{'GET':service.ticket_events}),
]
class Handler(BaseHTTPRequestHandler):
    def do_GET(self): self.handle_request('GET')
    def do_HEAD(self): self.handle_request('HEAD')
    def do_POST(self): self.handle_request('POST')
    def do_PUT(self): self.handle_request('PUT')
    def do_PATCH(self): self.handle_request('PATCH')
    def do_DELETE(self): self.handle_request('DELETE')
    def respond(self,status,data):
        blob=json.dumps(data,ensure_ascii=False).encode('utf-8')
        self.send_response(status);self.send_header('Content-Type','application/json; charset=utf-8')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Cache-Control','no-store')
        self.send_header('Content-Length',str(len(blob)));self.end_headers()
        if self.command != 'HEAD': self.wfile.write(blob)
    def body(self):
        try: length=int(self.headers.get('Content-Length','0'))
        except ValueError: raise service.AppError('Content-Length invalido')
        if length>65536: raise service.AppError('Requisicao muito grande',413)
        try: payload=json.loads(self.rfile.read(length).decode('utf-8'))
        except (json.JSONDecodeError,UnicodeDecodeError): raise service.AppError('JSON invalido')
        if not isinstance(payload,dict): raise service.AppError('O corpo deve ser um objeto JSON')
        return payload
    def handle_request(self,method):
        path=urlparse(self.path).path
        if method == 'HEAD':
            if path == '/api/health': return self.respond(200, {'status':'ok'})
            if path == '/': return self.static('/')
            return self.respond(404, {'error':'Rota inexistente'})
        if not path.startswith('/api/'):
            if method=='GET': return self.static(path)
            return self.respond(405,{'error':'Metodo nao permitido'})
        try:
            func=ROUTES.get((method,path))
            if func:
                if method=='GET':
                    value=func({k:v[0] for k,v in parse_qs(urlparse(self.path).query).items()}) if path=='/api/tickets' else func()
                else: value=func(self.body())
                return self.respond(201 if method=='POST' else 200,value)
            for regex,methods in SINGLES:
                match=regex.fullmatch(path)
                if match:
                    if method not in methods: return self.respond(405,{'error':'Metodo nao permitido'})
                    value=methods[method](match.group(1),self.body()) if method in ('PUT','PATCH') else methods[method](match.group(1))
                    return self.respond(200,value)
            return self.respond(404,{'error':'Rota inexistente'})
        except service.AppError as err: return self.respond(err.status,{'error':str(err)})
        except Exception:
            self.log_error('Erro interno ao processar %s %s',method,path)
            return self.respond(500,{'error':'Erro interno do servidor'})
    def static(self,path):
        lookup={'/':'index.html','/index.html':'index.html','/app.js':'app.js','/style.css':'style.css'}
        filename=lookup.get(path)
        if not filename: return self.respond(404,{'error':'Arquivo nao encontrado'})
        blob=(WEB/filename).read_bytes()
        self.send_response(200);self.send_header('Content-Type',mimetypes.guess_type(filename)[0] or 'text/plain')
        self.send_header('Content-Length',str(len(blob)));self.send_header('X-Content-Type-Options','nosniff')
        self.end_headers()
        if self.command != 'HEAD': self.wfile.write(blob)

def run(host='127.0.0.1',port=8000):
    initialize()
    httpd=ThreadingHTTPServer((host,port),Handler)
    print(f'Sistema disponivel em http://{host}:{port}',flush=True)
    try: httpd.serve_forever()
    finally: httpd.server_close()

if __name__=='__main__': run()
