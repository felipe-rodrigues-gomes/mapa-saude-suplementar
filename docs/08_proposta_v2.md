# Proposta v2 — hospedagem, narrativa e comparação entre concorrentes

Pedido (16/11/2026): (1) a rede da CAMED bloqueia o GitHub: hospedar em feliperodrigues.cloud; (2) falta storytelling, o site joga dado sem contexto; (3) falta comparar a minha operadora com as concorrentes **do mesmo estado**, de qualquer porte.

## 1. Hospedagem: `mapa.feliperodrigues.cloud`

Mesmo caminho do `gestao.feliperodrigues.cloud`:
- **DNS (Hostinger):** registro A `mapa` → 147.79.106.148 (o servidor do EasyPanel). O domínio não tem curinga, então precisa desse registro.
- **EasyPanel:** serviço novo lendo o repositório público, com um Dockerfile de 3 linhas (nginx servindo `site/`), HTTPS automático e publicação a cada push, como os outros.
- O GitHub Pages continua como cópia.
- **Risco:** filtros corporativos às vezes bloqueiam subdomínio novo, ainda sem categoria. Vale testar da rede da CAMED assim que subir.

## 2. Narrativa: "a conta da sua mensalidade"

Hoje cada seção é um achado solto. A proposta é uma história com o leitor no centro, em cinco capítulos ligados por perguntas:

| Capítulo | Pergunta que abre | O que mostra | Pergunta que leva ao próximo |
|---|---|---|---|
| 0. Você | "Você tem plano de saúde? De qual estado?" | escolha do estado (e, se quiser, da operadora); tudo que vem depois fala "no seu estado" | — |
| 1. Seus R$ 100 | "Para onde vai cada R$ 100 que você paga?" | R$ 82 atendimento, R$ 9 administração, R$ 3 venda… e o que sobra | "Se sobra tão pouco, como o setor lucrou R$ 23 bilhões em 2025?" |
| 2. O lucro | "De onde vem o lucro?" | operação × aplicações, ano a ano (o gancho, agora como revelação) | "E quem sustenta essa conta?" |
| 3. Quem paga | "Quem são os clientes no seu estado?" | cobertura, plano individual sumindo, envelhecimento, quem domina o mercado local | "E o que vocês recebem em troca?" |
| 4. O que você recebe | "O atendimento acompanha o que se paga?" | reclamações, nota da ANS, ida ao SUS (com as três leituras) | "E a sua operadora, como está?" |
| 5. Sua operadora | "Como ela se compara às concorrentes no seu estado?" | o comparador (item 3) | — |

Em cada capítulo: uma frase de contexto **antes** do número, o número, uma linha "o que isso significa para você", e a pergunta que puxa o próximo. Indicador de progresso (capítulo 2 de 5). A escolha do estado fica guardada no aparelho.

## 3. Comparador: "sua operadora contra as concorrentes no seu estado"

- **Concorrente** = toda operadora com clientes no estado, de qualquer porte (corte: ≥ 1% dos clientes do estado ou ≥ 5 mil clientes, para não listar centenas).
- A pessoa escolhe o estado e a operadora. As 3 maiores concorrentes entram por padrão, e dá para trocar.
- **Lado a lado**, com o melhor de cada linha marcado, em dois blocos honestos:

| No seu estado (dado do estado) | Na operadora inteira (a contabilidade é nacional) |
|---|---|
| clientes e participação no mercado local | quanto da mensalidade volta em atendimento |
| crescimento em 12 meses | lucro sobre a receita |
| **hospitais na rede**, e quantos com pronto-socorro (NOVO) | nota de qualidade da ANS |
| **preço de tabela** da sua faixa de idade, por tipo de plano e acomodação (NOVO) | glosa e prazo para pagar a rede |
| **reclamações por 100 mil clientes no estado** e o que mais reclamam (NOVO) | cobrança do SUS parada na Justiça |
| ida ao SUS por possível falha de acesso, no estado | |
| clientes com 59 anos ou mais | |

- Link compartilhável: `#comparar/CE/317144` ("olha como está a sua").

### Dados novos (tudo dados abertos da ANS)
| Base | Tamanho | Vira |
|---|---|---|
| NIP 2025–2026 (demandas dos consumidores) | ~330 MB | reclamações por operadora × estado × tema |
| Produtos e prestadores hospitalares | 2,1 GB | hospitais distintos na rede ativa por operadora × estado (e município), com urgência |
| Valor comercial médio (NTRP, jun/2026) + características dos planos | ~420 MB | preço de tabela mediano por operadora × estado × faixa × contratação × acomodação |

### Cuidados (vão escritos na página)
- **Preço de tabela** é o valor informado à ANS na nota técnica do plano à venda. Não é o que cada cliente paga: coletivo negocia e há reajustes.
- **Contar hospitais** não mede qualidade, e planos da mesma operadora têm redes diferentes. A contagem é de hospitais em pelo menos um plano ativo.
- **Reclamações** de operadora com poucos clientes no estado oscilam: a mesma trava de 20 mil clientes.

## 4. Tela de reclamações: "quem mais gera reclamação no seu estado?" (pedido do Felipe, 16/11)

A tela feita para provocar curiosidade (e conversa). Capítulo próprio, antes do comparador completo.

- **O número, em português:** "a cada mil clientes, X reclamaram na ANS nos últimos 12 meses" (NIP por operadora × estado do beneficiário ÷ clientes no estado). A ANS publica o mesmo índice como "por 100 mil por mês", que ninguém entende.
- **Ranking do estado** em barras, com a operadora escolhida destacada e a média do estado como referência.
- **Segunda camada (o que dá conversa):** quanto a operadora **resolveu sozinha** (classificação da NIP: reparação voluntária e eficaz) contra quanto precisou da ANS. E os 3 temas que mais aparecem para cada uma (negativa de cobertura, reembolso, prazo, reajuste…).
- **Travas para a polêmica ser defensável:** só operadoras com ≥ 20 mil clientes no estado; assistência médica separada de odontologia; fonte e período em cada número; o mesmo critério para todas (nenhuma poupada nem destacada fora da regra); frase de leitura: "mais reclamação pode ser carteira maior em plano individual, idosa ou mais exigente; o número mostra onde olhar, não o veredito".
- **Link compartilhável:** `#reclamacoes/CE` e `#reclamacoes/CE/317144`.

## Ordem sugerida
1. Hospedagem (rápido; depende do registro DNS).
2. Dados do comparador (NIP, rede, preço).
3. Tela de reclamações e comparador.
4. Narrativa (reescrita das seções em capítulos).
5. Teste em celular e desktop; publicar.

## Implementado (16/11/2026)

- **Hospedagem:** `Dockerfile` (nginx 1.27) + `deploy/nginx.conf` na raiz. Falta o registro DNS `mapa` e o serviço no EasyPanel (passo do Felipe).
- **Narrativa:** abertura com a escolha do estado e cinco capítulos (Seus R$ 100 → O lucro → Quem paga → Reclamações → Compare), cada um terminando numa pergunta que leva ao próximo. O estado escolhido vale para a página inteira e fica guardado no navegador.
- **Reclamações:** `scripts/etl_nip.py` (331.592 reclamações válidas, jul/2025–jun/2026, sem planos só odontológicos; bate com o IGR). Resolução pela fórmula da ficha técnica da ANS, porque a base aberta de resolutividade parou em out/2019. Brasil: 6,3 por mil clientes por ano; de 2,4 (RS) a 19,0 (RR).
- **Comparador:** `scripts/exportar_uf.py` gera `site/dados/uf/XX.json` (concorrente = ≥ 1% dos clientes do estado ou ≥ 5 mil clientes nele) e `brasil.json`. Preço de tabela e hospitais vêm de `scripts/etl_preco_rede.py`.
- **Links:** `#reclamacoes/UF[/REG]`, `#compare/UF/REG[,REG…]`, `#operadora/REG`.
- **Leitura dos temas:** os nomes da NIP viram a frase de quem reclama ("Regras para Acesso aos Atendimentos" → "Autorização e acesso a atendimento"); o nome oficial fica no `title`.
