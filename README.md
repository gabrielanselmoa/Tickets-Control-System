# Sistema de Controle de Tickets — PIT II

Projeto acadêmico funcional web em Python + SQLite + HTML/CSS/JS, sem dependências pip.

## Instalação

```bash
python main.py
```

Abra **http://127.0.0.1:8000**. No Windows também é possível usar `py main.py`.

## Testes

```bash
python -m unittest discover -s tests -v
```

## Recursos

- CRUD completo de tickets com código exclusivo gerado automaticamente
- CRUD de departamentos e guichês
- Validação de status WAITING, CALLED, IN_SERVICE, FINISHED, CANCELLED
- Histórico de mudanças de estado
- Pesquisa por código/cliente e filtro por status
- Painel de indicadores, interface responsiva, erros HTTP tratados

## Estrutura

- `app/db.py`: projeto físico SQLite, chaves, índices e dados iniciais
- `app/service.py`: regras de negócio e operações CRUD
- `app/server.py`: controladores da API REST e servidor estático
- `web/`: telas de usuário em HTML/CSS/JS
- `tests/`: testes automatizados
- `docs/`: documentação, diagramas, instalação, orientações e templates
