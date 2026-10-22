# 🛡️ EPI Master Pro - Sistema de Controle de Estoque & Fichas de EPI (NR-6)

Aplicativo Desktop profissional desenvolvido para gestão completa, auditoria e controle rigoroso de **Equipamentos de Proteção Individual (EPI)**, em conformidade com as exigências da **Norma Regulamentadora NR-6** do Ministério do Trabalho.

---

## ⚡ EXECUTÁVEL PORTÁTIL PRONTO (Use em Qualquer Computador)

O executável independente foi gerado e está pronto para ser utilizado em **qualquer computador com Windows**, sem precisar instalar Python, bibliotecas ou qualquer outro programa!

### 📌 Como usar o executável portátil:
- **Abrir com 1 clique:** Dê um duplo clique em [Abrir_Executavel.bat](file:///c:/Users/werle/Desktop/EPI/Abrir_Executavel.bat).
- **Pasta Independente:** A pasta completa está localizada em:
  `c:\Users\werle\Desktop\EPI\dist\EPI_Master_Pro\`
  - Você pode copiar a pasta inteira `EPI_Master_Pro` para um **Pen-drive**, enviá-la por e-mail/zip ou colocá-la na rede da sua empresa.
  - Para abrir diretamente na pasta, dê um duplo clique no arquivo:
    **`EPI_Master_Pro.exe`**

---

## 🌙 NOVO: TEMA ESCURO (DARK MODE) INTEGRADO

O aplicativo agora conta com alternância instantânea de tema:
- **Botão na Barra Lateral:** Clique em `☀️ Modo Claro` ou `🌙 Modo Escuro` a qualquer momento para alternar o visual de toda a aplicação (telas, tabelas, caixas de diálogo, campos de busca e formulários).
- **Lembrança Automática:** Sua preferência fica salva no banco de dados SQLite e será lembrada automaticamente nas próximas inicializações.

---

## 📋 Principais Funcionalidades

### 1. 📦 Controle Preciso de Estoque de EPIs
- **Cadastro Completo:** Código, Nome do EPI, Número do Certificado de Aprovação (**C.A.**), Validade do C.A., Fabricante/Marca, Tamanho, Unidade de Medida (UN, PAR, KIT, etc.), Saldo Atual, Estoque Mínimo e Localização no Almoxarifado (prateleira/gaveta).
- **Alertas Visuais em Tempo Real:** 
  - 🟢 **Normal:** Saldo acima do estoque mínimo.
  - 🟡 **Estoque Baixo:** Saldo atingiu ou está abaixo do limite de segurança.
  - 🔴 **Zerado:** Produto esgotado no almoxarifado.
- **Entrada e Reposição:** Registro de notas fiscais de compra e novos lotes adicionados ao saldo.

### 2. 📤 Registro de Saídas & Entregas (Quem Colocou / Quem Entregou)
- **Identificação Obrigatória do Responsável:** Ao registrar a entrega para um funcionário, o sistema exige e armazena **quem entregou/colocou o item**.
- **Controle Preciso:** O sistema consulta o saldo físico no exato momento da entrega e impede saídas superiores ao estoque disponível.
- Registro completo: Colaborador, EPI, Quantidade, Responsável pela Entrega, Data/Hora, Motivo (*Admissional, Troca Periódica, Desgaste, Perda, Mudança de Função*) e Observações.

### 3. 📄 Fichas Individuais de EPI por Funcionário (Conforme NR-6)
- **Histórico Completo por Colaborador:** Veja todos os equipamentos recebidos pelo funcionário desde a admissão.
- **Emissão da Ficha Oficial em PDF:**
  - Gera um documento em formato **A4 Paisagem** contendo:
    - Cabeçalho oficial com **Razão Social**, **CNPJ** e dados da sua empresa.
    - Dados completos do colaborador (Nome, CPF, Matrícula, Função, Setor, Data de Admissão).
    - **Termo Legal de Responsabilidade e Guarda de EPI** (conforme redação da NR-6 e CLT).
    - Tabela de entregas com campos de conferência e **espaço para assinatura física do colaborador**.
  - Abre automaticamente no visualizador de PDF padrão do Windows pronto para **imprimir**.

### 4. 📈 Relatórios & Auditoria Organizados
- Relatórios personalizáveis com filtros por:
  - **Período:** Atalhos rápidos (*Hoje*, *Últimos 7 dias*, *Este Mês*, *Tudo*) ou intervalo de datas customizado.
  - **Tipo de Movimentação:** Saídas, Entradas, Devoluções ou Todas.
  - **Filtro Textual:** Por Produto, por Funcionário, por C.A. ou por Responsável pela Entrega.
- **Exportação Dupla:**
  - 📊 **Planilha Excel (.xlsx):** Formatada profissionalmente com estilos corporativos, larguras automáticas e dados estruturados.
  - 📄 **Relatório em PDF:** Formatado para apresentação a gerências, auditorias do trabalho ou fiscalização.

### 6. ✍️ Assinatura Digital na Tela (Touchscreen / Mouse)
- **Painel Interativo de Assinatura:** No momento da entrega de EPIs ou da entrega em lote do Kit Admissional, o colaborador pode assinar digitalmente diretamente na tela usando mouse, caneta touch ou a ponta do dedo.
- **Inclusão Automática no PDF:** A assinatura gráfica é capturada, vinculada ao registro no banco de dados e impressa diretamente na linha correspondente da **Ficha Oficial NR-6 em PDF**.

---

### 7. 🏷️ Etiquetas com Código de Barras & Leitura por Bipe
- **Geração de Etiquetas (Code128):** Na tela de Estoque, clique em `🏷️ Imprimir Etiquetas Barcode` para gerar uma folha A4 pronta para impressão contendo etiquetas com Código de Barras Code128, Código do EPI, Nome, C.A. e Localização na Prateleira.
- **Campo de Bipe Rápido:** Na tela de Saída/Entregas, o operador pode simplesmente bipar o código com qualquer leitor de código de barras USB/sem fio, e o sistema seleciona automaticamente o EPI no formulário.

---

### 8. 🎯 Matriz de EPIs por Cargo & Kit Admissional (Entrega em Lote)
- **Definição por Cargo:** Vincule os EPIs obrigatórios a cada função (ex.: *Mecânico de Manutenção*, *Operador de Produção*, *Eletricista*), definindo a quantidade e a periodicidade padrão de troca (dias de vida útil).
- **Entrega de Kit com 1 Clique:** Ao admitir um novo funcionário ou renovar equipamentos, basta selecionar o colaborador e clicar em `📦 Entregar Kit Completo`. O sistema gera a baixa de todos os itens simultaneamente com verificação de estoque e coleta de assinatura digital única.

---

### 9. 💰 Valoração Financeira & Custos
- **Custo Unitário e Total do Estoque:** Cada EPI possui preço de aquisição. O sistema calcula e exibe em tempo real o valor financeiro total imobilizado no almoxarifado.
- **Relatório de Gastos:** Total investido em entregas por período, permitindo apurar custos de segurança por departamento, centro de custo ou colaborador.

---

### 10. ⏳ Alertas de Validade de C.A. & Troca Preventiva
- **Validade do C.A.:** Filtro rápido na tela de estoque destacando EPIs com Certificado de Aprovação vencido ou prestes a vencer em 60 dias.
- **Previsão de Troca:** No Dashboard, o painel lista colaboradores com EPIs próximos do fim da vida útil calculada, permitindo a substituição preventiva antes de qualquer não-conformidade.

---

### 11. 🔐 Perfis de Acesso & Segurança
- **Controle de Usuários:** Autenticação por usuário e senha com criptografia SHA-256.
- **Níveis de Permissão:**
  - `ADMIN`: Acesso total a configurações, cadastro de operadores, matriz de cargos e backup.
  - `ALMOXARIFE`: Operações diárias de entrada, saída, entregas e relatórios.
  - `CONSULTA`: Visualização de estoque, fichas e dashboards em modo somente leitura.
- Usuários padrão pré-configurados:
  - **Admin:** `admin` / senha: `admin`
  - **Almoxarife:** `almoxarife` / senha: `123`
  - **Consulta:** `consulta` / senha: `123`

---

### 12. 📥 Importação em Massa via Excel (Colaboradores e EPIs)
- **Carga Rápida de Dados:** Nas telas de Funcionários e Estoque, clique em `📥 Importar Excel` para cadastrar centenas de registros de uma só vez a partir de planilhas `.xlsx` ou arquivos `.csv`.
- **Planilhas Modelo Prontas:** Botão `📄 Modelo` para gerar e abrir automaticamente as planilhas modelo já formatadas com exemplos.

---

### 13. 📄 Termo de Devolução & Quitação de EPIs (Demissão / Troca)
- **Módulo de Devolução:** Na tela de Fichas de EPI, clique em `🔄 DEVOLUÇÃO / QUITAÇÃO DE EPI`.
- **Blindagem Jurídica:** Selecione os EPIs em posse do colaborador, defina o estado de conservação (*Bom Estado, Higienizado, Desgaste Natural, Danificado, Descartado*), colete a assinatura digital na tela e gere o **Termo Oficial de Devolução e Quitação de EPIs em PDF (A4 Paisagem)**.

---

### 14. 📊 Gráficos Visuais Interativos no Dashboard
- **Top 5 EPIs Mais Consumidos:** Gráfico de barras horizontais em tempo real indicando os equipamentos de maior rotatividade e custo.
- **Gastos com EPI por Departamento:** Gráfico visual comparativo do investimento em proteção individual alocado em cada setor.

---

### 15. 🌐 Consulta Automática Online de C.A. (MTE)
- **Validação Imediata:** No cadastro/edição de qualquer EPI, clique em `🔍 Consultar` ao lado do número do C.A. para verificar a validade, situação e fabricante oficial, preenchendo as informações técnicas automaticamente.

---

### 16. 📬 Alertas & Notificações por E-mail (SMTP)
- **Configuração Completa:** Aba dedicada em Configurações para servidor SMTP (Gmail, Outlook, servidores corporativos com suporte a TLS/SSL).
- **Disparo de Alertas:** Botão `🚨 Disparar Alerta por E-mail` no Dashboard que compila e envia um relatório em HTML com os EPIs abaixo do estoque mínimo e C.A.s a vencer aos e-mails de Compras e Segurança do Trabalho.

---

### 17. 🛡️ Trilha de Auditoria Completa (Logs de Ações)
- **Rastreabilidade Absoluta:** Todas as ações críticas (criação/edição de EPIs, saídas, devoluções, importações em massa, alterações de parâmetros e backups) são registradas com data, hora, módulo, ação e usuário logado.
- **Visualização e Busca:** Aba de auditoria com busca textual e filtro por módulo do sistema.

---

## 🗄️ Estrutura de Arquivos

```
c:\Users\werle\Desktop\EPI\
│
├── Abrir_Executavel.bat       # Abre o executável compilado (.exe) com 1 clique
├── Iniciar_EPI.bat            # Execução direta com Pythonw
├── build.py                   # Script de compilação com PyInstaller
├── main.py                    # Ponto de entrada do sistema
├── database.py                # Gerenciador de conexão SQLite e migrações
│
├── dist\EPI_Master_Pro\       # 🚀 PASTA PORTÁTIL (Copie para qualquer Pen-Drive ou PC)
│   ├── EPI_Master_Pro.exe     # Executável independente (Não precisa de Python)
│   ├── data\                  # Banco de dados SQLite portátil e assinaturas
│   └── exports\               # Fichas NR-6, etiquetas e relatórios gerados
│
├── services/                  # Regras de negócio (PDF, Excel, Barcode, Matriz, EPIs)
├── ui/                        # Interface Gráfica moderna com Dark/Light Mode
└── README.md
```
