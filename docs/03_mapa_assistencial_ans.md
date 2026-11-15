# O "Mapa Assistencial da Saúde Suplementar" da ANS: o que aproveitar

Painel público da ANS (Power BI, ano-base 2025, 34 páginas), olhado em 15/11/2026.
Fonte de tudo: **SIP — Sistema de Informações de Produtos** (produção assistencial informada pelas operadoras, trimestral).

## O que existe em dado aberto e o que não existe

| No painel | Em dado aberto? |
|---|---|
| Eventos, beneficiários e despesa por item assistencial (consultas, exames, terapias, internações, partos, odonto) | **Sim**, `FTP/PDA/SIP/sip_mapa_assistencial_AAAAMM.csv`, 2020T1–2025T4 |
| Recortes por modalidade, porte e contratação | **Sim**: é o grão do arquivo |
| **Seção 4 — "Visão por Operadora"** | **Não.** O arquivo aberto não traz a operadora. |

Ou seja, o dado por operadora (consultas por beneficiário, internações por mil, mix de despesas) só aparece dentro do painel. Opções:
- **Não usar por operadora.** O SIP entra como referência de mercado por modalidade/porte. *(recomendado para a v1)*
- **Pedir à ANS pela Lei de Acesso à Informação** a base do SIP por operadora. É o caminho legítimo; se sair, entra na v2.
- Extrair do Power BI público: **não**. Fere a regra "só arquivos públicos" e não é reproduzível.

**Decisão (15/11/2026): o SIP fica para a v2.** A v1 segue com sinistralidade, beneficiários, cobertura, reclamações/IDSS, glosa e ressarcimento ao SUS.

## O que vale trazer na v2 (checado no arquivo de 2025)

1. **Cesárea.** 79,5% dos partos por plano em 2025 foram cesáreas (338 mil de 426 mil). Varia de 71% (seguradoras) a 83% (cooperativas médicas e filantropia); 83% no individual, 79% no empresarial. Indicador de interesse público, fácil de entender.
2. **Para onde vai o dinheiro.** Internações R$ 128,7 bi (42%), exames R$ 55,9 bi, consultas R$ 38,5 bi, terapias R$ 34,2 bi, outros ambulatoriais R$ 27,1 bi. Uma barra só explica a sinistralidade melhor que qualquer texto.
3. **Custo médio da internação por modalidade.** Seguradora R$ 22,7 mil, autogestão R$ 12,9 mil, medicina de grupo R$ 11,5 mil, cooperativa R$ 10,4 mil, filantropia R$ 8,7 mil. Reflete rede própria/verticalização, mix de casos e região.
4. **Pronto-socorro.** 71 mi de consultas em PS contra 217 mi ambulatoriais em 2025: quase 1 em cada 4 consultas. O painel da ANS mostra subindo de 20,6% (2019) para 24,6% (2025).
5. **Uso por beneficiário por modalidade** (consultas/ano, exames/ano, internações por mil). Explica *por que* a autogestão tem sinistralidade alta: carteira mais velha e mais uso (no painel, 36,5 exames por beneficiário/ano contra 23,5 na média do setor; esses dois números estão no painel, ainda não os recalculei pelo arquivo).
6. **Rastreamento de câncer** (mamografia 50–69 anos, citopatológico 25–59, sangue oculto 50–69). Mede prevenção, mas o denominador precisa de cuidado: conferir se `QT_BENEF_FORA_CARENCIA` do item já é a população-alvo antes de calcular cobertura.

## O que não trazer
- As tabelas longas da Seção 2 (centenas de itens), odontologia detalhada, treemaps.
- Itens por especialidade: o próprio painel avisa que a soma não fecha com o total.

## Por que o painel da ANS é difícil (e o que evitar)
- Títulos dizem o assunto, não o achado ("Consultas Médicas").
- Número sem comparação com nada (5,5 consultas: é muito? pouco?).
- Sigla e código no lugar de pergunta (A.01.07, E1.04.02).
- 34 páginas, sem busca, sem caminho: o usuário precisa saber o que procura.
- A parte mais útil (por operadora) está escondida na última seção e não tem dado aberto.
