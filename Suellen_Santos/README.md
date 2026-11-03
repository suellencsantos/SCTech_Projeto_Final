# Crédito às pessoas físicas: juros e inadimplência

- **Curso:** Visualização de Dados e BI.
- **Turma:** T1.
- **Professor:** Rodrigo Garcia Brunini.
- **Atividade:** Projeto Avaliativo do Módulo 2.

Aplicação de Business Intelligence desenvolvida em Python e Streamlit para acompanhar a evolução dos juros e da inadimplência do crédito livre às pessoas físicas no Brasil. O projeto usa quatro séries mensais públicas do Banco Central do Brasil (BCB), cobre janeiro de 2012 a agosto de 2026 e oferece filtros, indicadores, estatísticas descritivas, análise de correlação e comparação de defasagens.

## 1. Problema, objetivo e importância

**Pergunta orientadora:** como os juros do crédito pessoal e do cartão e a inadimplência das pessoas físicas evoluíram no Brasil, e que associação temporal aparece entre o custo do crédito e os atrasos superiores a 90 dias?

O tema é relevante para profissionais de crédito, risco, planejamento financeiro, educação financeira e análise econômica. O objetivo é transformar séries extensas em uma leitura acessível, reproduzível e interativa. O painel não recomenda produtos financeiros nem estima risco individual.

## 2. Escopo e resultados esperados

O projeto analisa:

- juros anuais médios de novas operações de crédito pessoal e cartão;
- percentual inadimplente da carteira livre total das pessoas físicas e do cartão;
- níveis, variações, médias, extremos e tendências mensais e anuais;
- correlação de Pearson contemporânea;
- correlação exploratória entre juros no mês `t` e inadimplência até 12 meses depois.

Ficam fora do escopo: previsão, inferência causal, avaliação de consumidores, segmentação por renda ou região, crédito direcionado e recomendação de política pública. O trabalho é concluído quando o ETL é reproduzível, os controles de qualidade passam e a aplicação permite responder à pergunta com os recortes disponíveis.

## 3. Fonte, licença e método de obtenção

Os dados são públicos, agregados e publicados pelo **Banco Central do Brasil - Departamento de Estatísticas**, no Sistema Gerenciador de Séries Temporais (SGS). O catálogo informa licença **Open Data Commons Open Database License (ODbL)**. Acesso consultado em 21 de outubro de 2026.

| Código SGS | Série                                                        | Unidade | Catálogo oficial                                                                                                                                 |
| ----------- | ------------------------------------------------------------- | ------- | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| 20748       | Juros - pessoas físicas - crédito pessoal total             | % a.a.  | [BCB](https://dadosabertos.bcb.gov.br/dataset/20748-taxa-media-de-juros-das-operacoes-de-credito-com-recursos-livres---pessoas-fisicas---credito-) |
| 21112       | Inadimplência - pessoas físicas - total                     | %       | [BCB](https://dadosabertos.bcb.gov.br/dataset/21112-inadimplencia-da-carteira-de-credito-com-recursos-livres---pessoas-fisicas---total)            |
| 21129       | Inadimplência - pessoas físicas - cartão de crédito total | %       | [BCB](https://dadosabertos.bcb.gov.br/dataset/21129-inadimplencia-da-carteira-de-credito-com-recursos-livres---pessoas-fisicas---cartao-de-credit) |
| 22024       | Juros - pessoas físicas - cartão de crédito total          | % a.a.  | [BCB](https://dadosabertos.bcb.gov.br/dataset/22024-taxa-media-de-juros-das-operacoes-de-credito-com-recursos-livres---pessoas-fisicas---cartao-d) |

O arquivo foi obtido por download público no BCB-DSTAT e fornecido em CSV. Esse método é aceito pelo escopo do projeto por ser um arquivo público de fonte oficial com a forma de obtenção documentada. O pipeline preserva uma cópia bruta, a impressão digital SHA-256 e a identificação das séries. Não há dados pessoais, sensíveis ou credenciais.

## 4. Pipeline e metodologia

```mermaid
flowchart LR
    A[CSV público BCB-DSTAT] --> B[Extração local]
    B --> C[Validação de estrutura]
    C --> D[Conversão de datas e números]
    D --> E[Controles de qualidade]
    E --> F[CSV processado]
    F --> G[EDA e estatística]
    G --> H[Painel Streamlit]
```

O ETL executado em `src/data_pipeline.py`:

1. detecta a codificação e lê o CSV separado por ponto e vírgula;
2. reconhece as séries pelos códigos SGS, sem depender do texto completo do cabeçalho;
3. separa a linha final de fonte das observações mensais;
4. converte `mmm/aa` em data e a vírgula decimal em número;
5. valida campos obrigatórios, valores ausentes, datas duplicadas e lacunas mensais;
6. grava a base processada e um relatório de qualidade com o hash do arquivo original.

A EDA calcula estatísticas de posição e dispersão, extremos, variações em pontos percentuais, médias anuais e correlações. A análise de defasagem correlaciona juros em `t` com inadimplência em `t + k`, para `k` de 0 a 12 meses. Essa comparação é exploratória e não constitui um teste causal.

## 5. Bibliotecas e tecnologias

- [Python](https://www.python.org/) - linguagem do pipeline, testes e aplicação;
- [pandas](https://pandas.pydata.org/docs/) - leitura, transformação e análise tabular;
- [NumPy](https://numpy.org/doc/) - ajuste linear e operações numéricas;
- [Plotly](https://plotly.com/python/) - gráficos interativos;
- [Streamlit](https://docs.streamlit.io/) - interface, filtros, métricas e publicação;
- `unittest` - testes do pipeline e dos resultados de referência;
- Git e GitHub - versionamento e publicação do código.

As dependências de produção estão fixadas em `requirements.txt` para tornar o deploy reproduzível.

## 6. Resultados encontrados

Após o tratamento, a base contém **176 meses completos**, sem lacunas, ausências ou datas duplicadas.

- Em **agosto de 2026**, último mês disponível, os juros eram **52,59% a.a.** no crédito pessoal e **97,77% a.a.** no cartão. Em 12 meses, as variações foram +3,25 e +6,00 pontos percentuais, respectivamente.
- A inadimplência total das pessoas físicas chegou a **8,01%**, e a inadimplência do cartão a **9,96%** em agosto de 2026. Ambos são os maiores valores do recorte e aumentaram 1,04 e 1,00 ponto percentual em 12 meses.
- No período completo, a correlação contemporânea entre juros do crédito pessoal e inadimplência total foi **0,488**. Para cartão, juros e inadimplência apresentaram correlação **0,680**.
- Entre as defasagens testadas, a maior correlação absoluta ocorreu em **3 meses** para crédito pessoal versus inadimplência total (`r = 0,528`) e em **1 mês** para cartão (`r = 0,683`).
- Os menores níveis do recorte concentram-se entre 2020 e 2021. A inadimplência total atingiu 4,09% em março de 2021, e a do cartão, 3,79% em abril de 2021. Essa coincidência temporal exige contexto adicional e não deve ser lida isoladamente.

## 7. Discussão e conclusão

Os dados sustentam três conclusões descritivas. Primeiro, o custo e a inadimplência do crédito cresceram de forma relevante após os níveis baixos de 2020-2021. Segundo, o cartão manteve juros e inadimplência superiores aos indicadores comparáveis do crédito pessoal na maior parte do recorte. Terceiro, as associações positivas e as defasagens curtas justificam monitoramento conjunto, mas não provam que uma série cause a outra.

Juros representam novas concessões ponderadas pelo valor contratado; inadimplência representa o estoque com atraso superior a 90 dias. Além disso, inflação, renda, emprego, composição da carteira, renegociações, regulação e condições macroeconômicas não foram controlados. Uma interpretação causal exigiria variáveis adicionais e desenho estatístico apropriado.

## 8. Aplicação profissional

O pipeline pode apoiar uma área de risco, planejamento ou inteligência de mercado como painel de contexto macro de crédito. Para uso corporativo, recomenda-se:

- atualização automatizada pela API BCData/SGS e monitoramento de falhas;
- catálogo de dados, versionamento, validações e responsáveis definidos;
- acompanhamento de revisões metodológicas do BCB;
- testes de regressão para métricas e gráficos;
- controle de acesso caso sejam adicionados dados internos;
- separação explícita entre indicadores agregados e decisões sobre clientes.

## 9. Aplicação Streamlit

**Deploy:** [sctechprojetofinal-suellensantos.streamlit.app](https://sctechprojetofinal-suellensantos.streamlit.app/)

Funcionalidades:

- seleção de período;
- alternância entre crédito pessoal e cartão;
- métricas com variação em 12 meses;
- séries mensais e médias anuais;
- dispersão, tendência linear e correlação;
- análise interativa de defasagem de 0 a 12 meses;
- estatísticas descritivas, dicionário, metodologia e limitações;
- download do recorte filtrado.

## 10. Como executar

Pré-requisitos: Git e Python 3.12.

```bash
python -m venv .venv
```

No Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m src.data_pipeline
python -m unittest discover -s tests -v
streamlit run app.py
```

No Linux ou macOS:

```bash
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m src.data_pipeline
python -m unittest discover -s tests -v
streamlit run app.py
```

A aplicação usa caminhos relativos à raiz e não exige variáveis de ambiente. Para refazer o ETL com outro arquivo compatível:

```bash
python -m src.data_pipeline --input caminho/arquivo.csv
```

## 11. Estrutura de pastas

```text

├── .streamlit/
│   └── config.toml
├── data/
│   ├── processed/
│   │   └── credito_pf_mensal.csv
│	│		et_report.json
│   └──── raw/
│      └── bcb_series_credito_pf.csv
├── scripts/
│   └── build_data.py
├── src/
│   ├── analysis.py
│   ├── charts.py
│   └── data_pipeline.py
│── tests/
│   └── test_pipeline.py
├── app.py
├── requirements.txt
├── README.md
```

O CSV original fornecido pode permanecer na raiz para rastreabilidade; o ETL cria a cópia canônica em `data/raw/`.

## 12. Limitações e melhorias futuras

- o recorte termina em agosto de 2026 e o último ano está incompleto;
- as quatro séries são agregadas e não permitem segmentar consumidores;
- correlação bruta entre séries temporais pode ser elevada por tendências e autocorrelação;
- as definições de juros e inadimplência usam bases conceituais diferentes;
- a análise não controla variáveis macroeconômicas nem mudanças regulatórias;
- o CSV é uma fotografia e não recebe atualizações automáticas.

Melhorias: coleta via API do SGS, deflatores e variáveis macroeconômicas, testes de estacionariedade, modelos com defasagens distribuídas, detecção de quebras estruturais e alertas de atualização.

## 13. Créditos e referências

- [Banco Central do Brasil - Portal de Dados Abertos](https://dadosabertos.bcb.gov.br/)
- [Sistema Gerenciador de Séries Temporais - SGS](https://www3.bcb.gov.br/sgspub/)
- [Documentação do Streamlit](https://docs.streamlit.io/)
- [Documentação do pandas](https://pandas.pydata.org/docs/)
- [Documentação do Plotly para Python](https://plotly.com/python/)

Projeto acadêmico desenvolvido individualmente. Fontes, bibliotecas e decisões analíticas estão identificadas para permitir auditoria e reprodução.

## 14. Links de entrega

| Item                          | Link                                                                                                                                                                                                                              |
| ----------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Repositório pessoal          | [github.com/suellencsantos/SCTech_Projeto_Final/tree/743a2e8e4c558c9fe0ee55a68b2d041fd7b81bb3/Suellen_Santos](https://github.com/suellencsantos/SCTech_Projeto_Final/tree/743a2e8e4c558c9fe0ee55a68b2d041fd7b81bb3/Suellen_Santos) |
| Aplicação publicada         | [sctechprojetofinal-suellensantos.streamlit.app](https://sctechprojetofinal-suellensantos.streamlit.app/)                                                                                                                          |
| Repositório oficial da turma | `INSERIR_LINK_DA_TURMA`                                                                                                                                                                                                         |
