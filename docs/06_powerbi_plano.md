# Etapa 4 — Plano do Power BI

> **Decisão (15/11/2026): HTML é o produto principal (todas as páginas, link do post); o Power BI fica enxuto, como prova técnica.**
> Power BI = modelo semântico em TMDL (legível no GitHub) + medidas DAX comentadas + 2 páginas: **"O lucro vem das aplicações"** e **"Ficha da operadora"**.
> Só operadoras médico-hospitalares. Tabelas enxutas em `dados/pbi/` (scripts/exportar_pbi.py) para o `.pbix` ficar pequeno.
> O plano completo abaixo fica como referência para o HTML (etapa 5).

## Como vai ser construído
- Projeto **PBIP** (modelo em TMDL + relatório em PBIR), gerado por script e versionado no GitHub; o `.pbix` sai dele no fim (Arquivo › Salvar como).
- Fonte: os parquet de `dados/tratados/`, lidos por um parâmetro `PastaDados`. Quem clonar o repositório troca o parâmetro e atualiza.
- Power BI Desktop instalado: versão Store 2.159 (nov/2026).
- **DAX:** nos arquivos do projeto o Power BI grava em sintaxe invariante (vírgula). Na documentação e no README as medidas aparecem como você digita no Desktop em PT-BR, com ponto e vírgula.
- Em fases, validando cada uma: (a) modelo + medidas, conferidas contra o Python; (b) uma página por vez.

## Modelo (estrela)
| Tabela | Grão | Uso |
|---|---|---|
| `dOperadora` | operadora | nome, modalidade, porte, UF sede/principal, região, no ranking? motivo |
| `dTrimestre` | trimestre (2021T1–2026T2) | eixo do contábil |
| `dCompetencia` | mês | eixo de beneficiários e IGR |
| `dUF` | UF | nome para o mapa (sem acento), região, população IBGE |
| `dMunicipio` | município | mapa municipal |
| `fContabil` | operadora × trimestre | sinistralidade, resultados, índices (numerador e denominador separados) |
| `fBeneficiarios` | competência × operadora × UF × contratação × faixa × sexo | carteira, 59+, crescimento, cobertura |
| `fBenefMunicipio` | competência × município | mapa de cobertura |
| `fIGR`, `fIDSS`, `fGlosa` | operadora × mês / ano / semestre | qualidade |
| `fRessarcUso`, `fRessarcCobranca` | mês × operadora × UF × grupo de leitura / situação | SUS |
| `fFoto` | operadora (foto atual, `ind_operadora`) | ranking, quartis por porte e ficha |

**Filtro por UF:** nos indicadores de mercado (vidas, cobertura, SUS) a UF filtra direto. Nos indicadores de operadora (sinistralidade, resultado), a contabilidade é nacional: a UF seleciona as **operadoras com carteira no estado**, e o painel diz isso no título.

## Medidas principais (exemplos, sintaxe PT-BR)
```dax
Sinistralidade 12m =
DIVIDE ( SUM ( fContabil[sinist_num_12m] ); SUM ( fContabil[sinist_den_12m] ) )

Resultado da operação (R$ bi) =
DIVIDE ( SUM ( fContabil[resultado_operacional_ytd] ); 1E9 )

Sinistralidade – mediana do porte =
VAR _porte = SELECTEDVALUE ( dOperadora[PORTE] )
RETURN
    CALCULATE (
        MEDIAN ( fFoto[sinistralidade] );
        REMOVEFILTERS ( dOperadora );
        dOperadora[PORTE] = _porte;
        fFoto[RANKING_OK] = TRUE ()
    )
```
Toda razão é numerador ÷ denominador somados (nunca média de percentuais). Quartis com `PERCENTILE.INC` sobre `fFoto`, só operadoras do ranking.

## Páginas (título = achado; uma pergunta por página)
| # | Página | Pergunta | Visuais centrais |
|---|---|---|---|
| 0 | **Início** | "Procure a sua operadora" | busca, mapa de cobertura por UF, 3 números com comparação |
| 1 | **O lucro vem das aplicações** (gancho) | De onde vem o resultado do setor? | operação × aplicações × lucro, 2021–2025; % de operadoras salvas pelo financeiro |
| 2 | **Quanto da mensalidade volta em atendimento** | Quem gasta mais com o cliente? | ranking por porte/modalidade, tendência 12m, índice combinado |
| 3 | **Quem são os clientes** | A carteira está mudando? | vidas por contratação, 59+, receita e custo por vida, crescimento |
| 4 | **Custo × qualidade** | Gastar mais reduz reclamação? | quadrante sinistralidade × reclamação (mediana do porte), nota ANS, glosa |
| 5 | **Plano de saúde e SUS** | Quando o cliente de plano vai ao SUS? | uso por mil vidas nos 3 grupos (controlado por UF), cobrança × Justiça |
| 6 | **Ficha da operadora** | Como a minha operadora se compara? | todos os indicadores × quartis do porte, motivo se fora do ranking (drill-through + busca) |
| 7 | **Como foi feito** | De onde vêm os números? | fontes, fórmulas, defasagens, ressalvas |

Padrões: "?" em todos os visuais; tabelas com cabeçalho e números ao centro e textos longos à esquerda, sem quebra de linha, com total batendo com o card; clicar filtra a página (sem regras NoFilter).

## Riscos
- **Tamanho do .pbix:** o GitHub aceita até 100 MB por arquivo. `fBeneficiarios` tem 4,5 mi de linhas; se passar do limite, agrego sem sexo ou uso Git LFS.
- **Mapa do Brasil:** em out/2026 a cor por valor não aplicou no mapa de formas via script. Plano B: mapa coroplético nativo ou barras por UF.
- **Identidade visual:** a mesma paleta e as mesmas fontes vão para o Power BI e para a página HTML; defino na primeira página e valido com você.
