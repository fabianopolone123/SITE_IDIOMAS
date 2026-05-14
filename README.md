# SITE_IDIOMAS

Site Django para estudos de italiano com repeticao espacada.

## Documentacao para continuidade

Antes de alterar o projeto, leia:

```text
docs/PROJECT_CONTEXT.md
```

Esse arquivo documenta arquitetura, SRS, cards, importacao segura, deploy/VPS,
regras para preservar progresso dos usuarios e comandos de manutencao.

## Funcionalidades

- Cadastro simples com username, senha, nome completo, WhatsApp e email.
- Dashboard com revisoes vencidas, frases novas disponiveis e progresso diario.
- Cards de estudo com audio primeiro, depois texto, traducao e explicacao.
- Repeticao espacada com avaliacoes: Errei, Dificil, Bom e Facil.
- Limite flexivel de 20 frases novas por dia, com confirmacao para continuar.
- Baralho curado de frases em italiano com traducao e notas de estudo.

## Como rodar

```powershell
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py import_alice_phrases
python manage.py runserver 127.0.0.1:8002
```

Depois acesse:

```text
http://127.0.0.1:8002/
```

Para testar no celular na mesma rede, use o IP local do computador e rode:

```powershell
python manage.py runserver 0.0.0.0:8002
```

## Testes

```powershell
python manage.py test
python manage.py check
```

## Deploy automatico para o VPS

Depois de alterar o projeto local, rode no PowerShell:

```powershell
.\scripts\deploy_vps.ps1 -Message "Descreva a alteracao"
```

Ou clique duas vezes em `deploy_vps.bat` e informe a mensagem do commit quando pedir.

O script faz:

- testes locais;
- `python manage.py check`;
- commit das alteracoes;
- `git push origin main`;
- atualizacao do VPS em `/var/www/site_idiomas`;
- `migrate`, `import_alice_phrases`, `collectstatic`, `check`;
- restart do servico `site_idiomas`.

Ele usa por padrao:

```text
root@145.223.93.162
/var/www/site_idiomas
site_idiomas.service
```

## Atualizar cards em producao

Os cards ficam versionados em `studies/alice_deck.py`. O banco de producao guarda usuarios,
cadastros e progresso de revisao. Para atualizar a VPS sem apagar progresso:

```bash
git pull origin main
python manage.py migrate
python manage.py import_alice_phrases
```

Depois reinicie o servico do Django/Gunicorn/Uvicorn configurado na VPS.

O comando `import_alice_phrases` e incremental:

- cria cards novos;
- atualiza traducao, explicacao, ordem e texto de cards existentes;
- preserva usuarios;
- preserva `ReviewState`, intervalos, revisoes e historico de progresso.

Nao use em producao:

```bash
python manage.py import_alice_phrases --reset
```

`--reset` apaga os cards e tambem apaga o progresso ligado a eles por cascata.

Ao adicionar novos cards em `studies/alice_deck.py`, coloque sempre no final da lista
`ALICE_CARDS`. Nao reordene cards antigos. As chaves estaveis sao geradas pela posicao atual
do baralho (`alice-0001`, `alice-0002`, etc.) e sao usadas para preservar progresso mesmo
quando corrigimos texto, traducao ou explicacao.

## Variaveis de ambiente para producao

Veja `.env.example`.

Obrigatorias/recomendadas na VPS:

```bash
DJANGO_SECRET_KEY=uma-chave-secreta-forte
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=seudominio.com,www.seudominio.com
DJANGO_CSRF_TRUSTED_ORIGINS=https://seudominio.com,https://www.seudominio.com
```

Para arquivos estaticos:

```bash
python manage.py collectstatic
```
