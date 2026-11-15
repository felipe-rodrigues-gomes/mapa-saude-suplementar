# Princípios do projeto

**O que é:** os dados públicos da ANS sobre planos de saúde, finalmente legíveis. Mesmo dado que a ANS publica, apresentado para quem precisa decidir alguma coisa.

**Para quem:** quem trabalha no setor (operadoras, prestadores, consultorias, corretores), jornalistas e o beneficiário curioso. Funciona como cartão de visitas: precisa ser útil de verdade, não só bonito.

## Regras de desenho (valem para o Power BI e para a página)

1. **O título diz o achado, não o assunto.** "Medicina de grupo gasta 77% do que recebe; autogestão, 93%", e não "Sinistralidade por modalidade".
2. **Todo número vem com uma comparação.** Nunca "82,4%" sozinho: "82,4%, 3 pontos acima das operadoras do mesmo porte".
3. **Termo técnico vira pergunta em português.**
   - Sinistralidade → "Quanto da mensalidade volta em atendimento"
   - IDSS → "Nota da ANS (0 a 1)"
   - IGR → "Reclamações por 100 mil clientes"
   - Glosa → "Quanto da conta do hospital/clínica a operadora recusa"

   A sigla técnica fica no "?" de cada visual.
4. **A busca vem primeiro.** A tela de entrada é "procure a sua operadora" + o mapa; os rankings vêm depois.
5. **Uma pergunta por tela, poucos visuais, celular primeiro.** O que não cabe na tela do celular não entra.
6. **Avisar quando o dado não é confiável, em vez de esconder.** Glosa perto de 0% = "provável falha de envio à ANS"; operadora pequena = "poucos clientes, o índice oscila".

## Regras de dado

- Só fontes públicas: ANS e, para a população, IBGE. Nenhum dado ou conhecimento interno de qualquer operadora.
- Todas as operadoras seguem o mesmo critério: nenhuma é poupada nem destacada fora da regra.
- Cada indicador traz a fórmula, a fonte, o período e a data da carga na nota metodológica.
