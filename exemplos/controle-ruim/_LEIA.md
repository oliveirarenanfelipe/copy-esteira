# O controle de copy ruim — e ele é sintético de propósito

Estas peças existem para **um** teste: o teste 2 da régua, a discriminação. Ele responde se a
régua extraída de um corpus reprova copy reconhecidamente ruim.

Sem ele, uma régua que aprova tudo passa no teste da dispersão com nota alta e entra no registro.
Gate que não reprova nada não é gate.

Use assim:

```bash
python -m esteira.aferir ./meu-corpus --peca email --contra ./exemplos/controle-ruim
```

## Por que sintéticas, e por que isso está escrito aqui

Não há corpus público de "copy ruim" rotulado, e copy ruim de verdade é material de alguém —
material de terceiro não entra neste repositório.

Então elas foram **escritas para falhar**, cada uma num modo de falha nomeado no nome do arquivo.
Isso tem um limite que fica dito em vez de escondido: uma peça escrita para falhar falha mais
facilmente que copy ruim de verdade, que erra de formas mais sutis. O teste 2 mede o **piso** da
discriminação, não o teto.

Se a régua não reprova nem isto, ela não reprova nada.

## As peças

| Arquivo | O modo de falha |
|---|---|
| `01-institucionalis.txt` | fala da empresa, nunca do leitor; zero segunda pessoa |
| `02-frase-quilometrica.txt` | período longo encadeado, sem respiro nem frase curta |
| `03-jargao-corporativo.txt` | sinergia, solução, excelência: palavra que não significa nada |
| `04-sem-pedido.txt` | descreve e nunca pede nada; zero imperativo |
| `05-tudo-pergunta.txt` | interroga o leitor do começo ao fim, sem afirmar |
| `06-empilha-modificador.txt` | adjetivo sobre adjetivo, voz passiva, significância inflada |

Duas delas foram barradas pelo porteiro de escrita da casa na hora de gravar, com índice de vício
de 65,6 e 46,7 contra um teto de 35. A reprovação é o atestado de que elas servem: são ruins de um
jeito medido, não de um jeito opinado.
