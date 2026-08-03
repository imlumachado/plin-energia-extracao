# PLIN Energia — Extração e Dashboard

Sistema para extrair relatórios do portal PLIN Energia (via Playwright), persistir as faturas em SQLite e apresentar um dashboard Streamlit com a identidade visual da dbm (preto, verde e branco, fonte Stack Sans).

## Estrutura

| Arquivo | Função |
|---|---|
| `Teste_Plin_Playwright.py` | Robô de captura dos relatórios do portal PLIN |
| `extracao.py` | Funções de extração/normalização das faturas |
| `db.py` | Camada de persistência SQLite (schema, upsert, consultas) |
| `dashboard.py` | Dashboard Streamlit (KPIs, gráficos, tabela) |
| `executar_extracao.ps1` | Script PowerShell para execução agendada (headless + log) |
| `fontes/` | Fontes Stack Sans embutidas no dashboard via base64 |
| `saida_plin/plin.db` | Banco SQLite com as faturas (versionado para o deploy) |

## Pré-requisitos

- Python 3.10+ (local: 3.13)
- Google Chrome/Chromium (para o Playwright)
- Credenciais do portal PLIN

## Configuração

1. Instale as dependências:

   ```powershell
   .venv\Scripts\python.exe -m pip install -r requirements.txt
   ```

2. Instale o navegador do Playwright (se ainda não tiver):

   ```powershell
   .venv\Scripts\python.exe -m playwright install chromium
   ```

3. Crie o arquivo `.env` a partir do exemplo e preencha as credenciais:

   ```
   PLIN_EMAIL=contasapagar@dbm.com.br
   PLIN_SENHA=SUA_SENHA
   ```

   O `.env` está no `.gitignore` e nunca deve ser commitado.

## Executar a extração manualmente

Modo interativo (abre o navegador):

```powershell
.venv\Scripts\python.exe Teste_Plin_Playwright.py
```

Modo automatizado (headless, sem janela):

```powershell
$env:PLIN_HEADLESS = "1"
.venv\Scripts\python.exe Teste_Plin_Playwright.py
```

A saída é gravada em `saida_plin/` (JSON, CSV, Excel, HTML, screenshot) e o banco SQLite é atualizado com upsert (sem duplicar).

## Agendar a extração no Windows

A tarefa `Plin_Extracao_Mensal` roda todo dia 5 às 06:00. Para recriar:

```powershell
schtasks /Create /TN "Plin_Extracao_Mensal" /TR "powershell.exe -NoProfile -ExecutionPolicy Bypass -File \"C:\caminho\para\executar_extracao.ps1\"" /SC MONTHLY /D 5 /ST 06:00 /F
```

O script `executar_extracao.ps1` define `PLIN_HEADLESS=1` e grava logs em `logs/` com carimbo de data/hora.

## Rodar o dashboard localmente

```powershell
.venv\Scripts\python.exe -m streamlit run dashboard.py
```

Acesse `http://localhost:8501`.

## Publicar no Streamlit Community Cloud

1. Acesse **https://share.streamlit.io** e entre com a conta GitHub (`imlumachado`).
2. Clique em **New app** → **Deploy a public app from GitHub**.
3. Selecione o repositório `plin-energia-extracao`, branch `main`.
4. Em **Main file path**, informe: `dashboard.py`.
5. Em **Advanced settings**, selecione Python 3.13 (ou 3.11+).
6. Clique em **Deploy** e aguarde alguns minutos.

Dependências (`streamlit`, `pandas`, `plotly`) estão no `requirements.txt`; o tema visual está em `.streamlit/config.toml`; os dados vêm de `saida_plin/plin.db` (já versionado).

Para atualizar os dados publicados após uma extração, basta commitar o novo `saida_plin/plin.db` e enviar ao GitHub — o Streamlit Cloud redeploya automaticamente.

## Atualizar o banco no repositório

```powershell
git add saida_plin/plin.db
git commit -m "chore: atualiza banco de faturas"
git push origin main
```
