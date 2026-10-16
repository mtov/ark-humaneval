# Verificação antes da execução — 16/10/2026

O ambiente e a integração local estão verificados. A autenticação, a existência
do modelo no endpoint configurado e o resultado de uma execução real continuam
dependendo da API. Nenhuma chamada à API foi feita nesta revisão.

## Ambiente conferido

| Item | Resultado |
| --- | --- |
| Ark de origem | `/Users/mtov/ark-project/ark` |
| Python do benchmark | `../ark/.venv/bin/python`, versão 3.14.7 |
| Pytest | 9.1.1 |
| Cliente OpenAI | 2.49.0 |
| Modelo na configuração atual | `gpt-6-luna` |
| Endpoint na configuração atual | Padrão do cliente (`openai_base_url: null`) |
| Timeout por requisição no Ark | 600 segundos |
| Timeout total do Ark por tarefa | 1.800 segundos, ajustável com `--timeout` |
| Timeout da avaliação externa | 30 segundos, ajustável com `--test-timeout` |
| `OPENAI_API_KEY` no terminal da revisão | Ausente |

O executor também foi chamado a partir de outro diretório, com caminhos
absolutos. Identificou corretamente o Ark e as 164 tarefas sem depender do
diretório de trabalho do terminal.

## Problemas encontrados e corrigidos nesta revisão

1. **Retomada com CSV incompleto:** uma linha truncada podia ser considerada
   concluída. O CSV agora é publicado por substituição atômica e validado antes
   da retomada, incluindo cabeçalho, campos, duplicatas, status e códigos de saída.
2. **Traces antigos em nova tentativa:** logs de uma execução interrompida podiam
   permanecer quando a tentativa seguinte falhava antes de produzi-los. Os logs
   da tarefa pendente são removidos antes de uma nova tentativa.
3. **Tarefas alteradas durante uma rodada:** os hashes eram registrados somente
   na preparação. Agora são conferidos antes de cada tarefa e depois de copiá-la;
   o Ark recebe a cópia verificada.
4. **Configuração incompleta:** o modo de verificação aceitava campos ausentes ou
   inválidos que causariam falhas posteriores. Agora valida o nome do modelo,
   timeout, campos opcionais e prompt de sistema; prompts de tarefa vazios também
   são recusados.
5. **Imports ausentes em três tarefas:** os testes usavam funções auxiliares sem
   importá-las, causando `NameError` mesmo com uma solução correta. Foram
   acrescentados `poly` em `he_032`, `encode_cyclic` em `he_038` e `encode_shift`
   em `he_050`. Os asserts e o código inicial das soluções não foram alterados.

Os cenários corrigidos do executor foram reproduzidos em testes antes da correção.
O problema dos imports foi detectado ao executar o Ark real com uma solução
fornecida pelo teste de integração.

## Evidências locais

- **29 testes do executor aprovados**, cobrindo sucesso, reprovação, erro do Ark,
  solução ausente, timeout do Ark e dos testes, retomada, Ctrl+C, bloqueio de
  execução concorrente, integridade do CSV e das entradas, limpeza de traces,
  configuração inválida e funções auxiliares das tarefas.
- **56 testes do Ark atual aprovados** em uma cópia temporária, sem alterar seu
  checkout.
- **164 suítes importadas e coletadas pelo Pytest**, cada uma em um processo
  independente. Isso verifica a coleta, não a aprovação de soluções.
- **164 suítes verificadas quanto a referências globais ausentes**; os três
  imports incompletos encontrados foram corrigidos e receberam teste de regressão.
- **Cinco integrações completas aprovadas:** `he_000`, `he_010`, `he_032`,
  `he_038` e `he_050`. Foram usados o código real do Ark, seu ponto de entrada,
  protocolo, edição, confirmação por stdin, testes internos e avaliação externa.
  Somente a requisição ao modelo foi substituída por respostas locais com
  soluções conhecidas. Os tokens desses testes são simulados.
- O timeout foi testado com um subprocesso filho; o filho também foi encerrado.
- Fontes, configuração, trace e workspace existentes de `../ark` foram conferidos
  por hash antes e depois das integrações: **22 arquivos preservados**.
- Os **820 arquivos das tarefas** foram conferidos antes e depois da revisão.
  As únicas diferenças autorizadas são os três imports descritos acima.

Os testes e as integrações desta revisão não criaram uma rodada real em
`results/`. Os artefatos de auditoria ficaram em diretórios temporários.

## Execução sugerida

A partir da raiz deste projeto, defina a chave e rode primeiro uma tarefa real:

```bash
export OPENAI_API_KEY="sua-chave"
../ark/.venv/bin/python run_benchmark.py --run-name piloto-real --task he_000
```

O piloto confirma autenticação e acesso ao modelo, que a verificação local não
confirma. Depois, uma rodada completa usa outro nome:

```bash
../ark/.venv/bin/python run_benchmark.py --run-name avaliacao-01
```

Para retomar, repita o mesmo comando. Alterações no Ark, no executor, nas tarefas
ou nas opções exigem outra rodada. Falhas de tarefa permanecem registradas e são
ignoradas na retomada. Os testes continuam visíveis ao agente durante a resolução.
