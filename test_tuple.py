import sqlite3
from flask import Flask
from ajsystem.core.extensions import db

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite://'
db.init_app(app)

class T(db.Model):
    __tablename__ = 't7'
    id = db.Column(db.Integer, primary_key=True)
    tipo = db.Column(db.String)
    valor = db.Column(db.Numeric(12,2))

with app.app_context():
    db.create_all()
    db.session.add_all([T(tipo='A', valor=10), T(tipo='A', valor=20), T(tipo='B', valor=30)])
    db.session.commit()
    
    from ajsystem.defs.data import register_model
    register_model('T', T)
    
    Q = {'select': ['tipo','valor'], 'from': 'T'}
    
    from ajsystem.core.do_report import _auto_data
    
    # Test 1: Tuple with order only
    report1 = {
        'label': 'Test1',
        'body': {
            'source': (Q, {'order': [2, 1]}),
            'table': {}
        }
    }
    try:
        rows1 = _auto_data(report1, None, None)
        print(f'Test1 (order only): {len(rows1)} rows')
        for r in rows1[:1]:
            print(f'  tipo={r.tipo}, valor={r.valor}')
    except Exception as e:
        print(f'Test1 error: {type(e).__name__}: {e}')
    
    # Test 2: Tuple with filter only
    report2 = {
        'label': 'Test2',
        'body': {
            'source': (Q, {'filter': {'tipo': 'A'}}),
            'table': {}
        }
    }
    try:
        rows2 = _auto_data(report2, None, None)
        print(f'Test2 (filter only): {len(rows2)} rows')
        for r in rows2:
            print(f'  tipo={r.tipo}, valor={r.valor}')
    except Exception as e:
        print(f'Test2 error: {type(e).__name__}: {e}')
    
    # Test 3: Tuple with both order and filter
    report3 = {
        'label': 'Test3',
        'body': {
            'source': (Q, {'order': [2, 1], 'filter': {'tipo': 'A'}}),
            'table': {}
        }
    }
    try:
        rows3 = _auto_data(report3, None, None)
        print(f'Test3 (both): {len(rows3)} rows')
        for r in rows3:
            print(f'  tipo={r.tipo}, valor={r.valor}')
    except Exception as e:
        print(f'Test3 error: {type(e).__name__}: {e}')
    
    # Test 4: Normal dict source (não-tupla)
    report4 = {
        'label': 'Test4',
        'body': {
            'source': Q,
            'table': {}
        }
    }
    try:
        rows4 = _auto_data(report4, None, None)
        print(f'Test4 (normal dict): {len(rows4)} rows')
        for r in rows4:
            print(f'  tipo={r.tipo}, valor={r.valor}')
    except Exception as e:
        print(f'Test4 error: {type(e).__name__}: {e}')
    
    print('\n=== Todos os testes concluídos ===')
