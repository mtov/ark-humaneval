# HumanEval com o Ark atual

Executa as 164 tarefas fornecidas neste projeto usando o código e a configuração
do Ark em `../ark`. Compatível com macOS e Linux, com Python 3.11 ou superior.

## Como rodar o benchmark

Os comandos abaixo devem ser executados no terminal, na raiz deste projeto.
O projeto espera esta organização de diretórios:

```text
ark-project/
├── ark/              # Seu Ark atual, com config/ e .venv/
└── human-eval-all/    # Este projeto
```

### 1. Entre na pasta do projeto

Nesta máquina:

```bash
cd /Users/mtov/ark-project/human-eval-all
```

O executor usa automaticamente `../ark/.venv/bin/python`. Você não precisa
ativar o ambiente virtual nem instalar uma segunda cópia do Ark neste projeto.
Se o ambiente do Ark ainda não existir, siga a seção [Preparação do ambiente](#preparação-do-ambiente).

### 2. Configure a chave no terminal

Na configuração atual, a chave é lida de `OPENAI_API_KEY`:

```bash
export OPENAI_API_KEY="sua-chave"
```

Substitua `sua-chave` pela sua chave real. O comando vale para esse terminal e
seus processos; execute-o novamente se abrir outro terminal para iniciar o benchmark.

O modelo e o endpoint são os definidos em `../ark/config/config.json`.
O prompt de sistema vem de `../ark/config/system_prompt.txt`. O executor copia
essa configuração no início de cada rodada; ajuste-a antes de começar.

### 3. Confira o ambiente

```bash
../ark/.venv/bin/python run_benchmark.py --check
```

A saída deve identificar seu Ark, o Python, o modelo configurado, **164 tarefas**
e a chave como **presente**. Este comando não faz chamadas à API nem cria
resultados. Ele valida os arquivos e a configuração local, mas não confirma a
validade da chave ou o acesso ao modelo na API.

### 4. Rode uma tarefa como piloto

```bash
../ark/.venv/bin/python run_benchmark.py --run-name piloto-real --task he_000
```

Este comando já faz chamadas reais ao modelo. Aguarde o resultado da tarefa.
O esperado para um piloto bem-sucedido é `PASS` e o resumo `1/1 PASS`.
Os resultados ficam em `results/piloto-real/`.

Se aparecer `ERROR`, `FAIL` ou `TIMEOUT`, consulte o CSV e os arquivos em
`results/piloto-real/traces/` antes de iniciar a rodada completa. Para repetir
esse piloto após uma falha já registrada, use outro nome, como `piloto-real-02`.

### 5. Execute as 164 tarefas

```bash
../ark/.venv/bin/python run_benchmark.py --run-name avaliacao-01
```

**Esse é o comando para executar o benchmark completo.** Sem `--task` e sem
`--limit`, ele seleciona as 164 tarefas, em sequência, de `he_000` a `he_163`.
Não é necessário responder às confirmações de edição: o executor fornece `y`
automaticamente. `ARK_AUTO_APPROVE` não é necessário.

O terminal mostra cada tarefa iniciada e seu resultado ao terminar. Os logs
detalhados são salvos após a execução da tarefa; não são transmitidos ao vivo.
Ao final, o terminal informa a quantidade e a proporção de tarefas com `PASS`.

A rodada completa usa `results/avaliacao-01/`, separada do piloto. Para consultar
o CSV em outro terminal, entre na raiz deste projeto e execute:

```bash
cat results/avaliacao-01/results.csv
```

O código final de cada tarefa fica em `results/avaliacao-01/workspaces/` e os
logs em `results/avaliacao-01/traces/`.

### 6. Interrompa ou retome, se necessário

Para interromper, pressione **Ctrl+C** no terminal da execução. Para retomar,
configure a chave no terminal e repita **o mesmo comando, com as mesmas opções**:

```bash
../ark/.venv/bin/python run_benchmark.py --run-name avaliacao-01
```

As tarefas já registradas no CSV, incluindo falhas e timeouts, são ignoradas.
A tarefa interrompida por Ctrl+C fica pendente e será executada novamente.

Para fazer uma nova avaliação do zero, escolha outro nome:

```bash
../ark/.venv/bin/python run_benchmark.py --run-name avaliacao-02
```

Mantenha o Ark, as tarefas e as opções inalterados para retomar a mesma rodada.
Se você alterar o código/configuração do Ark, o executor, as tarefas, o ambiente
ou os limites de tempo, use um novo nome de rodada.

## Preparação do ambiente

**Se `../ark/.venv/bin/python` já funciona, não é necessário recriar o ambiente.**
Caso ainda não exista, crie-o usando Python 3.11 ou superior, a partir da raiz
deste projeto:

```bash
python3 -m venv ../ark/.venv
../ark/.venv/bin/python -m pip install -r ../ark/requirements.txt
```

As tarefas já estão fornecidas. Você não precisa gerar os workspaces ou instalar
o pacote `human_eval`.

## Outras opções de execução

```bash
# Executar somente as primeiras dez tarefas
../ark/.venv/bin/python run_benchmark.py --run-name piloto-10 --limit 10

# Selecionar tarefas específicas
../ark/.venv/bin/python run_benchmark.py --run-name selecao --task he_000 --task he_065

# Aumentar os limites de tempo em uma nova rodada
../ark/.venv/bin/python run_benchmark.py --run-name avaliacao-longa --timeout 3600 --test-timeout 60

# Conferir outro checkout ou ambiente Python
python3 run_benchmark.py --ark-dir /caminho/ark --python /caminho/venv/bin/python --check

# Consultar todas as opções
../ark/.venv/bin/python run_benchmark.py --help
```

| Opção | Função | Padrão |
| --- | --- | --- |
| `--run-name` | Nome da rodada; repita-o para retomar | Nome único com data/hora UTC |
| `--task` | Executa uma tarefa; pode ser repetido | Todas as tarefas |
| `--limit` | Seleciona somente as primeiras N tarefas | Sem limite |
| `--timeout` | Limite total do processo do Ark por tarefa, em segundos | 1800 |
| `--test-timeout` | Limite da avaliação externa por tarefa, em segundos | 30 |
| `--ark-dir` | Diretório do código/configuração do Ark | `../ark` |
| `--python` | Executável Python para o Ark e a avaliação | `<ark-dir>/.venv/bin/python` |
| `--check` | Verifica o ambiente sem chamar a API | Desativado |

O timeout de cada requisição ao modelo continua sendo o definido no Ark.
`--timeout` limita o tempo de **toda a execução do Ark na tarefa**, incluindo
requisições e testes internos. Um timeout ou Ctrl+C encerra também os subprocessos
da tarefa.

## Se algo der errado

| Situação | Como proceder |
| --- | --- |
| `Defina a variável OPENAI_API_KEY` | Execute o `export` no mesmo terminal que iniciará o benchmark. |
| Python ausente ou ambiente inválido | Siga a preparação do ambiente ou informe `--python`. |
| Piloto com `ERROR` | Leia o log `.console.log` e o `.agent.log`, quando existir; confira a configuração do Ark e o acesso ao modelo. |
| Tarefa com `FAIL` | Leia o `.pytest.log`; a solução foi reprovada na avaliação externa. |
| Tarefa com `TIMEOUT` | Confira `error_type` no CSV para distinguir o limite do Ark do limite dos testes. |
| Aviso de que Ark, tarefas, ambiente ou opções mudaram | Use outro `--run-name` para iniciar uma rodada com os dados atuais. |
| Rodada já em execução | Aguarde ou interrompa o processo que usa aquele nome; use outro nome para uma rodada independente. |

## Isolamento e resultados

Cada rodada recebe uma cópia do código Python e dos dois arquivos de configuração
do Ark atual. Essa cópia executa em `results/<rodada>/runtime/`. Isso permite usar
a versão atual sem sobrescrever `../ark/ark-workspace` ou `../ark/agent_trace.log`.
Uma nova rodada captura novamente o conteúdo de `../ark`.

```text
.
├── run_benchmark.py
├── humaneval_official_workspaces/   # 164 tarefas originais
├── tests/test_benchmark.py          # Testes locais do executor, sem API
└── results/<rodada>/               # Gerado durante a execução
    ├── manifest.json
    ├── results.csv
    ├── traces/
    │   ├── he_000.console.log       # stdout e stderr do Ark
    │   ├── he_000.agent.log         # Trace interno, quando produzido
    │   └── he_000.pytest.log        # Avaliação externa, quando executada
    ├── workspaces/he_000/           # Código final com testes originais
    └── runtime/                    # Cópia executável do Ark
```

O manifesto registra caminhos, versões de Python/Pytest/cliente OpenAI, opções e
hashes do executor, código/configuração do Ark e arquivos das tarefas selecionadas.
Se esses dados mudarem, a retomada é recusada: escolha outro nome de rodada para
evitar misturar versões. A chave de API não é gravada pelo executor. A configuração
e os traces do Ark são copiados integralmente; eles podem conter dados do endpoint.

O CSV é gravado a cada tarefa e contém:

| Campo | Conteúdo |
| --- | --- |
| `task_id` | Identificador `he_000` a `he_163` |
| `status` | `PASS`, `FAIL`, `ERROR` ou `TIMEOUT` |
| `time_seconds` | Tempo do processo do Ark, sem a avaliação externa |
| `tokens` | Total reportado pelo Ark; vazio se indisponível |
| `turns` | Ações numeradas impressas no console |
| `error_type` | Categoria do erro, quando houver |
| `ark_exit_code` | Código de saída do processo do Ark |
| `test_exit_code` | Código de saída da avaliação externa, quando executada |

A gravação substitui o CSV inteiro de forma atômica. A retomada valida o
cabeçalho e cada registro; linhas incompletas, duplicadas ou inconsistentes
interrompem a execução com uma mensagem, sem pular tarefas silenciosamente.

`PASS` exige saída zero do Ark e aprovação na avaliação externa. Erros de
execução do Ark recebem `ERROR`; soluções reprovadas recebem `FAIL`. O comando
retorna zero quando a rodada termina, mesmo se houver tarefas reprovadas; confira
o resumo e o CSV. Erros do executor retornam 1; Ctrl+C retorna 130.

A avaliação externa usa uma cópia dos **testes originais** e o diretório `src/`
produzido pelo agente. Alterações do agente nos testes não entram nessa avaliação.
Os arquivos de entrada são conferidos contra os hashes do manifesto antes de
cada tarefa e depois de sua cópia. O Ark recebe essa cópia verificada. A execução
não modifica as tarefas fornecidas. Os testes ficam visíveis ao agente
durante a resolução; esta execução não representa uma avaliação com testes ocultos.

O empacotamento fornecido tinha imports incompletos nos testes de `he_032`,
`he_038` e `he_050`. Foram acrescentados os imports das funções auxiliares `poly`,
`encode_cyclic` e `encode_shift`, respectivamente. Os asserts foram preservados.

Para conferir manualmente uma solução salva, a partir da raiz do projeto:

```bash
cd results/avaliacao-01/workspaces/he_000
../../../../../ark/.venv/bin/python -m pytest -q -p no:cacheprovider tests/test_solution.py
```

## Testes do executor

```bash
../ark/.venv/bin/python -m pytest -q -p no:cacheprovider tests
```

Esses testes usam um agente simulado, sem chamadas ao modelo.
O relatório da revisão detalhada está em [VERIFICACAO.md](VERIFICACAO.md).

## Enviar os resultados ao GitHub

O `.gitignore` permite versionar os artefatos de cada rodada: `results.csv`,
`manifest.json`, `traces/` e `workspaces/`. As cópias de execução em `runtime/`,
os locks e os caches continuam excluídos.

Na criação inicial do repositório, `git add .` já inclui esses resultados.
Para enviar novas avaliações depois que o repositório tiver sido criado e
conectado ao GitHub, execute na raiz do projeto:

```bash
git add .gitignore results/
git status
git commit -m "Adiciona resultados das avaliações do Ark"
git push
```

## Limpeza realizada

Foram removidos o código duplicado `ark_latest/`, o ambiente Linux
`venv_ark_latest/`, os resultados/traces/workspaces antigos e seus ZIPs. O antigo
executor foi substituído por `run_benchmark.py`. O gerador de tarefas também foi
removido: as 164 tarefas já estão fornecidas e sua execução não depende do pacote
`human_eval`. Os repositórios Git internos das tarefas e caches dispensáveis foram
removidos; prompts, fontes e testes foram preservados.
