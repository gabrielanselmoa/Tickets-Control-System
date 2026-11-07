"""Testes automatizados com unittest (stdlib)."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app import db, service

class TicketTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.patcher=patch.object(db,'DB_PATH',Path(self.tmp.name)/'test.sqlite3')
        self.patcher.start();db.initialize()
        self.dept=service.all_departments()[0]['id']
        self.point=service.all_points()[0]['id']
    def tearDown(self): self.patcher.stop();self.tmp.cleanup()
    def create(self): return service.ticket_create({'customer_name':'Cliente Teste','department_id':self.dept})
    def test_create_and_list(self):
        t=self.create();self.assertTrue(t['code']);self.assertEqual(t['status'],'WAITING')
        self.assertEqual(len(service.tickets_list()),1)
    def test_update_and_read(self):
        t=self.create();updated=service.ticket_update(t['id'],{'customer_name':'Novo Cliente'})
        self.assertEqual(updated['customer_name'],'Novo Cliente');self.assertEqual(service.ticket_get(t['id'])['customer_name'],'Novo Cliente')
    def test_delete(self):
        t=self.create();service.ticket_delete(t['id'])
        with self.assertRaises(service.AppError):service.ticket_get(t['id'])
    def test_invalid_transition(self):
        t=self.create()
        with self.assertRaises(service.AppError):service.ticket_transition(t['id'],{'status':'FINISHED'})
    def test_full_lifecycle_and_history(self):
        t=self.create()
        for status in ['CALLED','IN_SERVICE','FINISHED']:
            t=service.ticket_transition(t['id'],{'status':status,'service_point_id':self.point})
        self.assertEqual(t['status'],'FINISHED');self.assertEqual(len(service.ticket_events(t['id'])),4)
    def test_department_fk(self):
        with self.assertRaises(service.AppError):service.ticket_create({'customer_name':'Ana','department_id':99999})
    def test_unique_code(self):
        self.assertNotEqual(self.create()['code'],self.create()['code'])
    def test_department_crud(self):
        d=service.department_create({'name':'Recepcao','prefix':'RC'})
        self.assertEqual(service.department_update(d['id'],{'name':'Recepcao B','prefix':'RB'})['prefix'],'RB')
        self.assertTrue(service.department_delete(d['id'])['deleted'])
    def test_point_crud(self):
        p=service.point_create({'name':'Guiche 7'})
        self.assertEqual(service.point_update(p['id'],{'name':'Guiche 8'})['name'],'Guiche 8')
        self.assertTrue(service.point_delete(p['id'])['deleted'])
    def test_search_treats_percent_as_literal(self):
        self.create()
        self.assertEqual(service.tickets_list({'search':'%'}), [])

    def test_search_treats_underscore_as_literal(self):
        self.create()
        self.assertEqual(service.tickets_list({'search':'_'}), [])

    def test_filter_by_department(self):
        ticket = self.create()
        other = service.department_create({'name':'Outro','prefix':'OU'})
        self.assertEqual(len(service.tickets_list({'department_id':str(self.dept)})), 1)
        self.assertEqual(service.tickets_list({'department_id':str(other['id'])}), [])
        self.assertEqual(service.tickets_list({'department_id':str(self.dept)})[0]['id'], ticket['id'])

    def test_no_sql_injection(self):
        t=service.ticket_create({'customer_name':"X'); DROP TABLE tickets; --",'department_id':self.dept})
        self.assertIsNotNone(service.ticket_get(t['id']))
if __name__=='__main__': unittest.main()
