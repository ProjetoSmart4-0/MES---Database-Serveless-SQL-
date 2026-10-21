-- 1. Criação do tipo ENUM de status dos itens (se ainda não existir no script)
CREATE TYPE piece_status AS ENUM (
    'RAW_MATERIAL', 
    'IN_PROCESSING', 
    'INSPECTED_OK', 
    'INSPECTED_NOK', 
    'EXPEDITED'
);

-- 2. Tabela principal de estoque
CREATE TABLE IF NOT EXISTS inventory_stock (
    id SERIAL PRIMARY KEY,
    item_name VARCHAR(100) NOT NULL,
    category piece_status NOT NULL DEFAULT 'RAW_MATERIAL',
    quantity INT NOT NULL DEFAULT 0,
    reorder_point INT NOT NULL DEFAULT 10, -- Nível mínimo de alertas
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 3. Carga Inicial de Dados (Seeds para testes na Sprint 1)
INSERT INTO inventory_stock (item_name, category, quantity, reorder_point) VALUES
('Bloco Bruto', 'RAW_MATERIAL', 50, 10),
('Tampa Plástica', 'RAW_MATERIAL', 50, 10),
('Caixa Expedição', 'EXPEDITED', 0, 5)
ON CONFLICT DO NOTHING;