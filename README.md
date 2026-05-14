# SITE_IDIOMAS

Site Django para estudos de italiano com repeticao espacada.

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
