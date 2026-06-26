# Instalação no Windows Server — Cash Auditor

Guia para instalar o `cash_auditor.exe` no **servidor de homologação** e, depois de
aprovado, promover para o **servidor de produção** da agência central.

O `cash_auditor.exe` é um executável único: contém a API, o dashboard e o
servidor web. **Não é necessário instalar Python** no servidor.

---

## 1. Obter o executável

> **Ativar a compilação automática (uma vez):** por restrição de permissão, o
> workflow do GitHub Actions foi versionado em [`docs/ci/build-windows.yml`](ci/build-windows.yml).
> Para ativá-lo, mova-o para `.github/workflows/build-windows.yml` no seu
> repositório (ex.: `git mv docs/ci/build-windows.yml .github/workflows/build-windows.yml`
> e faça commit). A partir daí, cada push na `main` compila o `.exe`.

O `.exe` é compilado automaticamente no GitHub Actions (runner Windows):

- **Por build (qualquer push na `main`):** aba **Actions** → workflow
  **`build-windows-exe`** → abra o run mais recente → baixe o artifact
  **`cash_auditor-exe`** (um `.zip` contendo `cash_auditor.exe`).
- **Por versão (recomendado para homologação/produção):** crie uma tag
  `vX.Y.Z` no repositório; o `.exe` é anexado à **Release** correspondente.

> Assim você consegue rastrear exatamente qual versão está em homologação e qual
> foi aprovada para produção.

---

## 2. Homologação

1. Crie a pasta `C:\CashAuditor\` e copie o `cash_auditor.exe` para dentro dela.
2. Execute o `cash_auditor.exe` (duplo-clique ou pelo Prompt de Comando).
   - Na primeira execução, o banco **SQLite** `cash_auditor.db` é criado **na mesma
     pasta** do `.exe` e persiste entre reinícios.
   - O dashboard abre automaticamente em `http://localhost:8000`.
3. Para acessar de outras máquinas da rede (gerentes), inicie liberando o host:

   ```bat
   set CASH_AUDITOR_HOST=0.0.0.0
   set CASH_AUDITOR_PORT=8000
   cash_auditor.exe
   ```

   Acesse de outro PC por `http://IP_DO_SERVIDOR:8000`.
4. Libere a porta no firewall (uma vez, em PowerShell como Administrador):

   ```powershell
   New-NetFirewallRule -DisplayName "Cash Auditor 8000" -Direction Inbound `
     -Protocol TCP -LocalPort 8000 -Action Allow
   ```

5. Valide os fluxos: cadastro de agências, cadastro de contadoras, ingestão de
   contagens (via `POST /api/contagens/ingest` com a `api_key`) e o tempo real no
   dashboard.

---

## 3. Rodar como serviço do Windows (início automático)

Para o sistema subir sozinho com o servidor e reiniciar em caso de falha, use o
[NSSM](https://nssm.cc/) (Non-Sucking Service Manager):

```powershell
# Instale o nssm (ex.: via choco install nssm) e depois:
nssm install CashAuditor "C:\CashAuditor\cash_auditor.exe"
nssm set CashAuditor AppDirectory "C:\CashAuditor"
nssm set CashAuditor AppEnvironmentExtra CASH_AUDITOR_HOST=0.0.0.0 CASH_AUDITOR_PORT=8000 CASH_AUDITOR_NO_BROWSER=1
nssm start CashAuditor
```

- `CASH_AUDITOR_NO_BROWSER=1` evita tentar abrir o navegador no servidor.
- O serviço reinicia automaticamente e sobe junto com o Windows.
- Para parar/atualizar: `nssm stop CashAuditor`.

---

## 4. Banco de dados

| Cenário | Recomendação |
|---|---|
| Homologação | SQLite (padrão) — arquivo `cash_auditor.db` ao lado do `.exe`. |
| Produção | **PostgreSQL** — defina `DATABASE_URL` antes de iniciar. |

Exemplo para produção com PostgreSQL:

```bat
set DATABASE_URL=postgresql+psycopg://usuario:senha@servidor-bd:5432/cash_auditor
cash_auditor.exe
```

(ou configure a mesma variável no serviço via `nssm set ... AppEnvironmentExtra`).

### Backup

- **SQLite:** basta copiar o arquivo `cash_auditor.db` (com o serviço parado, ou
  use cópia consistente). Restaurar = colocar o arquivo de volta na pasta do `.exe`.
- **PostgreSQL:** `pg_dump` agendado (diário) e `pg_restore`/`psql` para restaurar.

---

## 5. Promover de homologação para produção

1. Após aprovado em homologação, use **a mesma versão** (mesma tag/`.exe`) no
   servidor de produção — não recompile uma versão diferente.
2. Copie o `cash_auditor.exe` para o servidor de produção.
3. Configure `DATABASE_URL` apontando para o **PostgreSQL de produção**.
4. Instale como serviço (seção 3) e libere a porta no firewall.
5. Valide e configure a rotina de backup.

---

## 6. Solução de problemas

| Sintoma | Causa provável / solução |
|---|---|
| Porta 8000 em uso | Outro processo ocupa a porta — altere `CASH_AUDITOR_PORT`. |
| Outras máquinas não acessam | Inicie com `CASH_AUDITOR_HOST=0.0.0.0` e libere o firewall. |
| Antivírus bloqueia o `.exe` | Adicione exceção; o `.exe` do PyInstaller pode gerar falso positivo. |
| Dados sumiram após mover o `.exe` | O `cash_auditor.db` fica **ao lado** do `.exe`; mova os dois juntos (ou use PostgreSQL). |
