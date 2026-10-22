# 📋 HANDOFF - EPI MASTER PRO
**Sistema Profissional de Gestão de EPIs, Fichas NR-6 e Controle de Almoxarifado**  
**Versão Atual:** `3.6.4` | **Data:** `22/10/2026` | **Repositório:** [https://github.com/werleyoli/EPI.git](https://github.com/werleyoli/EPI.git)

---

## 1. 📌 Visão Geral do Sistema
O **EPI Master Pro** é uma aplicação desktop desenvolvida em Python para gerenciamento completo do ciclo de vida de Equipamentos de Proteção Individual (EPIs), atendendo rigorosamente às exigências legais das Normas Regulamentadoras do Ministério do Trabalho e Emprego:
- **NR-6:** Equipamentos de Proteção Individual, fichas de entrega nominais, controle de C.A. e assinaturas do colaborador.
- **NR-35 & NR-33:** Inspeções e manutenções periódicas de equipamentos duráveis para trabalho em altura e espaços confinados.

---

## 2. 🏗️ Arquitetura e Estrutura do Projeto

```
EPI/
├── main.py                     # Ponto de entrada da aplicação e inicialização do CustomTkinter
├── version.py                  # Controle centralizado de versão (v3.6.4) e release
├── database.py                 # Conexão SQLite, DDL das tabelas e migrações dinâmicas
├── seed_data.py                # Dados iniciais para inicialização rápida do sistema
├── build.py                    # Script automatizado de compilação com PyInstaller
├── EPI_Master_Pro.spec         # Especificação de empacotamento do executável
│
├── assets/                     # Ícones, imagens de apoio e logotipos
├── data/                       # Banco de dados local (epi_control.db) e assinaturas
├── exports/                    # PDFs e relatórios gerados (Fichas NR-6, ordens de compra, etc.)
│
├── services/                   # Camada de Regras de Negócio e Serviços
│   ├── auth_service.py         # Autenticação, controle de usuários (Admin/Almoxarife) e logs
│   ├── ca_service.py           # Consulta online oficial de Certificados de Aprovação (MTE)
│   ├── compra_service.py       # Gestão de reposição e ordens de compra automáticas
│   ├── devolucao_service.py    # Devolução de EPIs, higienização, manutenção e descartes
│   ├── employee_service.py     # Gestão de colaboradores, biometria de tamanhos e ficha NR-6
│   ├── epi_service.py          # Catálogo de EPIs, famílias/grupos, preços e estoque por grade
│   ├── excel_service.py        # Importação e exportação de planilhas Excel / CSV
│   ├── import_service.py       # Assistente de carga de dados Legado
│   ├── movement_service.py     # Registro de entradas, saídas, baixas e histórico retroativo
│   ├── pdf_service.py          # Geração profissional de Fichas NR-6 e relatórios (ReportLab)
│   ├── validade_uso_service.py # Controle de vida útil de EPIs em uso e cartas de convocação
│   └── whatsapp_service.py     # Envio de comprovantes e convocações via WhatsApp Web
│
└── ui/                         # Interface Gráfica (CustomTkinter)
    ├── app.py                  # Janela principal, sidebar lateral e roteamento de telas
    ├── components/             # Componentes reutilizáveis
    │   ├── chart_canvas.py     # Gráficos embutidos sem dependências pesadas
    │   ├── date_picker.py      # Seletor interativo de calendário (DatePickerDialog)
    │   ├── signature_pad.py    # Painel interativo de assinatura digital por mouse/touch
    │   ├── table_view.py       # Tabela paginada e estilizada com temas claro/escuro
    │   └── theme.py            # Definição de paleta de cores e tipografia
    └── views/                  # Telas do sistema
        ├── dashboard_view.py   # Painel com KPIs de estoque, saídas e trocas pendentes
        ├── employee_sheet_view.py # Ficha nominal NR-6, assinatura e emissão de PDF
        ├── employees_view.py   # Cadastro de funcionários e grade de tamanhos individuais
        ├── inventory_view.py   # Catálogo de EPIs, estoque por grade e preços duplos
        ├── movements_view.py   # Lançamento de saídas, entradas, devoluções e histórico
        ├── reports_view.py     # Relatórios gerenciais e inspeções periódicas
        ├── settings_view.py    # Configurações da empresa, cabeçalho da ficha e backup
        └── tv_mode_view.py     # Painel em tela cheia para monitor de TV no almoxarifado
```

---

## 3. ✨ Histórico de Melhorias Implementadas

### 🎯 Versão 3.6.4 (Atual)
1. **Sincronização Dinâmica e Retroativa de Custos no Dashboard e Relatórios:**
   - Adicionada rotina de migração em `database.py` que calcula e atualiza retroativamente `custo_unitario` e `custo_total` para movimentações históricas que estavam com valor zerado.
   - Atualizado o serviço `EPIService.update_epi` para propagar automaticamente novos preços para movimentações passadas do EPI em questão que ainda não possuíam valor.
   - Refatoradas as consultas em `MovementService` (`get_recent_stats`, `get_top_epis_consumed`, `get_department_costs`, `get_financial_summary`, `get_movement`, `list_movements`) utilizando lógica `CASE / COALESCE(NULLIF(...))` para que o Dashboard e os extratos reflitam os custos reais mesmo em transações cadastradas antes da atribuição de preço.
2. **Cálculo de Preço Unitário e Prejuízo no Relatório de Itens Não Devolvidos:**
   - No relatório em PDF de Manutenção, Descarte e Retidos (`PDFService.generate_maintenance_discard_pdf`), a tabela `[3] ITENS NÃO DEVOLVIDOS / RETIDOS` agora puxa o valor unitário cadastrado do EPI caso a saída estivesse com custo zerado, garantindo o preenchimento exato da coluna `Custo Unit.` e do cálculo de `Prejuízo R$` para cobrança em TRCT ou notificação.
3. **Correção da Exibição do Período no Extrato de Movimentações:**
   - Corrigida a formatação de período em `reports_view.py`, tratando datas no formato brasileiro `DD/MM/AAAA` e eliminando o erro de quebra de string (`26//2 a 26//2...`).
4. **Filtro de Colaboradores Inativos na Ficha NR-6:**
   - Na tela da Ficha Individual de EPI (`EmployeeSheetView`), o menu de colaboradores passa a carregar **apenas colaboradores ativos por padrão**.
   - Adicionado o checkbox interativo `[ ] Exibir Inativos` ao lado do seletor: ao marcar, os colaboradores inativos/desligados passam a ser listados com a tag visual `[INATIVO]` no nome.
   - Ao selecionar um colaborador desligado através de atalhos em outras telas, o sistema ativa automaticamente a opção de inativos para permitir a auditoria da ficha.

### 🎯 Versão 3.6.3
1. **Identificação de Produto Novo ou Usado na Ficha de EPI (Tela e PDF):**
   - Na impressão PDF (NR-6), a condição do equipamento entregue é inserida de forma elegante diretamente abaixo do nome do produto (`<br/><font size=6.5 color='...'><b>[NOVO]</b></font>` ou `[USADO]`), mantendo o layout limpo sem necessidade de criar colunas extras que espremam os dados.
   - Na tabela de Histórico em tela (`EmployeeSheetView`), o nome do equipamento recebe a identificação clara `[NOVO]` ou `[USADO]`.
   - Compatibilidade automática com todo o histórico retroativo e novas saídas cadastradas.

### 🎯 Versão 3.6.2
1. **Ordenação Cronológica das Saídas na Ficha (De Cima para Baixo):**
   - Ajustada a consulta SQL (`services/employee_service.py`) de `ORDER BY m.data_hora DESC` para `ORDER BY m.data_hora ASC, m.id ASC`.
   - No relatório em PDF (`services/pdf_service.py`), garantida a ordenação cronológica estrita das entregas: a primeira entrega do histórico aparece na linha superior e as entregas posteriores descem sequencialmente de cima para baixo, respeitando o preenchimento de formulários físicos de segurança do trabalho.

### 🎯 Versão 3.6.1
1. **Data de Validade / Troca Calculada na Ficha e no PDF:**
   - O sistema calcula a data exata limite de uso com base na data da entrega somada aos dias de vida útil cadastrados no produto (`data_hora + dias_vida_util`).
   - Na tela da Ficha: Exibido como `DD/MM/AAAA (6m)` ou `DD/MM/AAAA (180d)`.
   - Na impressão PDF (NR-6): Data calculada em negrito `DD/MM/AAAA` com o intervalo de meses `(6m)` logo abaixo.
2. **Padronização Universal dos Campos de Data com DatePicker:**
   - Todos os formulários que possuíam campos de data manuais ou em padrão americano foram atualizados para o padrão brasileiro `DD/MM/AAAA`.
   - Adicionado botão interativo de calendário `[📅]` e atalho de duplo clique (`<Double-Button-1>`) que abre o seletor `DatePickerDialog`:
     - Modal de Entrada de Estoque (`open_stock_entry_dialog`).
     - Modal de Edição de Movimentação (`open_edit_movement_dialog`).
     - Modal de Entrega Retroativa de EPI (`open_exit_modal`).
     - Modal de Cadastro/Edição de EPI (`open_epi_dialog`).
     - Modal de Cadastro/Edição de Colaborador (`open_employee_dialog`).
     - Modal de Inspeção Periódica (`open_inspection_dialog`).
3. **Divisão de Preço Unitário Novo e Preço Usado (50%) no EPI:**
   - Adicionada coluna `preco_usado` na tabela `epis` com migração dinâmica de schema.
   - No cadastro de EPI, os campos foram divididos em `Preço Unit. Novo (R$)` e `Preço Unit. Usado (50%) (R$)`.
   - Cálculo automático instantâneo: ao digitar o preço novo, o campo de preço usado calcula automaticamente 50% do valor, mantendo edição manual liberada para o administrador.
   - Puxada automática nos lançamentos: entregas com condição física `USADO / REUTILIZADO` carregam diretamente o valor do produto usado.

### 🎯 Versões 3.5.x e Anteriores
1. **Modal de Saída Aberto Diretamente na Ficha do Colaborador:**
   - O botão *Registrar Saída / Entrega de EPI* na própria ficha de EPI abre o modal com o colaborador já pré-selecionado, sem redirecionamentos desnecessários.
2. **Segregação de Manutenção e Descarte:**
   - Produtos devolvidos em estado de manutenção ou descarte não inflacionam o estoque útil e possuem relatórios e grades segregados.
3. **Tratamento de Itens Não Devolvidos:**
   - Colaboradores demitidos que não devolvem itens possuem status destacado em vermelho (`🚨 NÃO DEV.`) na tela e no PDF para auditoria de extravio.
4. **Layout dos Botões do Cabeçalho:**
   - Organização dos botões em duas linhas horizontais com espaçamento equilibrado, eliminando sobreposições ou quebras em telas de menor resolução.
5. **Assinatura Digital & Foto de Entrega:**
   - Pad touchscreen/mouse para o colaborador assinar digitalmente e integração com webcam para registro fotográfico.

---

## 4. 🗄️ Modelo de Dados (SQLite)

O banco de dados armazena dados em `data/epi_control.db` e conta com as seguintes tabelas principais:
- `epis`: Catálogo de produtos, C.A., validade, fabricante, vida útil, preços (`preco_unitario`, `preco_usado`) e estoques consolidados.
- `epi_grades`: Estoques detalhados por variação de tamanho e condição física (`NOVO`, `BOM/USADO`, `RUIM/MANUTENÇÃO`, `DESCARTE/SUCATA`).
- `grupos_epi`: Categorias e famílias de EPIs para agrupamento em relatórios e estoque.
- `funcionarios`: Cadastro com matrícula, cargo, setor, admissão, PIN e biometria de tamanhos (calçado, luva, uniforme, máscara).
- `movimentacoes`: Histórico de todas as saídas, entradas, devoluções e baixas, armazenando custo unitário, estado, fotos e caminhos de assinaturas PNG.
- `inspecoes_epi`: Registro de inspeções periódicas de EPIs duráveis (NR-35/NR-33) com controle de validade de laudo.
- `configuracoes`: Chaves e valores de personalização da empresa, texto oficial do Termo NR-6 e dados de SMTP/Backup.
- `logs_auditoria`: Rastreabilidade de ações críticas realizadas no sistema.

---

## 5. 🚀 Guia de Execução e Compilação

### Como rodar em ambiente de desenvolvimento:
```bash
# Ativar ambiente virtual (se houver)
python main.py
```

### Como compilar o executável portátil:
```bash
python build.py
```
O script gera o executável standalone na pasta:
`dist/EPI_Master_Pro/EPI_Master_Pro.exe`

---

## 6. 🔮 Possíveis Pendências e Backlog de Melhorias Futuras

1. **Sincronização em Nuvem (Multi-unidades):**
   - Atualmente o sistema utiliza banco local SQLite (`data/epi_control.db`). Para empresas que possuem múltiplos almoxarifados ou obras remotas, pode-se implementar um conector para PostgreSQL / Supabase para sincronização em tempo real.
2. **Leitor Biométrico USB Dedicado:**
   - Adicionar suporte a leitores de impressão digital USB (ex: DigitalPersona / Nitgen) como alternativa adicional à assinatura digital e foto por webcam.
3. **Disparo Automático de Alertas em Segundo Plano (Serviço Windows):**
   - Criação de um serviço Windows em segundo plano para envio diário de avisos via e-mail e WhatsApp para gestores de segurança sobre C.A.s a vencer e colaboradores com EPIs com vida útil expirada.
4. **Módulo de Transferência entre Almoxarifados / Frentes de Obra:**
   - Cadastro de filiais e controle de transferências internas de saldo de EPIs entre depósitos centrais e obras periféricas.
5. **Leitura de Código de Barras / QR Code via Câmera do Notebook:**
   - Leitura de código de barras atualmente aceita leitor USB/bipe. Pode ser adicionado o leitor via vídeo da webcam em tempo real.

---
**Responsável Técnico:** Werley Oliveira  
**Licença:** Proprietário / Uso Interno  
