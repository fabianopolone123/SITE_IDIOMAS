TECH_SOURCE_TITLE = 'Entrevista de TI em italiano'
TECH_CHAPTER = 'Tecnologia e entrevista'


TECH_TOPICS = [
    {
        'it': 'requisiti',
        'pt': 'requisitos',
        'action_it': 'capire le aspettative del cliente',
        'action_pt': 'entender as expectativas do cliente',
        'problem_it': 'un requisito poco chiaro',
        'problem_pt': 'um requisito pouco claro',
        'result_it': 'evitare lavoro inutile',
        'result_pt': 'evitar trabalho inútil',
        'context': 'Use quando falar de levantamento de requisitos, alinhamento com produto ou conversa com cliente.',
    },
    {
        'it': 'architettura',
        'pt': 'arquitetura',
        'action_it': 'organizzare i componenti del sistema',
        'action_pt': 'organizar os componentes do sistema',
        'problem_it': 'un sistema difficile da mantenere',
        'problem_pt': 'um sistema difícil de manter',
        'result_it': 'rendere il progetto più stabile',
        'result_pt': 'tornar o projeto mais estável',
        'context': 'Use para explicar decisões técnicas, separação de responsabilidades e visão geral do sistema.',
    },
    {
        'it': 'database',
        'pt': 'banco de dados',
        'action_it': 'salvare e consultare i dati in modo sicuro',
        'action_pt': 'salvar e consultar dados com segurança',
        'problem_it': 'una query lenta',
        'problem_pt': 'uma consulta lenta',
        'result_it': 'migliorare il tempo di risposta',
        'result_pt': 'melhorar o tempo de resposta',
        'context': 'Use quando falar de SQL, modelagem, índices, consultas e integridade dos dados.',
    },
    {
        'it': 'API',
        'pt': 'API',
        'action_it': 'collegare servizi diversi',
        'action_pt': 'conectar serviços diferentes',
        'problem_it': 'una risposta non documentata',
        'problem_pt': 'uma resposta não documentada',
        'result_it': 'integrare il front-end con il back-end',
        'result_pt': 'integrar o front-end com o back-end',
        'context': 'Use em entrevistas sobre endpoints, contratos, autenticação, payloads e integrações.',
    },
    {
        'it': 'debug',
        'pt': 'depuração',
        'action_it': 'trovare la causa reale di un errore',
        'action_pt': 'encontrar a causa real de um erro',
        'problem_it': 'un bug intermittente',
        'problem_pt': 'um bug intermitente',
        'result_it': 'risolvere il problema senza cambiare codice inutile',
        'result_pt': 'resolver o problema sem mudar código desnecessário',
        'context': 'Use para mostrar método: reproduzir, ler logs, isolar causa e validar a correção.',
    },
    {
        'it': 'test automatici',
        'pt': 'testes automáticos',
        'action_it': 'verificare il comportamento del codice',
        'action_pt': 'verificar o comportamento do código',
        'problem_it': 'una regressione dopo una modifica',
        'problem_pt': 'uma regressão depois de uma alteração',
        'result_it': 'ridurre il rischio prima del rilascio',
        'result_pt': 'reduzir o risco antes da publicação',
        'context': 'Use para falar de testes unitários, integração, regressão e confiança no deploy.',
    },
    {
        'it': 'versionamento',
        'pt': 'versionamento',
        'action_it': 'collaborare sul codice con Git',
        'action_pt': 'colaborar no código com Git',
        'problem_it': 'un conflitto tra due modifiche',
        'problem_pt': 'um conflito entre duas alterações',
        'result_it': 'mantenere una cronologia chiara',
        'result_pt': 'manter um histórico claro',
        'context': 'Use para falar de branches, commits, pull requests, revisão e organização do trabalho.',
    },
    {
        'it': 'deploy',
        'pt': 'implantação',
        'action_it': 'pubblicare una nuova versione in produzione',
        'action_pt': 'publicar uma nova versão em produção',
        'problem_it': 'un rilascio con rischio alto',
        'problem_pt': 'uma publicação com risco alto',
        'result_it': 'mettere online la funzionalità senza fermare il servizio',
        'result_pt': 'colocar a funcionalidade online sem parar o serviço',
        'context': 'Use para falar de produção, rollback, migrações, servidor, Nginx, systemd ou CI/CD.',
    },
    {
        'it': 'sicurezza',
        'pt': 'segurança',
        'action_it': 'proteggere dati e accessi',
        'action_pt': 'proteger dados e acessos',
        'problem_it': 'un accesso non autorizzato',
        'problem_pt': 'um acesso não autorizado',
        'result_it': 'ridurre la superficie di attacco',
        'result_pt': 'reduzir a superfície de ataque',
        'context': 'Use para falar de autenticação, autorização, senhas, permissões e dados sensíveis.',
    },
    {
        'it': 'prestazioni',
        'pt': 'desempenho',
        'action_it': 'rendere l applicazione più veloce',
        'action_pt': 'tornar a aplicação mais rápida',
        'problem_it': 'una pagina troppo lenta',
        'problem_pt': 'uma página lenta demais',
        'result_it': 'migliorare l esperienza dell utente',
        'result_pt': 'melhorar a experiência do usuário',
        'context': 'Use para falar de cache, consultas, carregamento, latência e métricas.',
    },
    {
        'it': 'cache',
        'pt': 'cache',
        'action_it': 'evitare calcoli ripetuti',
        'action_pt': 'evitar cálculos repetidos',
        'problem_it': 'un dato letto troppe volte',
        'problem_pt': 'um dado lido vezes demais',
        'result_it': 'diminuire il carico sul server',
        'result_pt': 'diminuir a carga no servidor',
        'context': 'Use quando explicar otimização, invalidação, memória, resposta rápida e trade-offs.',
    },
    {
        'it': 'log',
        'pt': 'log',
        'action_it': 'capire cosa è successo nel sistema',
        'action_pt': 'entender o que aconteceu no sistema',
        'problem_it': 'un errore difficile da riprodurre',
        'problem_pt': 'um erro difícil de reproduzir',
        'result_it': 'diagnosticare il problema più rapidamente',
        'result_pt': 'diagnosticar o problema mais rapidamente',
        'context': 'Use para mostrar análise de incidentes, observabilidade e investigação em produção.',
    },
    {
        'it': 'monitoraggio',
        'pt': 'monitoramento',
        'action_it': 'osservare la salute dell applicazione',
        'action_pt': 'observar a saúde da aplicação',
        'problem_it': 'un servizio instabile',
        'problem_pt': 'um serviço instável',
        'result_it': 'reagire prima che l utente venga colpito',
        'result_pt': 'reagir antes que o usuário seja afetado',
        'context': 'Use para falar de métricas, alertas, disponibilidade e acompanhamento em produção.',
    },
    {
        'it': 'documentazione',
        'pt': 'documentação',
        'action_it': 'rendere le decisioni comprensibili al team',
        'action_pt': 'tornar as decisões compreensíveis para a equipe',
        'problem_it': 'una regola conosciuta solo da una persona',
        'problem_pt': 'uma regra conhecida por apenas uma pessoa',
        'result_it': 'facilitare manutenzione e onboarding',
        'result_pt': 'facilitar manutenção e entrada de novos membros',
        'context': 'Use para falar de README, comentários úteis, decisões técnicas e transferência de conhecimento.',
    },
    {
        'it': 'comunicazione',
        'pt': 'comunicação',
        'action_it': 'spiegare un problema tecnico in modo semplice',
        'action_pt': 'explicar um problema técnico de forma simples',
        'problem_it': 'una decisione fraintesa dal team',
        'problem_pt': 'uma decisão mal compreendida pela equipe',
        'result_it': 'allineare persone tecniche e non tecniche',
        'result_pt': 'alinhar pessoas técnicas e não técnicas',
        'context': 'Use para responder perguntas comportamentais sobre clareza, colaboração e negociação.',
    },
    {
        'it': 'priorità',
        'pt': 'prioridade',
        'action_it': 'scegliere cosa fare prima',
        'action_pt': 'escolher o que fazer primeiro',
        'problem_it': 'molte richieste nello stesso momento',
        'problem_pt': 'muitas demandas ao mesmo tempo',
        'result_it': 'consegnare valore più rapidamente',
        'result_pt': 'entregar valor mais rapidamente',
        'context': 'Use para falar de organização, impacto, urgência, escopo e comunicação com stakeholders.',
    },
    {
        'it': 'metodologia agile',
        'pt': 'metodologia ágil',
        'action_it': 'dividere il lavoro in piccoli incrementi',
        'action_pt': 'dividir o trabalho em pequenos incrementos',
        'problem_it': 'un progetto con requisiti che cambiano',
        'problem_pt': 'um projeto com requisitos que mudam',
        'result_it': 'adattarsi senza perdere il controllo',
        'result_pt': 'adaptar-se sem perder o controle',
        'context': 'Use para falar de sprints, feedback, retrospectiva, planejamento e entrega incremental.',
    },
    {
        'it': 'cloud',
        'pt': 'nuvem',
        'action_it': 'usare risorse scalabili',
        'action_pt': 'usar recursos escaláveis',
        'problem_it': 'un carico variabile',
        'problem_pt': 'uma carga variável',
        'result_it': 'aumentare capacità quando serve',
        'result_pt': 'aumentar capacidade quando necessário',
        'context': 'Use para falar de VPS, AWS, deploy, armazenamento, escalabilidade e custos.',
    },
    {
        'it': 'container',
        'pt': 'contêiner',
        'action_it': 'eseguire l applicazione in un ambiente isolato',
        'action_pt': 'executar a aplicação em um ambiente isolado',
        'problem_it': 'differenze tra sviluppo e produzione',
        'problem_pt': 'diferenças entre desenvolvimento e produção',
        'result_it': 'rendere il deploy più prevedibile',
        'result_pt': 'tornar a implantação mais previsível',
        'context': 'Use para falar de Docker, ambiente, dependências e consistência entre máquinas.',
    },
    {
        'it': 'messaggistica',
        'pt': 'mensageria',
        'action_it': 'processare attività in modo asincrono',
        'action_pt': 'processar atividades de forma assíncrona',
        'problem_it': 'un compito che richiede molto tempo',
        'problem_pt': 'uma tarefa que demora muito',
        'result_it': 'non bloccare la richiesta dell utente',
        'result_pt': 'não bloquear a requisição do usuário',
        'context': 'Use para falar de filas, workers, eventos, processamento em segundo plano e resiliência.',
    },
    {
        'it': 'autenticazione',
        'pt': 'autenticação',
        'action_it': 'verificare l identità dell utente',
        'action_pt': 'verificar a identidade do usuário',
        'problem_it': 'una sessione non valida',
        'problem_pt': 'uma sessão inválida',
        'result_it': 'permettere accesso solo a chi deve entrare',
        'result_pt': 'permitir acesso apenas a quem deve entrar',
        'context': 'Use para diferenciar login, sessão, token, autorização e proteção de rotas.',
    },
    {
        'it': 'codice pulito',
        'pt': 'código limpo',
        'action_it': 'scrivere funzioni chiare e piccole',
        'action_pt': 'escrever funções claras e pequenas',
        'problem_it': 'una funzione troppo grande',
        'problem_pt': 'uma função grande demais',
        'result_it': 'facilitare test e manutenzione',
        'result_pt': 'facilitar testes e manutenção',
        'context': 'Use para falar de legibilidade, nomes, simplicidade e manutenção por outras pessoas.',
    },
    {
        'it': 'revisione del codice',
        'pt': 'revisão de código',
        'action_it': 'trovare rischi prima del merge',
        'action_pt': 'encontrar riscos antes do merge',
        'problem_it': 'una modifica con effetto collaterale',
        'problem_pt': 'uma alteração com efeito colateral',
        'result_it': 'migliorare la qualità senza bloccare il team',
        'result_pt': 'melhorar a qualidade sem bloquear a equipe',
        'context': 'Use para falar de pull request, feedback, padrões, bugs e colaboração técnica.',
    },
    {
        'it': 'leadership tecnica',
        'pt': 'liderança técnica',
        'action_it': 'aiutare il team a prendere buone decisioni',
        'action_pt': 'ajudar a equipe a tomar boas decisões',
        'problem_it': 'un disaccordo tecnico',
        'problem_pt': 'uma discordância técnica',
        'result_it': 'arrivare a una soluzione condivisa',
        'result_pt': 'chegar a uma solução compartilhada',
        'context': 'Use para entrevistas sênior, mentoria, tomada de decisão e influência sem autoridade formal.',
    },
    {
        'it': 'apprendimento continuo',
        'pt': 'aprendizado contínuo',
        'action_it': 'imparare nuove tecnologie con metodo',
        'action_pt': 'aprender novas tecnologias com método',
        'problem_it': 'una tecnologia che non conosco ancora',
        'problem_pt': 'uma tecnologia que ainda não conheço',
        'result_it': 'diventare produttivo in poco tempo',
        'result_pt': 'tornar-me produtivo em pouco tempo',
        'context': 'Use para mostrar humildade, autonomia, estudo estruturado e adaptação.',
    },
]


def build_tech_note(topic, mode):
    common = (
        'Vocabulário palavra por palavra:\n'
        f"- {topic['it']} = {topic['pt']}\n"
        '- ho esperienza con = tenho experiência com\n'
        '- durante un progetto = durante um projeto\n'
        '- quando c è un problema = quando existe um problema\n'
        '- posso spiegare = posso explicar\n'
        f"- {topic['action_it']} = {topic['action_pt']}\n"
        f"- {topic['problem_it']} = {topic['problem_pt']}\n"
        f"- {topic['result_it']} = {topic['result_pt']}\n"
    )
    usage = (
        'Uso em contextos diferentes:\n'
        f"- Contexto técnico: use {topic['it']} para explicar decisões, ferramentas e responsabilidades.\n"
        f"- Contexto comportamental: conecte {topic['it']} com colaboração, clareza e impacto no time.\n"
        f"- Contexto de entrevista: responda com situação, ação e resultado; evite só listar tecnologia.\n"
    )
    focus = {
        'topic': 'Foco: reconhecer o termo principal e pronunciá-lo com segurança.',
        'experience': 'Foco: apresentar experiência de forma direta, sem parecer genérico.',
        'action': 'Foco: explicar o que você faz na prática usando esse tema.',
        'problem': 'Foco: explicar como você identifica problema antes de propor solução.',
        'result': 'Foco: ligar a tecnologia a resultado claro para o negócio ou para o usuário.',
        'project': 'Foco: contar uma situação real de projeto e mostrar sua contribuição.',
        'team': 'Foco: mostrar colaboração técnica e comunicação com o time.',
        'interview': 'Foco: transformar o tema em resposta pronta para entrevista.',
    }[mode]
    return f'{common}\n{usage}\n{focus}\n{topic["context"]}'


TECH_CARD_PATTERNS = [
    (
        "Conosco {it}.",
        "Conheço {pt}.",
        'topic',
    ),
    (
        "Ho esperienza con {it}.",
        "Tenho experiência com {pt}.",
        'experience',
    ),
    (
        "Uso {it} per {action_it}.",
        "Uso {pt} para {action_pt}.",
        'action',
    ),
    (
        "Il problema era {problem_it}.",
        "O problema era {problem_pt}.",
        'problem',
    ),
    (
        "La soluzione ha aiutato a {result_it}.",
        "A solução ajudou a {result_pt}.",
        'result',
    ),
    (
        "In un progetto, ho lavorato su {it}.",
        "Em um projeto, trabalhei com {pt}.",
        'project',
    ),
    (
        "Ho spiegato {it} al team.",
        "Expliquei {pt} para a equipe.",
        'team',
    ),
    (
        "Posso fare un esempio su {it}.",
        "Posso dar um exemplo sobre {pt}.",
        'interview',
    ),
]


def iter_tech_cards(limit=None):
    cards = []
    for topic in TECH_TOPICS:
        for italian_pattern, portuguese_pattern, mode in TECH_CARD_PATTERNS:
            cards.append(
                (
                    italian_pattern.format(**topic),
                    portuguese_pattern.format(**topic),
                    mode,
                )
            )

    selected = cards if limit is None else cards[:limit]
    for index, (text, translation, mode) in enumerate(selected, start=1):
        topic = TECH_TOPICS[(index - 1) // len(TECH_CARD_PATTERNS)]
        yield {
            'deck_key': f'tech-{index:04d}',
            'order': 10000 + index,
            'italian_text': text,
            'portuguese_text': translation,
            'study_note': build_tech_note(topic, mode),
            'source_title': TECH_SOURCE_TITLE,
            'chapter': TECH_CHAPTER,
        }
