def list_table(valores: dict):
    from sqlalchemy import select, union_all, literal
    ctes = [
        select(literal(k).label('codigo'), literal(v).label('descricao'))
        for k, v in valores.items()
    ]
    return union_all(*ctes).cte('list_table')
