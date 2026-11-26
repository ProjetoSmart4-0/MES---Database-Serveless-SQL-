# Consulta apenas metadados: não altera nada no Neon.
from estoque.db_connection import get_db_connection

TABELAS = ['production_orders', 'pieces_traceability', 'piece_events',
        'inventory_stock', 'telemetry_logs', 'oee_metrics_hourly',
        'production_records', 'machine_downtime']
with get_db_connection() as conn, conn.cursor() as cur:
    for tabela in TABELAS:
        cur.execute("""SELECT column_name, data_type FROM information_schema.columns
                    WHERE table_schema='public' AND table_name=%s ORDER BY ordinal_position""", (tabela,))
        colunas = cur.fetchall()
        print(f"\n{tabela}: " + (', '.join(f"{c['column_name']} ({c['data_type']})" for c in colunas) if colunas else 'NÃO ENCONTRADA'))
