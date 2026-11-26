BEGIN;
-- SMART 4.0 / Grupo 3. Execute uma vez no Neon após backup.
CREATE SEQUENCE IF NOT EXISTS mes_order_number_seq START 1;
SELECT setval('mes_order_number_seq', COALESCE((
SELECT MAX(NULLIF(regexp_replace(order_number, '^.*-', ''), '')::BIGINT)
FROM production_orders WHERE order_number ~ '^OP-[0-9]{8}-[0-9]+$'
), 0) + 1, false);
ALTER TABLE production_orders ADD COLUMN IF NOT EXISTS block_type VARCHAR(10), ADD COLUMN IF NOT EXISTS base_color VARCHAR(10), ADD COLUMN IF NOT EXISTS lid_color VARCHAR(10);
UPDATE production_orders SET block_type=COALESCE(block_type, CASE target_quantity WHEN 1 THEN 'UNICO' WHEN 2 THEN 'DUPLO' WHEN 3 THEN 'TRIPLO' ELSE 'LEGADO' END), base_color=COALESCE(base_color,'PRETA'), lid_color=COALESCE(lid_color,'PRETA') WHERE block_type IS NULL OR base_color IS NULL OR lid_color IS NULL;
ALTER TABLE production_orders ALTER COLUMN block_type SET NOT NULL, ALTER COLUMN base_color SET NOT NULL, ALTER COLUMN lid_color SET NOT NULL;
DO $$ BEGIN
IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='production_orders_block_type_check') THEN ALTER TABLE production_orders ADD CONSTRAINT production_orders_block_type_check CHECK (block_type IN ('UNICO','DUPLO','TRIPLO','LEGADO')); END IF;
IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='production_orders_base_color_check') THEN ALTER TABLE production_orders ADD CONSTRAINT production_orders_base_color_check CHECK (base_color IN ('PRETA','VERMELHA')); END IF;
IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='production_orders_lid_matches_base_check') THEN ALTER TABLE production_orders ADD CONSTRAINT production_orders_lid_matches_base_check CHECK (lid_color=base_color); END IF;
END $$;
CREATE TABLE IF NOT EXISTS order_boxes (
id BIGSERIAL PRIMARY KEY,
production_order_id INTEGER NOT NULL REFERENCES production_orders(id) ON DELETE CASCADE,
box_number SMALLINT NOT NULL CHECK (box_number BETWEEN 1 AND 3),
plaque_color_1 VARCHAR(10) NOT NULL CHECK (plaque_color_1 IN ('PRETA','VERMELHA','BRANCA','AMARELA','VERDE','AZUL')),
plaque_color_2 VARCHAR(10) NOT NULL CHECK (plaque_color_2 IN ('PRETA','VERMELHA','BRANCA','AMARELA','VERDE','AZUL')),
plaque_color_3 VARCHAR(10) NOT NULL CHECK (plaque_color_3 IN ('PRETA','VERMELHA','BRANCA','AMARELA','VERDE','AZUL')),
UNIQUE (production_order_id,box_number)
);
ALTER TABLE pieces_traceability ADD COLUMN IF NOT EXISTS order_box_id BIGINT;
DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='pieces_traceability_order_box_fk') THEN ALTER TABLE pieces_traceability ADD CONSTRAINT pieces_traceability_order_box_fk FOREIGN KEY (order_box_id) REFERENCES order_boxes(id); END IF; END $$;
CREATE UNIQUE INDEX IF NOT EXISTS pieces_traceability_order_box_unique ON pieces_traceability(order_box_id) WHERE order_box_id IS NOT NULL;
-- Capacidade fixa (não debitada): bases 6 por cor; tampas 6 por cor; plaquinhas 10 por cor.

COMMIT;
