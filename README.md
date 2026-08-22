# Pipeline de Dados Educacionais do INEP

Este projeto é desenvolvido como parte de um Trabalho de Conclusão de Curso em Engenharia da Computação.

O objetivo principal é desenvolver uma pipeline computacional para processamento e análise de dados públicos educacionais do INEP, com foco em ingestão, auditoria, limpeza, padronização, consolidação e geração de bases analíticas.

A geração de indicadores derivados, como um possível indicador de vulnerabilidade escolar, será tratada como aplicação posterior da pipeline, e não como o foco central inicial do projeto.

## Fonte dos dados

Os dados utilizados são obtidos manualmente a partir do portal oficial do INEP, especialmente a base de Taxas de Rendimento Escolar em nível de escola.

A pipeline não realiza web scraping nem download automático dos dados.

## Organização dos dados

Os arquivos oficiais baixados devem ser colocados em:

```text
data/raw/taxas_rendimento_escolar/
```

## Estrutura simplificada

Para entender o projeto rapidamente, consulte:

- `docs/guia_estrutura_projeto.md`
- `docs/diario_tecnico.md`
- `docs/decisoes_metodologicas.md`

As partes principais do projeto são:

```text
src/pipeline/    código das etapas da pipeline
docs/            documentação do TCC
data/            dados brutos e intermediários
outputs/         relatórios gerados
main.py          execução da pipeline
```
