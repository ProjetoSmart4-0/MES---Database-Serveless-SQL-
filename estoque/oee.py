'''Parte 7: OEE calculado a partir dos dados do Neon, sem simulações.'''
import os
from datetime import datetime, timezone
from psycopg2 import sql
from .db_connection import get_db_connection


def _coluna(cur, tabela, nome):
    cur.execute('''SELECT 1 FROM information_schema.columns
                   WHERE table_schema='public' AND table_name=%s AND column_name=%s''',
                (tabela, nome))
    if not cur.fetchone():
        raise ValueError(f"Coluna {tabela}.{nome} não existe. Confira o diagnóstico do Neon e o .env.")
    return sql.Identifier(nome)


def calcular_oee(inicio: datetime, fim: datetime, ppm: float | None = None):
    if inicio.tzinfo is None or fim.tzinfo is None or fim <= inicio:
        raise ValueError('Informe inicio e fim com fuso horário e fim maior que inicio.')
    if (fim - inicio).total_seconds() > 31 * 86400:
        raise ValueError('Período máximo: 31 dias.')
    ppm = ppm if ppm is not None else float(os.getenv('OEE_THEORETICAL_PPM', '0'))
    if ppm <= 0:
        raise ValueError('Configure OEE_THEORETICAL_PPM maior que zero.')
    time_name = os.getenv('OEE_TELEMETRY_TIME', 'recorded_at')
    state_name = os.getenv('OEE_TELEMETRY_STATE', 'machine_state')
    running = os.getenv('OEE_RUNNING_VALUE', 'RUNNING')
    machine_col = os.getenv('OEE_MACHINE_COLUMN', '')
    machine_value = os.getenv('OEE_MACHINE_VALUE', '')
    with get_db_connection() as conn, conn.cursor() as cur:
        t = _coluna(cur, 'telemetry_logs', time_name)
        s = _coluna(cur, 'telemetry_logs', state_name)
        filtro = sql.SQL('')
        params = [inicio, fim]
        if machine_col:
            m = _coluna(cur, 'telemetry_logs', machine_col)
            filtro = sql.SQL(' AND {}::text = %s').format(m)
            params.append(machine_value)
        # Cada estado vale até a próxima leitura; o último vale até o fim da janela.
        query = sql.SQL('''WITH anterior AS (
            SELECT {state}::text AS estado, {time} AS instante FROM telemetry_logs
            WHERE {time} < %s {filter} ORDER BY {time} DESC LIMIT 1
        ), janela AS (
            SELECT {state}::text AS estado, {time} AS instante FROM telemetry_logs
            WHERE {time} >= %s AND {time} < %s {filter}
        ), amostras AS (
            SELECT * FROM anterior UNION ALL SELECT * FROM janela
        ), periodos AS (
            SELECT estado, GREATEST(instante, %s::timestamptz) AS comeco,
                   LEAST(LEAD(instante, 1, %s::timestamptz) OVER (ORDER BY instante), %s::timestamptz) AS termino
            FROM amostras
        ) SELECT COALESCE(SUM(EXTRACT(EPOCH FROM termino-comeco))
                 FILTER (WHERE estado = %s AND termino > comeco),0) AS segundos_ativos,
                 COUNT(*) AS amostras FROM periodos''').format(state=s,time=t,filter=filtro)
        # O filtro de máquina aparece duas vezes na consulta.
        anterior_params = [inicio] + ([machine_value] if machine_col else [])
        janela_params = [inicio, fim] + ([machine_value] if machine_col else [])
        cur.execute(query, anterior_params + janela_params + [inicio, fim, fim, running])
        atividade = cur.fetchone()
        if not atividade['amostras']:
            raise ValueError('Sem telemetria para calcular disponibilidade no período.')
        ativos = float(atividade['segundos_ativos'])
        planejados = (fim-inicio).total_seconds()
        # Qualidade e total de peças: inspeções no período, sem contar peça duas vezes.
        _coluna(cur, 'pieces_traceability', 'inspected_at')
        _coluna(cur, 'pieces_traceability', 'status')
        cur.execute('''SELECT COUNT(*) AS total,
                   COUNT(*) FILTER (WHERE status::text IN ('INSPECTED_OK','EXPEDITED')) AS aprovadas
                   FROM pieces_traceability
                   WHERE inspected_at >= %s AND inspected_at < %s''', (inicio,fim))
        pecas = cur.fetchone()
        total = pecas['total']
        aprovadas = pecas['aprovadas']
        if not total:
            raise ValueError('Sem peças inspecionadas no período; qualidade e OEE indisponíveis.')
        if ativos <= 0:
            raise ValueError('Sem tempo de máquina em operação; OEE indisponível.')
        disponibilidade = min(1, ativos / planejados)
        desempenho = min(1, total / (ppm * ativos / 60))
        qualidade = aprovadas / total
        return {
            'inicio': inicio, 'fim': fim, 'ppm_teorico': ppm,
            'tempo_planejado_segundos': round(planejados,2),
            'tempo_operacao_segundos': round(ativos,2),
            'pecas_processadas': total, 'pecas_aprovadas': aprovadas,
            'disponibilidade_percentual': round(disponibilidade*100,2),
            'desempenho_percentual': round(desempenho*100,2),
            'qualidade_percentual': round(qualidade*100,2),
            'oee_percentual': round(disponibilidade*desempenho*qualidade*100,2),
            'observacao': 'Qualidade baseada em peças inspecionadas; valide se EXPEDITED mantém a aprovação.'
        }
