import argparse
from app.server import run

if __name__=='__main__':
    parser=argparse.ArgumentParser(description='Servidor do sistema de tickets')
    parser.add_argument('--host',default='0.0.0.0')
    parser.add_argument('--port',type=int,default=8000)
    args=parser.parse_args()
    run(args.host,args.port)
