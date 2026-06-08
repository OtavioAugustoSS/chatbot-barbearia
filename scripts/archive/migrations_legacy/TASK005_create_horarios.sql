CREATE TABLE IF NOT EXISTS horarios (
    dia_semana INT PRIMARY KEY,
    abertura VARCHAR(5) NULL,
    fechamento VARCHAR(5) NULL,
    fechado BOOLEAN NOT NULL DEFAULT FALSE
);
