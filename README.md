🔍 Detecção de Duplicidade de Pagamentos — Python + Pandas

Programa em Python que analisa uma base de pagamentos a fornecedores de serviços linguísticos (LSPs) e aponta os pagamentos que podem ter sido feitos em duplicidade, classificando cada caso por nível de risco.

⚠️ Projeto educacional. Os dados são inteiramente fictícios. Os alertas são indícios para investigação: não confirmam fraude nem devem ser usados para bloquear pagamentos automaticamente.

Por que este projeto existe

Pagar a mesma fatura duas vezes é um erro comum e caro. Ele raramente aparece como uma cópia perfeita: o número da nota vem com um traço a mais, o nome do fornecedor está escrito de outro jeito, o pagamento cai alguns dias depois. Este projeto mostra como encontrar esses casos "disfarçados" com regras claras e explicáveis.

O que o projeto demonstra
Identificação confiável do fornecedor: usa o identificador fiscal (CNPJ/Tax ID), padronizado, como referência principal. O nome do fornecedor só é usado quando o identificador não está disponível, porque nomes costumam ter variações ("Acme Ltda", "ACME LTDA.").
Precisão nos valores: trabalha com valores em centavos inteiros (R$ 1.234,56 vira 123456). Isso evita os pequenos erros de arredondamento que o computador comete com números decimais.
Regras que se complementam: compara fornecedor, valor (exato ou próximo), intervalo entre datas, número da nota (igual ou parecido) e possíveis pagamentos parciais.
Priorização por risco: cada alerta recebe uma pontuação e um nível de prioridade, com a explicação de quais regras foram acionadas.

Inclui também testes automatizados, dados de exemplo e um CSV de alertas gerado pelo programa.

Como as regras funcionam
Regra	Quando dispara	Força do indício
Correspondência forte	Mesmo fornecedor, mesma moeda, mesmo valor e datas próximas, mas com números de nota diferentes	Alta
Nota igual ou semelhante	Números de nota iguais ou quase iguais (ex.: NF-1023 e NF1023). Pode ser reenvio da fatura, formatação diferente ou erro de digitação	Alta
Valor próximo	Valores parecidos dentro de uma tolerância configurável	Fraca: pode gerar alarmes falsos
Possível pagamento parcial	Vários pagamentos com a mesma referência de serviço e valores diferentes	Requer validação: como a base não tem o valor original da fatura, o programa não consegue confirmar se a soma bate
Pontuação de risco

Cada regra acionada soma pontos ao alerta, e o total define o nível de prioridade. A pontuação é explicável e ajustável: dá para ver exatamente por que um caso recebeu aquela nota e mudar os pesos conforme a política da empresa. Não é um modelo estatístico treinado.

Formato da base
Coluna	Descrição
payment_id	Identificador único do pagamento
supplier_tax_id	Identificador fiscal do fornecedor (fictício)
supplier_name	Nome do fornecedor
invoice_number	Número da nota ou fatura
invoice_date	Data da nota, no formato AAAA-MM-DD
payment_date	Data do pagamento, no formato AAAA-MM-DD
amount_cents	Valor em centavos inteiros (ex.: R$ 1.234,56 = 123456)
currency	Código da moeda, por exemplo BRL
purchase_order	Pedido de compra, se houver
service_reference	Referência do serviço, se houver
payment_status	Situação do pagamento, por exemplo PAID, PENDING ou REVERSED

Como executar

Pré-requisito: Python 3.10 ou superior.

1. Instale as dependências

bash
python -m pip install -r requirements.txt

2. Rode o detector (a partir da pasta principal do projeto)

bash
python src/detector.py

O script lê data/pagamentos_ficticios.csv, mostra os alertas na tela e salva o resultado em outputs/alertas.csv.

Rodando os testes
bash
python -m unittest discover -s tests -v
Estrutura do projeto
deteccao_duplicidade_pagamentos/
├── data/
│   └── pagamentos_ficticios.csv   # pagamentos fictícios, com duplicidades escondidas
├── outputs/
│   └── alertas_exemplo.csv        # exemplo de alertas gerados
├── src/
│   └── detector.py                # lógica de detecção e pontuação
├── tests/
│   └── test_detector.py           # testes automatizados
├── .gitignore
├── requirements.txt
└── README.md
Limitações e próximos passos para uso real
Validar o formato do identificador fiscal e das moedas de acordo com os sistemas da empresa.
Ajustar, junto com a área financeira, o intervalo de datas, a tolerância de valores e as demais regras de negócio.

Antonio Aguiar · GitHub · LinkedIn
