# Contexto do Projeto SITE_IDIOMAS

Este documento existe para preservar contexto do projeto entre sessoes do Codex.
Leia este arquivo antes de fazer alteracoes relevantes.

## Objetivo

SITE_IDIOMAS e um site Django para estudo de italiano com repeticao espacada.
O foco atual e ensinar com frases curtas inspiradas em Alice no Pais das Maravilhas.

Fluxo principal do aluno:

1. Cria conta simples.
2. Entra no dashboard.
3. Clica em Comecar estudos.
4. Primeiro escuta apenas o audio da frase.
5. Depois revela o texto italiano.
6. Depois revela traducao e explicacao.
7. Avalia com Errei, Dificil, Bom ou Facil.
8. O sistema agenda a proxima revisao.

## Stack

- Python 3.10 usado no ambiente local atual.
- Django 5.2.12.
- SQLite local em desenvolvimento.
- Cards versionados no codigo em `studies/alice_deck.py`.
- Audio por Web Speech API no navegador, em `static/studies/speech.js`.

## Estrutura principal

- `config/settings.py`: configuracao Django.
- `config/urls.py`: inclui rotas de `studies`.
- `studies/models.py`: modelos de perfil, frases e progresso SRS.
- `studies/views.py`: cadastro, login, dashboard, estudo, revisao e limite de cards novos.
- `studies/forms.py`: formularios de cadastro/login.
- `studies/van_pdf.py`: geracao do PDF da autorizacao da van.
- `studies/alice_deck.py`: baralho curado versionado no Git.
- `studies/management/commands/import_alice_phrases.py`: importa/atualiza cards no banco.
- `templates/studies/study.html`: fluxo do card audio -> texto -> resposta.
- `static/studies/speech.js`: leitura em voz alta no navegador.
- `static/inscricao_van/van.css`: estilos da area de inscricao da van.
- `static/inscricao_van/panfleto.jpeg`: panfleto usado como fundo/arte da inscricao.
- `static/studies/styles.css`: layout responsivo.
- `docs/PROJECT_CONTEXT.md`: este arquivo.

## Modelos

### Profile

Ligado 1-para-1 com `User`.

Campos:

- `full_name`
- `whatsapp`

O email fica no `User` padrao do Django.

### StudyPhrase

Representa um card/frase.

Campos importantes:

- `deck_key`: chave estavel do card, exemplo `alice-0001`.
- `order`: ordem de exibicao.
- `italian_text`: frase em italiano.
- `portuguese_text`: traducao.
- `study_note`: explicacao/dica.
- `chapter`: contexto do baralho.

Regra critica: `deck_key` e o identificador seguro para preservar progresso em producao.
Nao dependa do texto italiano como identificador permanente, porque o texto pode ser corrigido.

### ReviewState

Representa o progresso de um usuario em um card.

Campos importantes:

- `user`
- `phrase`
- `first_seen_at`: quando o card entrou pela primeira vez para o usuario.
- `due_at`: proxima revisao.
- `interval_days`: intervalo atual.
- `ease_factor`: fator de facilidade.
- `repetitions`: numero de avaliacoes.
- `lapses`: numero de erros.
- `last_grade`
- `last_reviewed_at`

`unique_together = ['user', 'phrase']` impede progresso duplicado para o mesmo card.

### VanRegistration

Representa uma inscricao/autorizacao da van no caminho `/inscricao_van/`.

Campos importantes:

- `public_id`: UUID usado nas URLs publicas sem expor ID sequencial.
- dados do responsavel: nome, RG, CPF, WhatsApp e email.
- dados do menor: nome, nascimento e RG/CPF se houver.
- `transport_by`: texto usado no termo, padrao `van`.
- `signed_term`: PDF assinado enviado pela pessoa.
- `status`: `pending_signature` ou `signed_received`.

Quando `signed_term` e enviado, o model marca status como `signed_received`.

## Algoritmo SRS atual

Implementado em `ReviewState.schedule`.

Notas:

- `Errei` (`again`): volta em 2 minutos, zera intervalo para 0, reduz facilidade.
- `Dificil` (`hard`): primeira vez volta em 1 dia; depois cresce pouco.
- `Bom` (`good`): primeira vez volta em 2 dias; depois multiplica pelo `ease_factor`.
- `Facil` (`easy`): primeira vez volta em 4 dias; depois cresce mais rapido.

Esta e uma implementacao simples, inspirada em repeticao espacada, nao FSRS completo.

## Limite de cards novos

Constante em `studies/views.py`:

```python
NEW_CARDS_BLOCK_SIZE = 20
```

Comportamento:

1. Revisoes vencidas sempre aparecem primeiro.
2. Se nao houver revisao vencida, o app tenta liberar card novo.
3. A cada 20 cards novos iniciados no mesmo dia, aparece uma tela de aviso.
4. O aluno pode parar ou clicar em "Quero continuar mesmo assim".
5. Se continuar, libera outro bloco de 20.
6. Aos 40, 60, 80 etc., pergunta novamente.

A contagem usa `ReviewState.first_seen_at__date=timezone.localdate()`.

## Fluxo do card

View: `study`.

Estados por querystring:

- `?stage=audio`: estado inicial, mostra apenas botao de audio.
- `?stage=text`: mostra texto italiano e botao Play.
- `?stage=answer`: mostra traducao, explicacao e botoes de avaliacao.

O parametro antigo `?reveal=1` ainda e aceito e mapeado para `stage=answer`.

## Area `/inscricao_van/`

Objetivo: formulario de autorizacao para viagem de menor de idade para o evento
"Passaporte: Sua Identidade em Alta Definicao".

Rotas:

- `/inscricao_van/`: landing com panfleto e botoes.
- `/inscricao_van/fazer/`: cria a inscricao.
- `/inscricao_van/termo/<uuid>/`: baixa termo e envia termo assinado.
- `/inscricao_van/termo/<uuid>/baixar/`: gera PDF A4 do termo.
- `/inscricao_van/consultar/`: consulta por CPF do responsavel + nascimento do menor.
- `/inscricao_van/admin/`: login simples com senha `1580`.
- `/inscricao_van/admin/dashboard/`: relatorio de inscricoes.
- `/inscricao_van/admin/termos.zip`: baixa todos os termos assinados.

O PDF e gerado com ReportLab em `studies/van_pdf.py`.

Uploads ficam em:

```text
media/inscricao_van/termos_assinados/
```

Em producao, garantir que Nginx sirva esse caminho de media se o admin precisar baixar
arquivos diretamente por URL ou se houver links futuros.

## Audio e pronuncia

Arquivo: `static/studies/speech.js`.

Implementacao atual:

- Usa `window.speechSynthesis`.
- Prefere voz `it-*` se o navegador tiver.
- Se nao houver voz italiana exposta, usa `lang='it-IT'` e deixa o navegador decidir.
- Em mobile, o audio so inicia apos clique real do usuario, por limitacao dos navegadores.
- O script tenta recarregar lista de vozes algumas vezes porque mobile pode carregar vozes com atraso.

Limitacao: qualidade/sotaque depende do navegador e do sistema operacional. Para producao com voz
consistente, considerar gerar MP3 por card com TTS externo e salvar caminho do audio no banco ou storage.

## Regras para adicionar cards

Arquivo principal:

```text
studies/alice_deck.py
```

Adicionar novos cards sempre no final da lista `ALICE_CARDS`.

Formato atual:

```python
('Frase italiana.', 'Traducao em portugues.', 'explicacao especifica da frase.'),
```

Nao reordenar cards antigos. O importador gera chaves estaveis pela posicao atual:

- `alice-0001`
- `alice-0002`
- `alice-0003`

Se reordenar cards antigos, uma chave pode passar a apontar para outro card e isso bagunca progresso.

Pode corrigir texto/traducao/explicacao de card existente, desde que ele continue na mesma posicao.
O importador atualiza o card existente pelo `deck_key` e preserva `ReviewState`.

## Importacao segura dos cards

Comando:

```bash
python manage.py import_alice_phrases
```

Esse comando e incremental e seguro para producao:

- cria cards novos;
- atualiza cards existentes por `deck_key`;
- migra cards antigos sem `deck_key` procurando pelo texto italiano;
- preserva usuarios;
- preserva progresso e revisoes.

Nao usar em producao:

```bash
python manage.py import_alice_phrases --reset
```

`--reset` apaga `StudyPhrase`. Como `ReviewState.phrase` tem `on_delete=CASCADE`, isso apaga
tambem progresso e revisoes dos usuarios. `--reset` e apenas para desenvolvimento local controlado.

## Fluxo de deploy/VPS

Quando houver alteracao de codigo ou novos cards:

```bash
git pull origin main
python manage.py migrate
python manage.py import_alice_phrases
python manage.py check
```

Depois reiniciar o servico da aplicacao configurado na VPS, por exemplo Gunicorn/Uvicorn/systemd.

Nao subir `db.sqlite3` para o Git. O banco da VPS deve ser persistente e independente.

Se este projeto for colocado no mesmo dominio de outros projetos, por exemplo
`fabianopolone.com.br/inscricao_van/`, nao crie um `location /` para ele. Use apenas:

```nginx
location /inscricao_van/ {
    proxy_pass http://unix:/run/site-idiomas.sock;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}

location /static/inscricao_van/ {
    alias /var/www/site_idiomas/staticfiles/inscricao_van/;
}

location /media/inscricao_van/ {
    alias /var/www/site_idiomas/media/inscricao_van/;
}
```

Isso evita mexer nos outros tres projetos ja em producao no mesmo Nginx.

## Git

Repositorio remoto:

```text
https://github.com/fabianopolone123/SITE_IDIOMAS.git
```

Branch principal:

```text
main
```

Regra combinada com o usuario:

- Toda alteracao feita pelo Codex deve virar commit com mensagem clara.
- Depois do commit, dar `git push`.

Antes de commitar:

```bash
python manage.py test
python manage.py check
git status --short
```

## Arquivos ignorados

`.gitignore` exclui:

- `db.sqlite3`
- PDFs locais
- imagem original local `WhatsApp Image*.jpeg`
- caches Python
- ambientes virtuais
- `.env`
- arquivos de editor/OS

Isso e proposital. O PDF local nao e necessario para producao porque o baralho curado esta no codigo.

## Comandos locais comuns

Rodar local:

```powershell
python manage.py migrate
python manage.py import_alice_phrases
python manage.py runserver 127.0.0.1:8002
```

Rodar para celular na mesma rede:

```powershell
python manage.py runserver 0.0.0.0:8002
```

URL local:

```text
http://127.0.0.1:8002/
```

URL na rede local atual usada em desenvolvimento:

```text
http://192.168.15.23:8002/
```

Essa URL depende do IP da maquina e pode mudar.

## Configuracoes importantes

`config/settings.py` atualmente le configuracoes sensiveis por variaveis de ambiente:

- `DJANGO_SECRET_KEY`
- `DJANGO_DEBUG`
- `DJANGO_ALLOWED_HOSTS`
- `DJANGO_CSRF_TRUSTED_ORIGINS`

Defaults locais:

- `DJANGO_DEBUG` fica `True` quando ausente.
- `DJANGO_ALLOWED_HOSTS` aceita `127.0.0.1`, `localhost` e `192.168.15.23`.
- `STATIC_ROOT = BASE_DIR / 'staticfiles'`.

Tambem tem:

- `AUTH_PASSWORD_VALIDATORS = []`
- `LANGUAGE_CODE = 'pt-br'`
- `TIME_ZONE = 'America/Sao_Paulo'`

Antes de colocar online de verdade, ajustar:

- `DJANGO_DEBUG=False`
- `DJANGO_SECRET_KEY` forte e exclusivo
- `DJANGO_ALLOWED_HOSTS` com dominio/IP real
- `DJANGO_CSRF_TRUSTED_ORIGINS` com `https://dominio`
- banco de producao se nao for usar SQLite
- arquivos estaticos com `collectstatic`
- HTTPS/proxy reverso

## Testes existentes

Arquivo:

```text
studies/tests.py
```

Cobre:

- agendamento `Bom`;
- agendamento `Errei`;
- cadastro cria perfil e loga;
- primeiro estudo cria `ReviewState`;
- pausa apos 20 cards novos no dia;
- bypass da pausa com confirmacao;
- importacao incremental preserva historico;
- importacao por `deck_key` preserva historico mesmo se texto mudar.
- criacao de inscricao da van;
- download do termo em PDF;
- upload do termo assinado;
- consulta de inscricao;
- login do dashboard da van.

## Estado atual do baralho

No momento deste documento, o baralho tem 469 cards.

Para conferir:

```bash
python manage.py shell -c "from studies.alice_deck import ALICE_CARDS; print(len(ALICE_CARDS))"
python manage.py shell -c "from studies.models import StudyPhrase; print(StudyPhrase.objects.count())"
```

O segundo comando depende do banco ja ter recebido `import_alice_phrases`.

## Decisoes importantes ja tomadas

- Cards ficam no Git, nao em fixtures ou no banco local.
- Banco de producao recebe cards via comando incremental.
- `deck_key` protege progresso quando corrigimos cards.
- O aluno ve audio antes do texto para treinar escuta.
- Limite de 20 cards novos por dia e flexivel, nao bloqueio absoluto.
- Revisoess vencidas sempre tem prioridade sobre cards novos.
- Audio por Web Speech API e suficiente para MVP.
- MP3/TTS externo fica para fase posterior se precisar de voz consistente.
