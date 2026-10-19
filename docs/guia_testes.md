# Testes

Os testes criam exemplos pequenos e verificam se a pipeline segue suas regras. Cada função em `tests/` tem uma explicação do problema simulado e do resultado esperado.

| Arquivo | O que verifica | Casos |
| --- | --- | ---: |
| `test_consolidacao.py` | Tipos, ausências, duplicidades, preservação do histórico e publicação dos arquivos. | 18 |
| `test_camada_analitica.py` | Significado das métricas, versões históricas e relacionamentos. | 21 |
| `test_persistencia.py` | Captura dos arquivos, validações, carga transacional e município canônico. | 43 |

São **40 funções e 82 casos**: algumas funções são repetidas com exemplos diferentes. Destes, 59 não precisam de banco e 23 usam PostgreSQL.

## Como ler

O teste de duplicidade, por exemplo, cria duas observações da mesma escola no mesmo ano e espera que a publicação seja bloqueada. Ele impede contar a mesma observação duas vezes.

`assert` confere um resultado; `pytest.raises` confere se um erro esperado foi levantado. `tmp_path` fornece uma pasta temporária. `monkeypatch` simula temporariamente situações como uma falha na gravação. Os recursos de preparação, chamados fixtures, não são testes adicionais.

## Executar

Na raiz do projeto, com as dependências de desenvolvimento instaladas:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Por padrão, os 23 casos de integração são pulados. Para executá-los também:

```powershell
$env:INEP_TEST_INTEGRATION = '1'
.\.venv\Scripts\python.exe -m pytest -q
Remove-Item Env:INEP_TEST_INTEGRATION
```

A integração exige PostgreSQL e `.env` configurados. Usa dados artificiais em schemas descartáveis, sem substituir as tabelas analíticas de produção. Para acompanhar um teste em detalhe:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_consolidacao.py -k duplicidade_entre_lotes -v
```

## Limites

Estes arquivos se concentram nas etapas 5 e 6. Não testam o dashboard, as medidas DAX ou todo o comportamento das etapas 1–4. As simulações de falhas cobrem situações específicas, não qualquer interrupção possível. Os testes do catálogo conferem as regras codificadas; interpretar os cabeçalhos do INEP e validar a publicação real continuam sendo verificações separadas.
