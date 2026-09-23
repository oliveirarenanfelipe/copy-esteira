# Instruções para a IA que abriu este repositório

Você é um agente de código e alguém pediu para auditar ou escrever copy usando este
repositório. **Leia estas instruções inteiras antes de rodar qualquer coisa.** Elas
existem porque o erro comum aqui não é errar um número: é reescrever à mão um medidor
que já está pronto, testado e com mutação provada.

Este arquivo funciona com qualquer ferramenta que leia o repositório. Se a sua suporta
skills, instale-o como skill — o formato de um fabricante só não serve para um
repositório que qualquer um clona.

---

## As três proibições

Elas vêm antes dos comandos de propósito. Se você só ler esta seção, já é o suficiente
para não estragar o trabalho.

### 1. Não escreva medidor próprio

Não escreva Python para contar palavras por frase, medir legibilidade, calcular
contraste, procurar link quebrado ou detectar pixel de medição. **Tudo isso já existe
aqui, com teste de mutação.** Chame o comando.

Se você escrever o seu, ele vai discordar do que está no repositório, e ninguém vai
saber qual dos dois está certo. O medidor daqui erra de um jeito conhecido e documentado;
o seu erra de um jeito que ninguém mediu.

Legibilidade é o caso mais caro: a biblioteca popular de legibilidade em Python **não
cobre português**. Chamada sobre texto em português, ela devolve um número calculado com
coeficiente de inglês. Número errado que lê como fato é pior que número nenhum.

### 2. Não invente limiar que não está no registro

Os alvos ficam em `esteira/reguas.json`, em dados, nunca no código. Se o registro devolve
`null` para uma métrica, a resposta correta é **"não há régua medida para isto"**, e o
gate sai declarando que não mediu.

Não preencha o buraco com um número plausível. Um alvo sem corpus atrás é casca: lê como
medida e não é.

Se você precisa de uma régua que não existe, o caminho é medir um corpus e registrá-la
com `n` e fonte — não estimar.

### 3. Não entregue peça que o gate reprovou

Se o gate saiu **1**, a peça não está pronta. Não a apresente como entrega com uma
ressalva no fim do relatório. Não copie o arquivo da pasta `_reprovados/` para a pasta
de saída.

O repositório inteiro foi construído porque o auditor anterior avisava e nunca reprovava.
Se você transforma uma reprovação em aviso, desfaz o produto.

---

## Os quatro códigos de saída

Toda peça daqui usa a mesma taxonomia. Ela é a parte mais importante da interface,
porque separa dois "não" que parecem iguais e não são.

| Código | Nome | O que significa |
|---|---|---|
| `0` | LIMPO | mediu, e não há o que acusar |
| `1` | ACUSOU | mediu, e o alvo reprovou |
| `2` | NÃO DEU PARA USAR | argumento faltando, caminho que não existe, tipo de peça desconhecido |
| `3` | NÃO DEU PARA MEDIR | a fonte não respondeu, ou não há régua |

🔴 **`3` não é um verde.** Gate que não mede não aprova. Se você reportar um `3` como
"passou", está entregando uma peça que ninguém conferiu. Diga "não foi medido, e aqui
está o motivo".

E `0` também não quer dizer "a copy é boa". Quer dizer "é legível, navegável, medida e
está dentro da forma declarada para este tipo de peça". Boa é julgamento, e julgamento
não é o que esta camada faz.

---

## Os comandos, e o que cada um devolve

Rode tudo a partir da raiz do repositório. Python 3.12 ou mais novo, biblioteca padrão,
zero instalação.

### Auditar uma peça que já existe

```bash
python -m esteira.gate <caminho> --peca <tipo>
python -m esteira.gate <caminho> --peca <tipo> --saida <pasta>
```

`<caminho>` é um arquivo (`.html`, `.md`, `.txt`, `.tsx`, `.jsx`) ou uma pasta de
projeto. `--peca` é obrigatório: sem declarar o tipo, a esteira mediria com a régua
errada. Rodar sem ele sai `2`.

**Devolve** uma linha por gate, cada uma com o valor medido e o limiar que a julgou, e
o veredito no fim com o código de saída. Com `--saida`, escreve a auditoria em arquivo —
e peça reprovada vai para `<pasta>/_reprovados/`, que não é a pasta que a pessoa abre.

Os tipos aceitos hoje, e o regime de cada um:

| Tipo | Regime | n | O que isso quer dizer |
|---|---|---|---|
| `mensagem` | limiar | 59 | o gate reprova pela régua de forma |
| `email` | limiar | 44 | idem |
| `anuncio` | limiar | 35 | idem |
| `pagina-institucional` | direção | 18 | o número orienta, o gate não reprova por ele |
| `pagina-de-vendas` | direção | 10 | idem |
| `pagina-de-captura` | direção | 7 | idem |
| `pagina-de-obrigado` | direção | 5 | idem |

Nenhum tipo tem alvo nulo. As únicas três métricas sem régua são o índice de vício nos
três tipos de peça curta, e cada uma carrega no registro quantas peças a alcançaram e por
que isso não bastou.

⚠️ `pagina-institucional` tem 18 peças e mesmo assim é direção. Não é engano, e a regra é
o campo `evidencia` de cada ficha: uma régua só ganha poder de veto com 15 peças **e** uma
linha dizendo que prova existe de que aquele corpus vale ser perseguido — conversão
apurada, permanência medida, ou uma decisão registrada. Sem essa linha, o número orienta
e não reprova. Tamanho de corpus sozinho não dá poder de veto: 18 páginas medianas dão o
mesmo `n` que 18 páginas que venderam.

Mesmo nos tipos não cobertos, os gates universais rodam: contraste, caminhos, medição
instalada e CDN de terceiro não dependem de corpus de ninguém.

Para ver a lista atual direto do registro:

```bash
python -m esteira.gate
```

### Varrer o projeto inteiro, que um arquivo sozinho não mostra

```bash
python -m esteira.projeto <pasta-do-projeto>
python -m esteira.projeto <pasta-do-projeto> --exigir
```

Três tipos de achado só existem olhando o projeto todo, e o gate de um arquivo não os alcança:

- **link interno que não resolve** — precisa do mapa de rotas;
- **rota que exige login** — precisa saber como *este* projeto decide isso, e há dois modelos
  que se leem ao contrário;
- **tela que o produto declara e não entrega** — compara o produto com ele mesmo, sem régua
  externa nenhuma.

Mais contraste sobre fundo variável e recurso de terceiro servido em tempo de execução.

Rode isto **antes** do gate de arquivo quando o alvo for um site ou aplicativo, e não uma peça
solta. Com `--exigir`, vira gate e sai `1`.

### Medir a compreensão, que não é a legibilidade

```bash
python -m esteira.leitor <caminho>
python -m esteira.leitor <caminho> --exigir 6
```

Responde as dez perguntas que um visitante de primeira viagem faz, usando **só o texto
visível**, e devolve o placar de compreensão com a evidência de cada resposta.

Ele existe porque os dois números se separam: uma mesma página real mediu **68,7 de
legibilidade, faixa "fácil", e 3 de 10 de compreensão**. Fácil de ler, e não diz o que
a empresa faz. Nenhum ajuste de limiar de legibilidade acharia esse defeito.

Com `--exigir`, vira gate e sai `1` abaixo do piso. Sem, só relata e sai `0`.

### Medir um corpus e extrair uma régua

```bash
python -m esteira.aferir <pasta-de-pecas> --peca <tipo>
python -m esteira.aferir <pasta> --peca <tipo> --contra ./exemplos/controle-ruim
python -m esteira.aferir <pasta> --peca <tipo> --registrar
```

Cada arquivo `.txt` ou `.md` da pasta é **uma** peça. Medir um arquivo que contém trinta
e-mails devolve o retrato de um e-mail de trinta mil caracteres, que não existe.

Use isto quando a pessoa tiver um corpus próprio e quiser a régua dela, ou quando um tipo
de peça estiver `nao-coberto`. **Não** invente o alvo na mão — é para isso que este comando
existe, e ele roda os cinco testes da régua antes de gravar. Régua que não passa não entra.

### Escrever copy nova, com o mesmo gate por cima

```bash
python -m esteira.criar <candidatas.json> --peca <tipo> --saida <pasta>
```

⚠️ **Esta peça não escreve o texto. Quem escreve é você.** Ela recebe candidatas prontas
em JSON (veja `exemplos/candidatas.json` para o formato), aplica as lentes, exige que
cada lente que não se aplica se declare inaplicável, e **veta as candidatas que não
passam nos mesmos gates da Camada 1**.

Régua que vale só para os outros não é régua, é opinião. A copy que sai daqui passa pelo
mesmo gate da copy de terceiro.

### Descobrir qual comando rodar

```bash
python -m esteira.porta "audita a copy da minha página de vendas em ./lp"
```

Casamento de palavra sobre tabela, zero LLM: mesma frase, mesmo plano, sempre. **Ela
propõe e não executa** — devolve o comando pronto para você conferir e rodar.

### Rodar os testes

```bash
python -m pytest testar_gates.py -q     # com pytest
python testar_gates.py                  # sem pytest, mesmo veredito
```

---

## Onde ficam as réguas, e como ler uma

`esteira/reguas.json`. Três coisas moram lá, e elas têm origens diferentes:

| Camada da régua | De onde saiu | Muda quando |
|---|---|---|
| `universal` | WCAG e a medição que toda página que vende precisa ter | quase nunca |
| `pecas[<tipo>].alvos` | corpus medido de copy em português, com `n` e fonte declarados | quando você medir um corpus melhor |
| folga | o desvio do próprio corpus, nunca um número redondo | junto com o alvo |

Cada tipo de peça tem a **sua** régua, e isso não é refinamento: uma régua única reprova
justamente a peça que está certa. Página de captura deve ter zero pergunta; página de
vendas fica perto de sete por cento.

Leia o campo `regime` de cada tipo antes de confiar no número:

- `regime: "limiar"` — corpus grande o bastante, o gate **reprova** por ele;
- `regime: "direcao"` — corpus pequeno, o alvo é direção e o gate **não reprova**;
- alvo `null` — não há régua, e o gate declara que não mediu.

---

## O que fazer quando o gate acusa

1. **Leia qual gate acusou.** A linha traz o valor medido e o limiar. `forma:pf 24.1
   (limiar 13.2)` quer dizer frase longa demais para o tipo de peça, não "texto ruim".
2. **Vá ao trecho.** A Camada 0 sabe dizer de onde veio cada texto. Não conserte a peça
   inteira por causa de uma métrica.
3. **Não mexa no limiar para passar.** Se você acha que o limiar está errado, o caminho
   é medir o corpus de novo e registrar, dizendo `n` e fonte. Ajustar o alvo até a peça
   passar é escrever o teste olhando a resposta.
4. **Reprovação sobre `regime: "direcao"` não existe** — se saiu reprovação, o alvo é
   limiar, e ele tem corpus atrás.

---

## O que este repositório não faz

- **Não decide se a copy é boa.** Decide se ela é legível, navegável, medida e está
  dentro da forma declarada. O julgamento é de quem lê.
- **Não traz corpus, gramática nem julgamento de ninguém.** O motor e as réguas medidas
  saem; o material de cliente não sai, e em parte nem é nosso para publicar.
- **Não chama modelo de linguagem em lugar nenhum do veto.** O LLM interpreta e escreve;
  o veto é aritmética. Num teste real o mesmo pedido devolveu respostas diferentes duas
  vezes — aceitável numa sugestão, inaceitável num veto.
- **Não acessa a rede.** Tudo é lido do disco.

---

## Um roteiro completo, do pedido ao veredito

Pedido típico: *"audite a copy desta landing page"*.

```bash
# 1. o que a esteira entende do pedido (opcional, e não executa nada)
python -m esteira.porta "audita a copy da minha página de vendas em ./lp"

# 2. o projeto inteiro: rotas, links, login, contraste, recurso de terceiro
python -m esteira.projeto ./lp

# 3. os fatos da peça: forma, legibilidade, medição instalada
python -m esteira.gate ./lp --peca pagina-de-vendas --saida ./saida

# 4. a compreensão, que os passos 2 e 3 não medem
python -m esteira.leitor ./lp

# 5. leia os códigos de saída antes de escrever o relatório
```

No relatório, para cada achado: **o valor medido, o limiar que o julgou, e de onde veio o
texto.** Achado sem evidência é recusado pela própria esteira na Camada 3 — não o
apresente na sua.

Se algum passo saiu `3`, diga o que não foi medido. É a diferença entre "auditei e está
limpo" e "auditei o que deu, e isto aqui ficou de fora".
