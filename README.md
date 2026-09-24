# Copy Esteira

Uma esteira que recebe copy e devolve duas coisas: a auditoria do que está errado e a copy nova
para pôr no lugar, com gates que reprovam de verdade em vez de avisar.

Zero dependência no núcleo. Python 3.12 ou mais novo, biblioteca padrão.

```bash
python -m esteira.gate ./minha-pagina.html --peca pagina-de-captura
python -m esteira.leitor ./minha-pagina.html
python -m esteira.porta "audita a copy da minha página de vendas em ./lp"
```

O `--peca` acima é só o exemplo de um dos sete tipos. Eles estão listados em "Os sete tipos de
peça", mais abaixo, com quando usar cada um — e o tipo errado não dá erro, dá o número de outra
régua.

O passo a passo completo, do clone até a copy nova, está em "Como usar, do começo ao fim". Este
arquivo basta sozinho.

Se você chegou aqui com um agente de código junto, mande ele ler o `AGENTS.md` da raiz antes de
qualquer coisa. Ele repete os comandos daqui e acrescenta o que o agente **não** deve fazer, sendo
o primeiro item reescrever à mão um medidor que já está pronto e testado.

---

## O problema que ela resolve

Quase todo auditor de copy avisa. Ele imprime uma coluna chamada "fora da régua", a pessoa lê,
concorda, e publica a peça assim mesmo.

O auditor de copy anterior que originou este projeto tem 735 linhas, mede seis métricas por tipo
de peça e nunca reprovou uma peça na vida: a última linha do `main()` é `return 0`, incondicional.
Ele não tem defeito de implementação. Ele foi desenhado para informar.

Aqui o veredito é o código de saída, e peça reprovada não ganha arquivo de saída. Ela vai para
`_reprovados/`, que não é a pasta que você abre.

> Aviso que não reprova é decoração.

---

## As cinco camadas

```
  entrada  ->  C0 corpus  ->  C1 fatos      ->  C2 leitor frio
                                 (sem LLM)         (LLM cego)
                                    |                  |
                                    v                  v
                              C3 as mentes  ->  C4 o cético  ->  C5 as duas saídas
                              (dois grupos)     (refuta)         (auditoria + copy)
```

O veto mora inteiro na C1 e na C4. As outras propõem, e nunca reprovam sozinhas. O LLM interpreta
e escreve; o veto é determinístico, porque num teste real o mesmo pedido deu respostas diferentes
duas vezes. Isso é aceitável numa sugestão e inaceitável num veto.

| Camada | O que faz | Estado |
|---|---|---|
| 0 · corpus | vira texto visível, com `arquivo:linha` | pronta |
| 1 · fatos | legibilidade, forma, caminhos, medição, contraste | pronta, com mutação |
| 2 · leitor frio | mede compreensão sem contexto | pronta, calibrada antes de reprovar |
| 3 · mentes | dois grupos de lentes, cada uma declara quando não serve | registro pronto |
| 4 · cético | recebe um achado e tenta derrubá-lo | em uso |
| 5 · saídas | auditoria mais copy nova, vetada pelos mesmos gates | pronta |

---

## Como usar, do começo ao fim

Não há instalação. Clone, e confira que o motor está inteiro antes de confiar no que ele disser:

```bash
python testar_gates.py
```

### Com um agente de código junto

É o modo para o qual ela foi feita, porque a Camada 5 precisa de alguém que escreva.

1. Mande o agente ler o `AGENTS.md` da raiz. Ele diz o que existe e o que o agente não deve fazer.
2. Peça em língua normal: *"audita minha página de vendas em ./lp e me dá manchete nova"*.
3. O agente roda o roteiro abaixo, escreve as candidatas e entrega o que passou no veto.

### Sozinho, sem agente

Peça o roteiro à porta. Ela lê o pedido em língua normal, propõe os comandos na ordem, e não
executa nada:

```bash
python -m esteira.porta "audita a copy da minha página de vendas em ./lp e me propõe manchete nova"
```

### Os sete tipos de peça, e como escolher o seu

Todo comando que mede exige `--peca`, porque a régua de uma página de vendas não serve para uma
mensagem de WhatsApp. Se você errar o tipo, o veredito muda.

| `--peca` | quando usar | mídia |
|---|---|---|
| `pagina-de-vendas` | a página que **é** a oferta: tem preço, checkout, prova | página |
| `pagina-de-captura` | troca um material por um contato, sem preço | página |
| `pagina-de-obrigado` | o que aparece depois do cadastro ou da compra | página |
| `pagina-institucional` | quem somos, serviços, home da empresa | página |
| `anuncio` | criativo ou roteiro de anúncio | texto |
| `email` | um e-mail ou boletim, um por arquivo | texto |
| `mensagem` | WhatsApp, Telegram, mensagem de grupo | texto |

Esqueceu a lista? Rode o comando sem `--peca` e ele imprime os tipos:

```bash
python -m esteira.gate
```

A coluna **mídia** muda o que é cobrado. Peça de `página` responde também por medição instalada,
recurso de terceiro e link que não resolve. Peça de `texto` não, porque um roteiro em `.txt` não
tem pixel dentro dele, e cobrar isso dele seria reprovar por uma falta impossível de suprir.

### O roteiro, na ordem, e o que cada passo responde

```bash
# 1. o projeto inteiro: rotas, links que não resolvem, login, contraste, recurso de terceiro
python -m esteira.projeto ./lp

# 2. os fatos da peça: forma, legibilidade, medição instalada
python -m esteira.gate ./lp --peca pagina-de-vendas --saida ./saida

# 3. a compreensão, que os passos 1 e 2 não medem
python -m esteira.leitor ./lp

# 4. o que cada mente pergunta sobre ESTE material, para você escrever melhor
python -m esteira.dossie ./lp --peca pagina-de-vendas

# 5. escreva as candidatas num JSON, onde você quiser. O nome não importa,
#    o caminho é o que você passar no passo 6. O molde está em
#    `exemplos/candidatas.json`, e só `texto` é obrigatório

# 6. a copy nova, vetada pelos MESMOS gates do passo 2
python -m esteira.criar ./candidatas.json --peca pagina-de-vendas --saida ./saida

# 7. leia os códigos de saída antes de escrever o relatório
```

O **passo 4** é o que as oito mentes têm a dizer sobre o seu material: cada lente entrega a pergunta
que ela faz e a régua que ela aplica, mais as que se declaram inaplicáveis ao seu caso. É insumo
para escrever, e não veredito — nenhuma lente reprova nada.

O **passo 5** é a parte que esta ferramenta não faz por você, e é uma decisão em vez de uma falta: o
veto é aritmética, e aritmética não escreve. Quem escreve propõe, quem veta é código.

O mínimo que o passo 6 aceita é isto, com `molde`, `lente` e `contexto` opcionais:

```json
{"candidatas": [{"texto": "a manchete que você quer testar"}]}
```

### Três coisas que surpreendem na primeira vez

Só `gate` e `criar` gravam arquivo, e só quando você passa `--saida`. O `projeto` e o `leitor`
imprimem na tela e não deixam nada em disco, porque eles relatam e não produzem peça.

O `criar` sai **1** quando alguma candidata é vetada, mesmo havendo aprovadas. Não é erro: é o lote
tendo copy reprovada dentro. As aprovadas ficam em `saida/copy-nova.txt`, que é o arquivo que você
usa, e as vetadas em `saida/_reprovados/`.

O `projeto` sai **3** numa pasta sem arquivo de página. Três não é verde: quer dizer que não deu
para medir, e a diferença entre isso e "está limpo" é o motivo de esta ferramenta existir.

---

## O que ela mede sem instalar nada

### Legibilidade em português

Pelo índice Flesch adaptado ao português (Martins et al., ICMC-USP, 1996):

```
ILF = 248,835 − 1,015 × palavras/frase − 84,6 × sílabas/palavra
```

O intercepto muda de 206,835 para 248,835 porque o português tem mais sílabas por palavra, e a
fórmula inglesa o pune. Isso importa na prática: a biblioteca mais popular de legibilidade em
Python não cobre português. As variantes dela vão até russo e polonês, e param aí. Chamada sobre
texto em português, devolve um número calculado com coeficiente de inglês, e número errado que lê
como fato é pior que número nenhum.

### Métricas de forma

Palavras por frase, frases curtas, perguntas, segunda pessoa, imperativo e travessões. Cada uma com
alvo por tipo de peça, nunca um alvo único. Régua única reprova justamente a peça que está certa:
uma página de captura deve ter zero pergunta, enquanto uma página de vendas deve ter cerca de sete
por cento.

### Contraste WCAG, com o passo que quase todo medidor pula

Texto a 50% de opacidade sobre um fundo não é a cor dele. A conta tem dois passos: compor a cor
sobre o fundo, e só então medir contra esse mesmo fundo. Sobre fundo variável o gate reprova pelo
pior quadro, porque medir um só não decide nada. O mesmo texto pode ir de 5,29:1 a 1,27:1.

### Caminhos, medição instalada e CDN de terceiro

Link interno que não resolve. Ausência de pixel, de analytics ou de gravador de sessão. URL
absoluta servindo recurso em tempo de execução.

---

## De onde vêm os alvos, e como a régua passa por gate

Os alvos de `esteira/reguas.json` saíram de um corpus de copy em português, medido peça a peça.
Cada ficha carrega o `n`, a fonte e o regime:

| Regime | O que significa |
|---|---|
| `limiar` | 15 peças ou mais no corpus: o gate reprova por este alvo |
| `direcao` | menos de 15: o número orienta e o gate não reprova |
| `nao-coberto` | sem corpus: o alvo fica nulo, e o gate declara que não mediu |

A folga de cada métrica é o desvio medido do próprio corpus, nunca um número redondo. Isso não é
preciosismo: numa medição real a folga de palavras por frase estava em 2,0, herdada de outro
projeto, enquanto o desvio do corpus era 2,3. A folga estava abaixo do espalhamento natural do
material e reprovava oito de quarenta e sete peças legítimas. A folga estava errada, não o corpus.

Para medir o seu próprio corpus, uma peça por arquivo:

```bash
python -m esteira.aferir ./meu-corpus --peca email
python -m esteira.aferir ./meu-corpus --peca email --contra ./exemplos/controle-ruim
python -m esteira.aferir ./meu-corpus --peca email --registrar
```

O aferidor roda cinco testes antes de a régua entrar no registro, e régua que não passa não é
gravada:

| # | Teste | O que ele responde |
|---|---|---|
| 0 | dispersão | a mediana descreve o conjunto de onde saiu? |
| 1 | validação cruzada | extraída de metade, ela aprova a outra metade? |
| 2 | discriminação | ela reprova copy reconhecidamente ruim? |
| 3 | falso positivo | ela deixa passar peça boa que não estava no corpus? |
| 4 | cruzada | a régua de um grupo aprova a copy de outro? |

O teste 0 parece circular e não é. O argumento contra ele era que rodar a régua contra o próprio
corpus passaria cem por cento por construção. Medido: deu sessenta e seis. O corpus tem folga, as
peças se espalham, e o número não é garantido. Cem por cento seria régua frouxa demais para reprovar
qualquer coisa.

A armadilha vem dita junto: validar a régua contra o corpus de onde ela saiu prova coerência, não
qualidade. O teste 0 sozinho não basta, e é por isso que os outros quatro existem.

### Quem decide se uma rota exige login, e por que isso engana

Há dois modelos, e eles se leem ao contrário.

No primeiro, cada rota se protege sozinha, com uma marca de sessão no próprio arquivo ou no layout
acima dela. No segundo, um middleware cobre o site inteiro e uma lista de caminhos públicos abre as
exceções. O segundo é o recomendado em segurança, e é o que engana um detector ingênuo: ele procura
marca de autenticação dentro da rota, não acha nenhuma, e conclui que a rota é pública. Só que a
rota protegida ali é justamente aquela que ninguém mencionou.

A esteira lê o porteiro do projeto antes de responder. Num caso real, a primeira versão devolveu
zero rota protegida num site onde quase cinquenta exigiam login. Não errou por pouco: errou o
sentido da pergunta.

E há uma regra que vem junto, na direção contrária: caminho público abre a subárvore inteira. Se
`/blog` é público, `/blog/um-post` também é. Sem isso, todo artigo do blog vira rota privada no
relatório, e quem recebe conserta o que não estava quebrado.

---

## Legibilidade não é compreensão, e o número está medido

A mesma página, medida duas vezes por instrumentos diferentes:

| O que se mediu | Resultado |
|---|---|
| Legibilidade (índice Flesch adaptado) | 68,7 — faixa "fácil" |
| Compreensão (leitor sem contexto) | 3 de 10 |

Fácil de ler, e não diz o que a empresa faz.

As duas coisas são verdadeiras ao mesmo tempo, e nenhum ajuste de limiar na régua de forma acha o
segundo problema, porque ele não é de forma. É por isso que o leitor frio é uma camada separada, e
não uma métrica a mais.

```bash
python -m esteira.leitor ./minha-pagina.html            # relata
python -m esteira.leitor ./minha-pagina.html --exigir 5  # vira gate e reprova
python -m esteira.leitor ./meu-projeto --publico         # quem a página diz que você é
```

Ela responde as dez perguntas que um visitante de primeira viagem faz, usando só o texto visível, e
diz de qual trecho tirou cada resposta. Pergunta sem evidência fica sem resposta, nunca com uma
resposta deduzida do que a página quis dizer.

Ela foi calibrada antes de poder reprovar. O piso de 5 não é um número escolhido: é o menor placar
entre peças que já converteram, medidas antes de o gate ganhar poder de veto. Gate que reprova o que
converteu está errado sobre o mundo, não sobre a página. Sem `--exigir`, ele relata e não reprova.

⚠️ O limite dela fica dito em vez de escondido: ela mede se a página responde a pergunta, não se a
resposta é boa. Uma página que diz "para todos os públicos" responde à segunda pergunta, e responde
mal. Rodada contra a mesma página da tabela acima, ela devolveu 6 de 10 onde um leitor humano sem
contexto deu 3 de 10, porque conta a presença do vocabulário que responderia e não o conteúdo da
resposta. O que ela acha bem é o piso: as perguntas para as quais a página não tem vocabulário
nenhum.

---

## O detector de que mais me orgulho

`prescrito_e_ausente` não compara a página com régua externa nenhuma. Compara o produto com o que o
próprio produto declara que deveria existir.

Num caso real ele encontrou uma tela de FAQ prescrita no catálogo de templates do próprio sistema,
com rota declarada, e a rota não existia. Régua que não precisa do corpus de ninguém é régua
universal, e é a única que nasce pronta.

---

## As três réguas, e só uma nasce cheia

| Régua | De onde vem | Quando reprova |
|---|---|---|
| Universal | WCAG, caminhos, medição, legibilidade | sempre |
| De julgamento | o voto de quem opera, virando estatística | quando o n permitir |
| Do produto | gramática extraída do material do cliente | quando existir |

O `esteira/reguas.json` nasce com os alvos vazios, e isso é de propósito. Alvo nulo não reprova: o
gate mede o valor e declara que não tem com o que comparar. Inventar número ali seria casca, e
casca já custou caro.

### Como encher com o seu corpus

1. Junte as peças do seu produto que já funcionaram, as que converteram, não as que você gosta.
2. Meça cada uma com `python -m esteira.gate <peça> --peca <tipo>`. Os valores saem mesmo sem alvo.
3. Escreva a mediana de cada métrica no `alvos` do tipo de peça correspondente.
4. Preencha o campo `fonte` dizendo de onde o número veio e quantas peças entraram.

Com menos de umas 15 peças por tipo, trate o resultado como direção e não como meta. Não se publica
casa decimal sobre 13 casos.

Para a régua de julgamento o caminho é o mesmo de um precedente que já rodou: vote as peças,
acumule, e só então extraia regra com teste estatístico. Regra sem os dois lados e sem valor de p é
opinião com cara de dado.

---

## Os códigos de saída, e por que 3 não é verde

```
0  nada a acusar
1  ACUSOU — mediu, e o alvo reprovou
2  não deu para USAR — falta argumento, caminho não existe, peça não declarada
3  não deu para MEDIR — a fonte não respondeu, ou não há régua
```

O `3` existe porque a alternativa é mentir. Quando uma peça opcional falta, ou a página não
renderiza, o gate declara o que deixou de medir em vez de devolver verde. Gate que não mede não
aprova.

---

## O que ela não faz

Ela não escreve o texto final sozinha. As lentes analisam e propõem argumento, e a redação sai na
gramática do seu produto. Lente que escreve direto produz copy traduzida, que é copy de ninguém.

Ela não reprova por palavra numa lista. Um teste de palavra isolada não distingue o conteúdo que se
ensina do serviço que se vende, e alarme falso ensina a ignorar a linha. Ou o gate carrega o sujeito
e o contexto, ou o achado sai como baixa confiança para julgamento humano.

Ela não decide se a copy é boa. Decide se a peça é legível, navegável, medida e dentro da forma
declarada. Boa é julgamento.

---

## Rodar os testes

```bash
python -m pytest testar_gates.py -v    # com pytest
python testar_gates.py                 # sem pytest, mesmo veredito
```

O arquivo roda nos dois modos de propósito. Sem o bloco `__main__` dele, `python testar_gates.py`
sairia 0 sem executar um único teste, porque as funções seriam apenas definidas e nunca chamadas.
Foi medido, e o CI teria ficado verde para sempre provando nada.

### Mutação, que é o que prova um gate

Gate que passou não prova nada. Um gate que sempre devolve "passa" passa em todo teste de caminho
feliz que se escreva para ele. O que prova é quebrar o alvo de propósito e ver o gate reprovar:

```
GATE MUTADO        RESULTADO    TESTE QUE PEGOU
legibilidade       PEGA         test_MUTACAO_legibilidade
cdn-de-terceiro    PEGA         test_MUTACAO_cdn_de_terceiro
medicao            PEGA         test_MUTACAO_medicao_instalada
caminhos           PEGA         test_MUTACAO_caminhos
forma              PEGA         test_MUTACAO_forma_pf, _imperativo, _travessao
saida-reprovada    PEGA         test_REPROVADO_NAO_CHEGA_NA_PASTA_QUE_A_PESSOA_ABRE
aplicadas: 6 | detectadas: 6 | SOBREVIVENTES: 0
```

Gate cuja mutação sobrevive não conta como entregue.

---

## Licença

MIT. Veja `LICENSE`.

O que está aqui é o motor, o método e as réguas medidas. O **corpus** de onde as réguas saíram não
vem no pacote, e a gramática e o julgamento de cada produto também não: são de quem os construiu.

A distinção importa porque uma versão anterior deste repositório publicava os alvos vazios e mandava
quem clonasse enchê-los. Medido num clone limpo: a pessoa enche com três peças, a régua sai com
trinta e cinco pontos de desvio, e reprova as três candidatas — inclusive as duas boas. Ela abre o
relatório, vê tudo vermelho e desiste. Não por defeito do motor: por régua ruim que o produto a
obrigou a fabricar.

Então os números sobem prontos, e a ferramenta de refazer a conta com o seu corpus sobe junto: é o
`python -m esteira.aferir`, da seção "Como encher com o seu corpus" acima.
