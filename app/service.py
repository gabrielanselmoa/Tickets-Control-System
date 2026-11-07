"""Regras de negocio. SQL parametrizado e validacoes do CRUD."""
import secrets
import sqlite3
from .db import connect

STATUSES = ('WAITING','CALLED','IN_SERVICE','FINISHED','CANCELLED')
NEXT = {'WAITING': {'CALLED','CANCELLED'}, 'CALLED': {'IN_SERVICE','WAITING','CANCELLED'},
        'IN_SERVICE': {'FINISHED','CANCELLED'}, 'FINISHED': set(), 'CANCELLED': set()}

class AppError(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status

def clean(value, field, maximum=100, required=True):
    if not isinstance(value, str): raise AppError(f'{field} deve ser texto')
    value = value.strip()
    if (required and not value) or len(value)>maximum: raise AppError(f'{field} invalido (maximo {maximum} caracteres)')
    return value

def number(value, field):
    if isinstance(value, bool): raise AppError(f'{field} invalido')
    try: result=int(value)
    except (TypeError,ValueError): raise AppError(f'{field} invalido')
    if result<=0: raise AppError(f'{field} invalido')
    return result

def all_departments():
    with connect() as db: return [dict(r) for r in db.execute('SELECT * FROM departments ORDER BY name')]

def all_points():
    with connect() as db: return [dict(r) for r in db.execute('SELECT * FROM service_points ORDER BY name')]

def department_create(data):
    name=clean(data.get('name'), 'Nome'); prefix=clean(data.get('prefix'), 'Prefixo',4).upper()
    try:
        with connect() as db:
            cur=db.execute('INSERT INTO departments(name,prefix) VALUES (?,?)',(name,prefix))
            return dict(db.execute('SELECT * FROM departments WHERE id=?',(cur.lastrowid,)).fetchone())
    except sqlite3.IntegrityError: raise AppError('Nome ou prefixo de departamento ja cadastrado',409)

def department_update(id,data):
    id=number(id,'ID'); name=clean(data.get('name'),'Nome'); prefix=clean(data.get('prefix'),'Prefixo',4).upper()
    try:
        with connect() as db:
            cur=db.execute('UPDATE departments SET name=?,prefix=? WHERE id=?',(name,prefix,id))
            if not cur.rowcount: raise AppError('Departamento nao encontrado',404)
            return dict(db.execute('SELECT * FROM departments WHERE id=?',(id,)).fetchone())
    except sqlite3.IntegrityError: raise AppError('Nome ou prefixo duplicado',409)

def department_delete(id):
    try:
        with connect() as db:
            cur=db.execute('DELETE FROM departments WHERE id=?',(number(id,'ID'),))
            if not cur.rowcount: raise AppError('Departamento nao encontrado',404)
    except sqlite3.IntegrityError: raise AppError('Departamento possui tickets vinculados',409)
    return {'deleted':True}

def point_create(data):
    name=clean(data.get('name'),'Nome')
    try:
        with connect() as db:
            cur=db.execute('INSERT INTO service_points(name) VALUES (?)',(name,))
            return dict(db.execute('SELECT * FROM service_points WHERE id=?',(cur.lastrowid,)).fetchone())
    except sqlite3.IntegrityError: raise AppError('Guiche ja cadastrado',409)

def point_update(id,data):
    name=clean(data.get('name'),'Nome'); id=number(id,'ID')
    try:
        with connect() as db:
            cur=db.execute('UPDATE service_points SET name=? WHERE id=?',(name,id))
            if not cur.rowcount: raise AppError('Guiche nao encontrado',404)
            return dict(db.execute('SELECT * FROM service_points WHERE id=?',(id,)).fetchone())
    except sqlite3.IntegrityError: raise AppError('Guiche ja cadastrado',409)

def point_delete(id):
    with connect() as db:
        cur=db.execute('DELETE FROM service_points WHERE id=?',(number(id,'ID'),))
        if not cur.rowcount: raise AppError('Guiche nao encontrado',404)
    return {'deleted':True}

def ticket_get(id):
    with connect() as db:
        row=db.execute('''SELECT t.*,d.name AS department_name,p.name AS service_point_name FROM tickets t
          JOIN departments d ON d.id=t.department_id LEFT JOIN service_points p ON p.id=t.service_point_id WHERE t.id=?''',(number(id,'ID'),)).fetchone()
        if not row: raise AppError('Ticket nao encontrado',404)
        return dict(row)

def tickets_list(query=None):
    query=query or {}; where=[]; params=[]
    if query.get('status'):
        if query['status'] not in STATUSES: raise AppError('Status invalido')
        where.append('t.status=?');params.append(query['status'])
    if query.get('department_id'):
        where.append('t.department_id=?');params.append(number(query['department_id'],'Departamento'))
    if query.get('search'):
        where.append('(t.code LIKE ? OR t.customer_name LIKE ?)')
        term='%'+str(query['search'])[:100]+'%';params.extend([term,term])
    clause=' WHERE '+' AND '.join(where) if where else ''
    with connect() as db:
        rows=db.execute('''SELECT t.*,d.name AS department_name,p.name AS service_point_name FROM tickets t
          JOIN departments d ON d.id=t.department_id LEFT JOIN service_points p ON p.id=t.service_point_id'''+clause+
          ' ORDER BY t.created_at DESC,t.id DESC LIMIT 500',params).fetchall()
        return [dict(row) for row in rows]

def check_department(db,id):
    row=db.execute('SELECT id,prefix FROM departments WHERE id=? AND active=1',(id,)).fetchone()
    if not row: raise AppError('Departamento inexistente ou inativo',404)
    return row

def check_point(db,id):
    if id is None or id=='': return None
    id=number(id,'Guiche')
    if not db.execute('SELECT 1 FROM service_points WHERE id=? AND active=1',(id,)).fetchone():
        raise AppError('Guiche inexistente ou inativo',404)
    return id

def ticket_create(data):
    name=clean(data.get('customer_name'),'Cliente')
    description=clean(data.get('description',''),'Descricao',500,False)
    priority=data.get('priority','NORMAL')
    if priority not in ('NORMAL','PREFERENCIAL'): raise AppError('Prioridade invalida')
    department_id=number(data.get('department_id'),'Departamento')
    with connect() as db:
        dept=check_department(db,department_id)
        point=check_point(db,data.get('service_point_id'))
        for _ in range(8):
            code=f"{dept['prefix']}-{secrets.token_hex(4).upper()}"
            try:
                cur=db.execute('''INSERT INTO tickets(code,department_id,service_point_id,customer_name,description,priority)
                   VALUES (?,?,?,?,?,?)''',(code,department_id,point,name,description,priority))
                db.execute('INSERT INTO ticket_events(ticket_id,new_status,note) VALUES (?,?,?)',(cur.lastrowid,'WAITING','Criado'))
                break
            except sqlite3.IntegrityError as err:
                if 'tickets.code' not in str(err): raise
        else: raise AppError('Nao foi possivel gerar codigo unico',500)
        id=cur.lastrowid
    return ticket_get(id)

def ticket_update(id,data):
    id=number(id,'ID')
    with connect() as db:
        old=db.execute('SELECT * FROM tickets WHERE id=?',(id,)).fetchone()
        if not old: raise AppError('Ticket nao encontrado',404)
        if old['status'] in ('FINISHED','CANCELLED'): raise AppError('Ticket encerrado nao pode ser editado',409)
        name=clean(data.get('customer_name',old['customer_name']),'Cliente')
        description=clean(data.get('description',old['description']),'Descricao',500,False)
        priority=data.get('priority',old['priority'])
        if priority not in ('NORMAL','PREFERENCIAL'): raise AppError('Prioridade invalida')
        dept_id=number(data.get('department_id',old['department_id']),'Departamento')
        check_department(db,dept_id)
        point=check_point(db,data.get('service_point_id',old['service_point_id']))
        db.execute('''UPDATE tickets SET customer_name=?,description=?,priority=?,department_id=?,service_point_id=?,updated_at=datetime('now') WHERE id=?''',
           (name,description,priority,dept_id,point,id))
    return ticket_get(id)

def ticket_delete(id):
    with connect() as db:
        cur=db.execute('DELETE FROM tickets WHERE id=?',(number(id,'ID'),))
        if not cur.rowcount: raise AppError('Ticket nao encontrado',404)
    return {'deleted':True}

def ticket_transition(id,data):
    id=number(id,'ID'); target=data.get('status')
    if target not in STATUSES: raise AppError('Status invalido')
    with connect() as db:
        row=db.execute('SELECT status,service_point_id FROM tickets WHERE id=?',(id,)).fetchone()
        if not row: raise AppError('Ticket nao encontrado',404)
        if target not in NEXT[row['status']]: raise AppError('Transicao de status nao permitida',409)
        point=check_point(db,data.get('service_point_id',row['service_point_id']))
        if target in ('CALLED','IN_SERVICE') and not point: raise AppError('Informe o guiche para chamar/iniciar',400)
        db.execute("UPDATE tickets SET status=?,service_point_id=?,updated_at=datetime('now') WHERE id=?",(target,point,id))
        db.execute('INSERT INTO ticket_events(ticket_id,old_status,new_status,note) VALUES (?,?,?,?)',
           (id,row['status'],target,clean(data.get('note',''),'Observacao',200,False)))
    return ticket_get(id)

def ticket_events(id):
    ticket_get(id)
    with connect() as db: return [dict(r) for r in db.execute('SELECT * FROM ticket_events WHERE ticket_id=? ORDER BY id',(number(id,'ID'),))]

def dashboard():
    with connect() as db:
        return {r['status']:r['total'] for r in db.execute('SELECT status,COUNT(*) total FROM tickets GROUP BY status')}
