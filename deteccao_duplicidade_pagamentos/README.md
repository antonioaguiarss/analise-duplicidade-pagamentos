# Detecção de Duplicidade de Pagamentos — Python + Pandas

Projeto demonstrativo de controle financeiro para identificar pagamentos potencialmente duplicados a fornecedores de serviços linguísticos (LSPs).

> **Aviso:** dados inteiramente fictícios. Os alertas são indícios para investigação, não confirmação de fraude nem instrução para bloquear pagamentos automaticamente.

## O que o projeto demonstra

1. **Identificação confiável do fornecedor:** prioriza um identificador fiscal normalizado (CNPJ/Tax ID); usa nome normalizado apenas como fallback quando o ID não está disponível.
2. **Precisão monetária:** lê valores em centavos inteiros para evitar erros de ponto flutuante.
3. **Regras complementares:** compara fornecedor, valor exato ou valor próximo, janela de datas, número de nota igual/semelhante e possíveis pagamentos parciais.
4. **Priorização de risco:** atribui pontuação explicável e nível de prioridade, sem afirmar que uma duplicidade foi confirmada.

Também inclui testes automatizados, dados de exemplo e um CSV de alertas gerado pelo programa.

## Estrutura

```text
deteccao_duplicidade_pagamentos/
├── data/
│   └── pagamentos_ficticios.csv
├── outputs/
│   └── alertas_exemplo.csv
├── src/
│   └── detector.py
├── tests/
│   └── test_detector.py
├── .gitignore
├── requirements.txt
└── README.md
```

## Requisitos

- Python 3.10+
- pandas

Instale as dependências:

```bash
python -m pip install -r requirements.txt
```

## Executar

Na raiz do projeto:

```bash
python src/detector.py
```

O script lê `data/pagamentos_ficticios.csv`, imprime os alertas e salva `outputs/alertas.csv`.

Executar os testes:

```bash
python -m unittest discover -s tests -v
```

## Formato da base

| Coluna | Descrição |
|---|---|
| `payment_id` | Identificador único do registro de pagamento |
| `supplier_tax_id` | Identificador fiscal fictício do fornecedor |
| `supplier_name` | Nome do fornecedor |
| `invoice_number` | Número da nota/fatura |
| `invoice_date` | Data da nota/fatura, formato `AAAA-MM-DD` |
| `payment_date` | Data do pagamento, formato `AAAA-MM-DD` |
| `amount_cents` | Valor em centavos inteiros (ex.: R$ 1.234,56 = `123456`) |
| `currency` | Código da moeda, por exemplo `BRL` |
| `purchase_order` | Pedido/ordem de compra, se disponível |
| `service_reference` | Referência do serviço, se disponível |
| `payment_status` | Ex.: `PAID`, `PENDING`, `REVERSED` |

## Como interpretar as regras

- **Correspondência forte:** mesmo fornecedor fiscal, mesma moeda, mesmo valor e datas próximas, com notas diferentes.
- **Nota igual ou semelhante:** pode indicar reenvio de fatura, variação de formatação ou erro de digitação.
- **Valor próximo:** usa tolerância configurável; é um indício mais fraco e pode produzir falsos positivos.
- **Possíveis pagamentos parciais:** identifica grupos com a mesma referência de serviço e valores diferentes. Como a base demonstrativa não inclui o valor original da fatura, o sistema não confirma que a soma corresponde à fatura; o alerta pede validação documental.
- **Pontuação de risco:** explicável e ajustável. Não é um modelo estatístico treinado.

## Limitações e próximos passos para produção

- Validar o identificador fiscal e a moeda conforme os sistemas da empresa.
- Ajustar janelas de datas, tolerância de valores e regras de negócio com a área financeira.
- Tratar estornos, pagamentos em lote, impostos, retenções, adiantamentos e faturas parceladas.
- Restringir acesso aos dados, registrar decisões dos analistas e medir falsos positivos.
- Em bases grandes, substituir a comparação par a par por blocagem/índices para reduzir custo computacional.
- Não subir dados reais, CNPJs reais, nomes de clientes ou informações bancárias para repositórios públicos.

## Ideias de evolução

- Dashboard com volume e valor de alertas por mês.
- Pipeline agendado e integração com ERP.
- Registro de desfecho do alerta (`confirmado`, `legítimo`, `inconclusivo`) para calibrar regras.
