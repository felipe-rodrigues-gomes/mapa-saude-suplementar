# Etapa 5 — Página HTML (produto principal)

Pasta `site/`, estática, pronta para o GitHub Pages. Abre sem login, sem framework e sem biblioteca de gráficos.

## Como gerar e ver
```bash
python -I scripts/exportar_site.py                 # dados agregados em site/dados/*.json
python -m http.server 8766 --directory site        # http://localhost:8766
```

## Estrutura
| Seção | Pergunta | O que mostra |
|---|---|---|
| Abertura | De onde vem o lucro? | "O lucro vem das aplicações." + busca da operadora + placar −3,6 × +48,1 × 37,6 (R$ bi, 2021–2025) |
| Resultado | A operação dá lucro? | operação × aplicações × lucro por ano; 20% das operadoras salvas pelas aplicações |
| Mensalidade | Quanto volta em atendimento? | sinistralidade 12 meses (mercado e modalidades) + ranking por porte, modalidade e estado |
| Clientes | Quem tem plano? | mapa de cobertura por UF (toque mostra cobertura, crescimento, concentração), busca por município, contratação desde 2021 |
| Qualidade | Gastar mais reduz reclamação? | dispersão sinistralidade × reclamações (≥ 20 mil clientes), medianas |
| SUS | Ir ao SUS é falha? | três grupos de leitura, motivos, razão por modalidade, cobrança parada na Justiça |
| Sua operadora | Como a minha se compara? | ficha com 16 indicadores e faixa de quartis do porte, resultado, tendência, forma de pagamento, estados |
| Como foi feito | Dá para confiar? | fórmulas, regra do ranking, períodos, conferência com a ANS |

Link direto para uma ficha: `#operadora/<registro ANS>` (ex.: `#operadora/326305`).

## Decisões técnicas
- **Gráficos em SVG escritos à mão** (`site/js/app.js`): nenhuma biblioteca, uma cor com significado por série (coral = operação/perda, verde = aplicações, tinta = mercado/lucro), eixo que não começa em zero sempre avisado.
- **Mapa** pré-projetado em Python a partir da malha do IBGE (caminhos SVG prontos em `clientes.json`), sem biblioteca de mapa.
- **Peso:** a primeira tela usa ~100 KB de dados (mercado, clientes, qualidade, SUS). `operadoras.json` (709 KB, ~150 KB comprimido) carrega em segundo plano depois da primeira pintura; `municipios.json` (220 KB) só quando alguém busca uma cidade.
- **Sem JavaScript**, a página continua legível: os números principais estão escritos no HTML.
- **Acessibilidade:** busca com teclado (setas, Enter, Esc), estados do mapa navegáveis por Tab, tabela escondida com os números do gráfico de resultado, foco visível em todos os controles.
- **Identidade:** a mesma do Power BI (papel, tinta azul-petróleo, coral, verde-azulado, âmbar), fonte Public Sans. Tokens em `site/css/tokens.css`.
- **Quartis da ficha:** mesmas regras das medidas do Power BI (só operadoras do ranking; reclamações só com ≥ 20 mil clientes; glosa sem valores improváveis).

## Verificação (15/11/2026)
- Navegador: 1280×800 e 375×812 (celular), sem rolagem lateral, sem erro no console, busca por teclado ("unimed fortal" → ficha), âncoras do menu no lugar certo.
- Verificador de design (Hallmark `sloplint`): 0 falha; 2 avisos registrados no topo do `site.css` (volume de texto de um site de dados; contraste de texto sobre o verde, que não existe na página).

## Falta
- Links do rodapé "Código no GitHub" e "Quem fez" apontam para `#`, à espera do endereço do repositório e do seu LinkedIn.
- Publicação no GitHub Pages (etapa 6, junto com o README).
