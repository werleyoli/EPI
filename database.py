import sqlite3
import os
import sys
import hashlib
from datetime import datetime

if getattr(sys, 'frozen', False):
    APP_DIR = os.path.dirname(sys.executable)
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))

DB_FILE = os.path.join(APP_DIR, "data", "epi_control.db")
EXPORTS_DIR = os.path.join(APP_DIR, "exports")
SIGNATURES_DIR = os.path.join(APP_DIR, "data", "signatures")

def hash_password(password: str) -> str:
    """Gera hash SHA-256 da senha."""
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def get_connection():
    """Retorna uma conexão com o banco de dados SQLite com row_factory ativado."""
    os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)
    os.makedirs(SIGNATURES_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db():
    """Inicializa as tabelas do banco de dados e executa migrações automáticas."""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # 1. Tabela de EPIs
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS epis (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                codigo TEXT UNIQUE NOT NULL,
                nome TEXT NOT NULL,
                ca TEXT NOT NULL,
                validade_ca TEXT,
                fabricante TEXT,
                tamanho TEXT,
                unidade TEXT DEFAULT 'UN',
                quantidade INTEGER NOT NULL DEFAULT 0,
                estoque_minimo INTEGER NOT NULL DEFAULT 5,
                preco_unitario REAL DEFAULT 0.0,
                preco_usado REAL DEFAULT 0.0,
                dias_vida_util INTEGER DEFAULT 0, -- 0 = sem validade específica de uso
                localizacao TEXT,
                descricao TEXT,
                ativo INTEGER DEFAULT 1,
                created_at TEXT NOT NULL
            );
        """)

        # 2. Tabela de Funcionários
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS funcionarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                matricula TEXT UNIQUE NOT NULL,
                nome TEXT NOT NULL,
                cpf TEXT,
                cargo TEXT NOT NULL,
                departamento TEXT NOT NULL,
                data_admissao TEXT,
                status TEXT DEFAULT 'Ativo',
                pin_seguranca TEXT DEFAULT '1234',
                observacoes TEXT,
                created_at TEXT NOT NULL
            );
        """)

        # 3. Tabela de Usuários do Sistema (Login & Permissões)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS usuarios_sistema (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                nome TEXT NOT NULL,
                cargo TEXT,
                perfil TEXT NOT NULL, -- 'ADMIN', 'ALMOXARIFE', 'CONSULTA'
                ativo INTEGER DEFAULT 1,
                created_at TEXT NOT NULL
            );
        """)

        # 4. Tabela de Operadores de Entrega (Almoxarifado)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS operadores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT UNIQUE NOT NULL,
                cargo TEXT,
                ativo INTEGER DEFAULT 1
            );
        """)

        # 5. Tabela de Matriz de EPIs por Cargo (Kit Admissional e Obrigatórios)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS matriz_cargos_epis (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cargo TEXT NOT NULL,
                epi_id INTEGER NOT NULL,
                quantidade INTEGER NOT NULL DEFAULT 1,
                obrigatorio INTEGER DEFAULT 1,
                periodicidade_dias INTEGER DEFAULT 90,
                FOREIGN KEY (epi_id) REFERENCES epis(id) ON DELETE CASCADE,
                UNIQUE(cargo, epi_id)
            );
        """)

        # 6. Tabela de Movimentações (Saídas, Entradas, Devoluções, Descartes)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS movimentacoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tipo TEXT NOT NULL, -- 'SAIDA', 'ENTRADA', 'DEVOLUCAO', 'DESCARTE'
                epi_id INTEGER NOT NULL,
                funcionario_id INTEGER,
                quantidade INTEGER NOT NULL,
                custo_unitario REAL DEFAULT 0.0,
                custo_total REAL DEFAULT 0.0,
                data_hora TEXT NOT NULL,
                responsavel_entrega TEXT NOT NULL,
                motivo TEXT NOT NULL,
                assinatura_path TEXT, -- Caminho do PNG com a assinatura desenhada na tela
                observacao TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (epi_id) REFERENCES epis(id) ON DELETE RESTRICT,
                FOREIGN KEY (funcionario_id) REFERENCES funcionarios(id) ON DELETE RESTRICT
            );
        """)

        # 7. Tabela de Configurações da Empresa
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS configuracoes (
                chave TEXT PRIMARY KEY,
                valor TEXT
            );
        """)

        # 8. Tabela de Logs de Auditoria
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS logs_auditoria (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_nome TEXT NOT NULL,
                acao TEXT NOT NULL,
                modulo TEXT NOT NULL,
                detalhes TEXT,
                data_hora TEXT NOT NULL
            );
        """)

        # 9. Tabela de Inspeções e Manutenção Periódica de EPIs Duráveis (NR-35 / NR-33)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS inspecoes_epi (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                epi_id INTEGER NOT NULL,
                numero_serie TEXT,
                data_inspecao TEXT NOT NULL,
                data_proxima_inspecao TEXT NOT NULL,
                responsavel_tecnico TEXT NOT NULL,
                resultado TEXT NOT NULL, -- 'APROVADO', 'REPROVADO', 'MANUTENCAO'
                observacoes TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (epi_id) REFERENCES epis(id) ON DELETE CASCADE
            );
        """)

        # 10. Tabela de Orçamento por Departamento / Centro de Custo
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS orcamento_departamentos (
                departamento TEXT PRIMARY KEY,
                limite_mensal REAL DEFAULT 5000.0,
                created_at TEXT NOT NULL
            );
        """)

        # 11. Tabela de Fornecedores de EPIs
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS fornecedores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                razao_social TEXT NOT NULL,
                cnpj TEXT,
                contato TEXT,
                email TEXT,
                telefone TEXT,
                cidade_uf TEXT,
                ativo INTEGER DEFAULT 1,
                created_at TEXT NOT NULL
            );
        """)

        # 12. Tabela de Grupos / Famílias de EPIs
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS grupos_epi (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT UNIQUE NOT NULL,
                descricao TEXT,
                created_at TEXT NOT NULL
            );
        """)

        # 13. Tabela de Grades de Tamanho e Estados de Conservação dos EPIs
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS epi_grades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                epi_id INTEGER NOT NULL,
                tamanho TEXT NOT NULL,
                estado TEXT NOT NULL DEFAULT 'NOVO', -- 'NOVO', 'BOM', 'RUIM', 'DESCARTE'
                quantidade INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                FOREIGN KEY (epi_id) REFERENCES epis(id) ON DELETE CASCADE,
                UNIQUE(epi_id, tamanho, estado)
            );
        """)

        # 14. Tabela de Departamentos / Setores da Empresa
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS departamentos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT UNIQUE NOT NULL,
                descricao TEXT,
                created_at TEXT NOT NULL
            );
        """)

        # Índices
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_mov_epi ON movimentacoes(epi_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_mov_func ON movimentacoes(funcionario_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_mov_data ON movimentacoes(data_hora);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_epis_codigo ON epis(codigo);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_matriz_cargo ON matriz_cargos_epis(cargo);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_logs_data ON logs_auditoria(data_hora);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_inspecoes_epi ON inspecoes_epi(epi_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_epi_grades_epi ON epi_grades(epi_id);")

        # ------------------ MIGRAÇÕES DINÂMICAS ------------------
        # Caso o banco já exista com schema antigo, adiciona as novas colunas
        def add_column_if_not_exists(table, col, col_def):
            cursor.execute(f"PRAGMA table_info({table});")
            cols = [r[1] for r in cursor.fetchall()]
            if col not in cols:
                cursor.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_def};")

        add_column_if_not_exists("epis", "preco_unitario", "REAL DEFAULT 0.0")
        add_column_if_not_exists("epis", "preco_usado", "REAL DEFAULT 0.0")
        add_column_if_not_exists("epis", "dias_vida_util", "INTEGER DEFAULT 90")
        add_column_if_not_exists("epis", "is_duravel", "INTEGER DEFAULT 0")
        add_column_if_not_exists("epis", "grupo", "TEXT DEFAULT 'DIVERSOS / OUTROS'")
        add_column_if_not_exists("epis", "localizacao_secundaria", "TEXT DEFAULT ''")
        add_column_if_not_exists("epis", "qtd_novos", "INTEGER DEFAULT 0")
        add_column_if_not_exists("epis", "qtd_usados_bons", "INTEGER DEFAULT 0")
        add_column_if_not_exists("epis", "qtd_ruins", "INTEGER DEFAULT 0")
        add_column_if_not_exists("epis", "qtd_descarte", "INTEGER DEFAULT 0")
        add_column_if_not_exists("epis", "grade_resumo", "TEXT DEFAULT ''")
        add_column_if_not_exists("funcionarios", "pin_seguranca", "TEXT DEFAULT '1234'")
        add_column_if_not_exists("funcionarios", "telefone", "TEXT DEFAULT ''")
        add_column_if_not_exists("funcionarios", "tamanho_calcado", "TEXT DEFAULT '-'")
        add_column_if_not_exists("funcionarios", "tamanho_luva", "TEXT DEFAULT '-'")
        add_column_if_not_exists("funcionarios", "tamanho_uniforme", "TEXT DEFAULT '-'")
        add_column_if_not_exists("funcionarios", "tamanho_mascara", "TEXT DEFAULT '-'")
        add_column_if_not_exists("movimentacoes", "custo_unitario", "REAL DEFAULT 0.0")
        add_column_if_not_exists("movimentacoes", "custo_total", "REAL DEFAULT 0.0")
        add_column_if_not_exists("movimentacoes", "assinatura_path", "TEXT")
        add_column_if_not_exists("movimentacoes", "foto_path", "TEXT")
        add_column_if_not_exists("movimentacoes", "estado_conservacao", "TEXT DEFAULT 'NOVO'")
        add_column_if_not_exists("movimentacoes", "tamanho", "TEXT DEFAULT 'Único'")

        # Migração inicial para popular epi_grades a partir dos dados existentes
        now_dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("SELECT id, tamanho, quantidade FROM epis;")
        for ep_row in cursor.fetchall():
            eid, e_tam, e_qtd = ep_row[0], ep_row[1] or "Único", ep_row[2] or 0
            cursor.execute("SELECT COUNT(*) FROM epi_grades WHERE epi_id = ?;", (eid,))
            if cursor.fetchone()[0] == 0:
                cursor.execute("""
                    INSERT OR IGNORE INTO epi_grades (epi_id, tamanho, estado, quantidade, created_at)
                    VALUES (?, ?, 'NOVO', ?, ?);
                """, (eid, str(e_tam).strip() or "Único", e_qtd, now_dt))
                cursor.execute("""
                    UPDATE epis SET qtd_novos = ?, qtd_usados_bons = 0, qtd_ruins = 0, qtd_descarte = 0
                    WHERE id = ?;
                """, (e_qtd, eid))

        # Higienização de registros históricos de movimentações:
        try:
            cursor.execute("""
                SELECT m.id, m.tamanho, e.nome, f.tamanho_calcado, f.tamanho_uniforme, f.tamanho_luva
                FROM movimentacoes m
                JOIN epis e ON m.epi_id = e.id
                LEFT JOIN funcionarios f ON m.funcionario_id = f.id
                WHERE m.tamanho LIKE '%,%';
            """)
            for m_id, m_tam, e_nome, c_calc, c_uni, c_luva in cursor.fetchall():
                cands = [c.strip() for c in m_tam.split(",") if c.strip()]
                matched = None
                en_up = (e_nome or "").upper()
                if c_uni and c_uni not in ("-", "") and any(k in en_up for k in ["CAMISA", "UNIFORME", "CALÇA", "CALCA", "JALECO", "MOLETON"]):
                    for c in cands:
                        if c.upper() == c_uni.upper():
                            matched = c
                            break
                elif c_calc and c_calc not in ("-", "") and any(k in en_up for k in ["BOTA", "BOTINA", "CALÇADO", "CALCADO"]):
                    for c in cands:
                        if c.upper() == c_calc.upper():
                            matched = c
                            break
                elif c_luva and c_luva not in ("-", "") and "LUVA" in en_up:
                    for c in cands:
                        if c.upper() == c_luva.upper():
                            matched = c
                            break

                chosen = matched if matched else "Único"
                cursor.execute("UPDATE movimentacoes SET tamanho = ? WHERE id = ?;", (chosen, m_id))
        except Exception:
            pass

        # Migração: registros de movimentação com estado NÃO DEVOLVIDO devem ter tipo = 'NÃO DEVOLVIDO'
        try:
            cursor.execute("""
                UPDATE movimentacoes
                SET tipo = 'NÃO DEVOLVIDO'
                WHERE (tipo = 'DEVOLUCAO' OR tipo = 'SAIDA')
                  AND (UPPER(estado_conservacao) LIKE '%NÃO DEVOLV%' OR UPPER(estado_conservacao) LIKE '%NAO DEVOLV%' OR UPPER(estado_conservacao) LIKE '%RETIDO%');
            """)

            # Limpeza: itens que não foram devolvidos NÃO devem figurar em epi_grades com DESCARTE / SUCATA
            cursor.execute("""
                SELECT m.epi_id, m.tamanho, SUM(m.quantidade) as total_nao_dev
                FROM movimentacoes m
                WHERE m.tipo = 'NÃO DEVOLVIDO'
                   OR UPPER(m.estado_conservacao) LIKE '%NÃO DEVOLV%'
                   OR UPPER(m.estado_conservacao) LIKE '%NAO DEVOLV%'
                   OR UPPER(m.estado_conservacao) LIKE '%RETIDO%'
                GROUP BY m.epi_id, m.tamanho;
            """)
            for r_nd in cursor.fetchall():
                nd_eid, nd_tam, nd_qtd = r_nd[0], r_nd[1], r_nd[2]
                cursor.execute("""
                    UPDATE epi_grades
                    SET quantidade = MAX(0, quantidade - ?)
                    WHERE epi_id = ? AND UPPER(tamanho) = UPPER(?) AND (UPPER(estado) LIKE '%DESC%' OR UPPER(estado) LIKE '%SUCATA%');
                """, (nd_qtd, nd_eid, nd_tam))
                cursor.execute("""
                    UPDATE epis
                    SET qtd_descarte = MAX(0, qtd_descarte - ?)
                    WHERE id = ?;
                """, (nd_qtd, nd_eid))
        except Exception:
            pass

        # Migração: Preenche preco_usado com 50% do preco_unitario para registros existentes
        try:
            cursor.execute("""
                UPDATE epis
                SET preco_usado = ROUND(preco_unitario * 0.5, 2)
                WHERE (preco_usado IS NULL OR preco_usado = 0.0) AND preco_unitario > 0;
            """)
        except Exception:
            pass

        # Migração: Atualiza custos históricos em movimentacoes a partir dos preços configurados no EPI
        try:
            cursor.execute("""
                UPDATE movimentacoes
                SET custo_unitario = (
                    SELECT CASE 
                        WHEN UPPER(COALESCE(movimentacoes.estado_conservacao, '')) LIKE '%USADO%' 
                          OR UPPER(COALESCE(movimentacoes.estado_conservacao, '')) LIKE '%REUTIL%' 
                          OR UPPER(COALESCE(movimentacoes.estado_conservacao, '')) LIKE '%BOM%' 
                        THEN COALESCE(NULLIF(epis.preco_usado, 0.0), epis.preco_unitario * 0.5, 0.0)
                        ELSE COALESCE(epis.preco_unitario, 0.0)
                    END
                    FROM epis WHERE epis.id = movimentacoes.epi_id
                ),
                custo_total = quantidade * (
                    SELECT CASE 
                        WHEN UPPER(COALESCE(movimentacoes.estado_conservacao, '')) LIKE '%USADO%' 
                          OR UPPER(COALESCE(movimentacoes.estado_conservacao, '')) LIKE '%REUTIL%' 
                          OR UPPER(COALESCE(movimentacoes.estado_conservacao, '')) LIKE '%BOM%' 
                        THEN COALESCE(NULLIF(epis.preco_usado, 0.0), epis.preco_unitario * 0.5, 0.0)
                        ELSE COALESCE(epis.preco_unitario, 0.0)
                    END
                    FROM epis WHERE epis.id = movimentacoes.epi_id
                )
                WHERE (custo_unitario IS NULL OR custo_unitario = 0.0 OR custo_total IS NULL OR custo_total = 0.0)
                  AND EXISTS (SELECT 1 FROM epis WHERE epis.id = movimentacoes.epi_id AND epis.preco_unitario > 0);
            """)
        except Exception:
            pass

        # Grupos padrões de EPI
        default_grupos = [
            ("BOTA DE PVC", "Botas impermeáveis de policloreto de vinila (PVC) para umidade e químicos"),
            ("BOTA TÉRMICA", "Calçados e botas frigoríficas térmicas para baixas temperaturas"),
            ("CALÇADOS & BOTINAS DE SEGURANÇA", "Botinas com biqueira de aço/composite, sapatos ocupacionais"),
            ("CAMISAS DE SEGURANÇA / UNIFORMES", "Camisas operacionais, camisas UV e uniformes profissionais"),
            ("VESTIMENTAS & UNIFORMES", "Calças, macacões, aventais e vestimentas de proteção"),
            ("LUVAS DE PROTEÇÃO", "Luvas de segurança em geral para proteção das mãos"),
            ("LUVAS DE VAQUETA / RASPA", "Luvas de couro e raspa para serviços pesados, solda e abrasão"),
            ("LUVAS NITRÍLICAS / BORRACHA", "Luvas impermeáveis para contato com químicos e solventes"),
            ("ÓCULOS & PROTEÇÃO FACIAL", "Óculos de proteção ampla visão, protetores faciais"),
            ("CAPACETES DE SEGURANÇA", "Capacetes com jugular para proteção contra impactos na cabeça"),
            ("PROTEÇÃO AUDITIVA", "Protetores auriculares tipo concha e tipo plugue de inserção"),
            ("PROTEÇÃO RESPIRATÓRIA", "Máscaras descartáveis PFF2/N95 e respiradores semifaciais"),
            ("TRABALHO EM ALTURA", "Cintos tipo paraquedista, talabartes e trava-quedas (NR-35)"),
            ("DIVERSOS / OUTROS", "Outros equipamentos e acessórios de segurança e higiene"),
        ]
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for nome_g, desc_g in default_grupos:
            cursor.execute("INSERT OR IGNORE INTO grupos_epi (nome, descricao, created_at) VALUES (?, ?, ?);", (nome_g, desc_g, now_str))

        # Se houver algum item sem grupo cadastrado, define o padrão neutro 'DIVERSOS / OUTROS'.
        # O sistema não faz classificação automática por palavras-chave, respeitando 100% o que o usuário cadastrar.
        cursor.execute("UPDATE epis SET grupo = 'DIVERSOS / OUTROS' WHERE grupo IS NULL OR TRIM(grupo) = '';")

        # Higienização de registros de Não Devolvido / Extravio para o tipo 'NÃO DEVOLVIDO'
        cursor.execute("""
            UPDATE movimentacoes
            SET tipo = 'NÃO DEVOLVIDO'
            WHERE (tipo = 'DEVOLUCAO' OR tipo = 'EXTRAVIO_DEMISSAO')
              AND (UPPER(estado_conservacao) LIKE '%NÃO DEVOLV%' OR UPPER(estado_conservacao) LIKE '%NAO DEVOLV%' OR UPPER(estado_conservacao) LIKE '%RETIDO%');
        """)

        # Departamentos / Setores padrões da empresa
        default_deptos = [
            ("Linha de Montagem", "Setor de produção e montagem seriada"),
            ("Manutenção Industrial", "Equipe técnica mecânica, elétrica e predial"),
            ("Logística e Expedição", "Armazenagem, empilhadeiras e movimentação de cargas"),
            ("Operacional / Produção", "Fábrica e processamento operacional geral"),
            ("Segurança do Trabalho (SST)", "Engenharia e Técnicos de Segurança / CIPA"),
            ("Qualidade / Laboratório", "Controle de qualidade, testes e análises"),
            ("Administrativo / RH", "Escritório, RH, compras e diretoria"),
            ("Obras / Serviços Externos", "Atividades de campo, montagens e clientes")
        ]
        for nome_d, desc_d in default_deptos:
            cursor.execute("INSERT OR IGNORE INTO departamentos (nome, descricao, created_at) VALUES (?, ?, ?);", (nome_d, desc_d, now_str))

        # Migra departamentos já digitados em funcionarios para a tabela departamentos
        cursor.execute("SELECT DISTINCT departamento FROM funcionarios WHERE departamento IS NOT NULL AND departamento != '';")
        for f_row in cursor.fetchall():
            d_name = str(f_row[0]).strip()
            if d_name:
                cursor.execute("INSERT OR IGNORE INTO departamentos (nome, descricao, created_at) VALUES (?, ?, ?);", (d_name, f"Setor {d_name}", now_str))

        # Configurações padrão
        default_configs = [
            ("empresa_nome", "EMPRESA INDUSTRIAL LTDA"),
            ("empresa_cnpj", "00.000.000/0001-00"),
            ("empresa_endereco", "Rua Industrial, 1000 - Distrito Industrial"),
            ("responsavel_seguranca", "Técnico de Segurança do Trabalho"),
            ("tema_app", "Dark"),
            ("exigir_login", "0"), # 0 = Login rápido opcional / 1 = Exigir login ao abrir
            ("smtp_servidor", "smtp.gmail.com"),
            ("smtp_porta", "587"),
            ("smtp_usuario", ""),
            ("smtp_senha", ""),
            ("smtp_remetente", "almoxarifado@empresa.com"),
            ("alerta_destinatarios", "compras@empresa.com, seguranca@empresa.com"),
            ("termo_nr6", (
                "Recebi da empresa os Equipamentos de Proteção Individual (EPIs) acima relacionados, "
                "novos e em perfeitas condições de uso, devidamente higienizados e com os Certificados "
                "de Aprovação (C.A.) válidos, de acordo com o disposto na Norma Regulamentadora NR-6 "
                "do Ministério do Trabalho e Emprego.\n\n"
                "Comprometo-me a usá-los apenas para a finalidade a que se destinam, responsabilizando-me "
                "pela sua guarda e conservação, comunicando imediatamente qualquer alteração que os torne "
                "impróprios para uso, sob pena das sanções disciplinares cabíveis."
            )),
            ("termo_devolucao", (
                "Declaro para os devidos fins que procedi à devolução dos Equipamentos de Proteção Individual (EPIs) "
                "acima descritos, no estado de conservação indicado, dando à empresa plena e rasa quitação quanto à posse "
                "e guarda dos mesmos, nos termos da NR-6 e da legislação trabalhista vigente."
            )),
            ("percentual_valor_usado", "50")
        ]

        for k, v in default_configs:
            cursor.execute("INSERT OR IGNORE INTO configuracoes (chave, valor) VALUES (?, ?);", (k, v))

        # Cria usuário administrador padrão se não houver usuários
        cursor.execute("SELECT COUNT(*) FROM usuarios_sistema;")
        if cursor.fetchone()[0] == 0:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            admin_hash = hash_password("admin123")
            almox_hash = hash_password("1234")
            cursor.execute("""
                INSERT INTO usuarios_sistema (username, password_hash, nome, cargo, perfil, ativo, created_at)
                VALUES (?, ?, ?, ?, ?, 1, ?)
            """, ("admin", admin_hash, "Administrador Geral", "Engenheiro de Segurança / Admin", "ADMIN", now))
            cursor.execute("""
                INSERT INTO usuarios_sistema (username, password_hash, nome, cargo, perfil, ativo, created_at)
                VALUES (?, ?, ?, ?, ?, 1, ?)
            """, ("almoxarife", almox_hash, "Carlos Almoxarife", "Almoxarife", "ALMOXARIFE", now))

        # Operadores padrão se estiver vazio
        cursor.execute("SELECT COUNT(*) FROM operadores;")
        if cursor.fetchone()[0] == 0:
            cursor.execute("INSERT INTO operadores (nome, cargo) VALUES (?, ?);", ("Carlos Almoxarife", "Almoxarife"))
            cursor.execute("INSERT INTO operadores (nome, cargo) VALUES (?, ?);", ("Mariana SST", "Técnico SST"))
            cursor.execute("INSERT INTO operadores (nome, cargo) VALUES (?, ?);", ("João do Estoque", "Almoxarife Auxiliar"))

        conn.commit()

if __name__ == "__main__":
    init_db()
    print("Banco de dados atualizado com sucesso com as novas tabelas e colunas!")
