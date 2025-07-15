# 🚀 Guia de Deploy Passo a Passo - Solução de Sniping de Memecoins

Este guia detalhado irá conduzi-lo através do processo de deploy da solução completa de sniping de memecoins na blockchain Solana em sua conta Amazon Web Services (AWS), com foco na detecção de tokens migrados da Pump.Fun para a **PumpSwap**. A solução é composta por múltiplos agentes inteligentes, uma infraestrutura robusta como código (IaC) e um dashboard web para monitoramento. Seguir este guia passo a passo garantirá que todos os componentes sejam configurados corretamente e que a solução esteja pronta para operar em um ambiente de produção.

## Introdução

### O que você vai aprender:

1.  **Preparação do Ambiente**: Como configurar sua conta AWS e o AWS CLI.
2.  **Deploy da Infraestrutura**: Como provisionar todos os recursos AWS necessários usando CloudFormation.
3.  **Configuração de Credenciais**: Como armazenar suas chaves de API sensíveis de forma segura no AWS Secrets Manager.
4.  **Deploy dos Agentes**: Como empacotar e implantar as funções AWS Lambda que executam a lógica dos agentes.
5.  **Deploy do Dashboard**: Como colocar o dashboard web no ar para monitorar suas operações.
6.  **Verificação Pós-Deploy**: Como confirmar que todos os componentes estão funcionando corretamente.

### Pré-requisitos

Antes de iniciar o processo de deploy, certifique-se de ter os seguintes pré-requisitos:

*   **Conta AWS Ativa**: Uma conta AWS com acesso administrativo. Se você não tiver uma, crie uma em [aws.amazon.com](https://aws.amazon.com/).
*   **AWS CLI Instalado e Configurado**: O AWS Command Line Interface deve estar instalado em sua máquina local e configurado com as credenciais de um usuário IAM que tenha permissões para criar e gerenciar recursos na AWS (preferencialmente `AdministratorAccess` para o deploy inicial, que pode ser refinado posteriormente). Para instruções de instalação e configuração, consulte a documentação oficial da AWS CLI [aqui](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html).
*   **Python 3.9+**: Certifique-se de ter o Python 3.9 ou superior instalado em sua máquina. Você pode baixá-lo em [python.org](https://www.python.org/downloads/).
*   **Git Instalado**: Para clonar o repositório do projeto. Se não tiver, instale-o em [git-scm.com](https://git-scm.com/downloads).
*   **Chaves de API Necessárias**: Você precisará obter as chaves de API para os seguintes serviços. Guarde-as em um local seguro, pois elas serão usadas na configuração do Secrets Manager:
    *   **Helius API**: Essencial para o Agente Discoverer. Obtenha em [helius.xyz](https://helius.xyz/).
    *   **Twitter API (Opcional)**: Para análise de sentimento. Obtenha em [developer.twitter.com](https://developer.twitter.com/).
    *   **Telegram Bot Token**: Para notificações. Crie um bot via `@BotFather` no Telegram.
    *   **Chave Privada da Carteira Solana**: Para live trading. **Extremamente sensível!** Exporte da sua carteira Solana (Phantom, Solflare, etc.). Use uma carteira dedicada para esta solução com um saldo mínimo para testes.

### Estrutura do Projeto

Este guia assume que você clonou o repositório da solução. A estrutura de diretórios relevante para o deploy é a seguinte:

```
memecoin-sniping-solution/
├── src/                          # Código dos agentes (Lambda functions)
│   ├── discoverer/
│   ├── analyzer/
│   ├── trader/
│   ├── optimizer/
│   └── mitigation/               # Novas estratégias de mitigação
├── iac/                         # Infraestrutura como Código (CloudFormation)
│   └── cloudformation/
│       ├── sqs.yaml
│       ├── dynamodb.yaml
│       ├── lambda.yaml
│       ├── s3.yaml
│       ├── secrets_manager.yaml
│       ├── sns.yaml
│       ├── eventbridge.yaml
│       └── monitoring.yaml
│   └── deploy.sh                  # Script de deploy da infraestrutura
├── dashboard/                   # Dashboard web (Flask)
│   └── src/
│       ├── main.py
│       ├── routes/
│       └── static/
├── scripts/                     # Scripts de automação
│   ├── deploy_infrastructure.sh
│   ├── package_lambda.sh
│   └── setup_monitoring.sh
└── .github/workflows/           # CI/CD GitHub Actions (opcional para deploy manual)
    └── deploy.yml
```

Com os pré-requisitos atendidos e a estrutura do projeto compreendida, você está pronto para iniciar o processo de deploy.

---

*Autor: Manus AI*
*Data: 7 de Julho de 2025*



## 1. Deploy da Infraestrutura AWS (CloudFormation)

O primeiro passo crucial é provisionar toda a infraestrutura AWS necessária para a solução. Isso é feito usando o AWS CloudFormation, que permite definir todos os recursos como código (Infrastructure as Code - IaC). A solução já vem com templates CloudFormation pré-configurados para todos os serviços AWS que ela utiliza.

### 1.1. Clonar o Repositório do Projeto

Se você ainda não o fez, clone o repositório da solução para sua máquina local. Abra seu terminal ou prompt de comando e execute:

```bash
git clone https://github.com/seu-usuario/memecoin-sniping-solution.git # Substitua pela URL do seu repositório
cd memecoin-sniping-solution
```

### 1.2. Tornar os Scripts Executáveis

Os scripts de deploy e empacotamento são arquivos shell (`.sh`). Para que você possa executá-los, é necessário conceder permissões de execução. Navegue até o diretório raiz do projeto clonado e execute o seguinte comando:

```bash
chmod +x scripts/*.sh
```

Este comando garante que todos os scripts dentro do diretório `scripts/` sejam executáveis.

### 1.3. Executar o Script de Deploy da Infraestrutura

O script `scripts/deploy_infrastructure.sh` é responsável por orquestrar o deploy de todos os templates CloudFormation. Ele cria as filas SQS, tabelas DynamoDB, buckets S3, secrets no Secrets Manager (apenas os nomes, os valores serão adicionados depois), e configura as permissões IAM necessárias para os agentes Lambda.

No terminal, a partir do diretório raiz do projeto, execute:

```bash
./scripts/deploy_infrastructure.sh <ambiente>
```

Substitua `<ambiente>` por um nome que identifique seu ambiente, por exemplo, `dev`, `staging` ou `prod`. Este nome será usado para prefixar os nomes dos recursos na AWS, ajudando na organização. Por exemplo:

```bash
./scripts/deploy_infrastructure.sh dev
```

#### O que o script faz:

1.  **Criação de Stacks CloudFormation**: O script executa comandos `aws cloudformation deploy` para cada template YAML localizado em `iac/cloudformation/`. Cada template define um conjunto de recursos relacionados (ex: `sqs.yaml` para filas SQS, `dynamodb.yaml` para tabelas DynamoDB, etc.).
2.  **Criação de Recursos**: Serão criados os seguintes recursos na sua conta AWS:
    *   **Filas SQS**: Uma fila para o Agente Discoverer e outra para o Agente Analyzer.
    *   **Tabelas DynamoDB**: Uma tabela para o Agente Trader (para registrar trades) e outra para o Agente Optimizer (para otimizações).
    *   **Buckets S3**: Um bucket para armazenar o código dos Lambda functions e outro para configurações e backups.
    *   **Secrets Manager**: Criação dos nomes dos secrets para as chaves de API (Helius, Twitter, Telegram, Solana Wallet). **Neste ponto, apenas os nomes dos secrets são criados; os valores serão inseridos na próxima etapa.**
    *   **Tópicos SNS**: Para notificações de alerta.
    *   **Regras EventBridge**: Para agendar a execução do Agente Optimizer.
    *   **Roles IAM**: Criação de perfis de execução (IAM Roles) com as permissões mínimas necessárias para cada função Lambda interagir com os outros serviços AWS.

#### Tempo de Execução

O deploy da infraestrutura pode levar alguns minutos (geralmente de 5 a 15 minutos), dependendo da região da AWS e da complexidade dos recursos. O script exibirá o progresso no terminal. Em caso de erros, o CloudFormation tentará reverter as alterações para um estado consistente. Você pode monitorar o progresso e quaisquer erros no console do AWS CloudFormation, na seção 


de \'Eventos\' da stack correspondente.

Após a conclusão bem-sucedida desta etapa, sua infraestrutura AWS estará pronta para receber o código dos agentes e as configurações. O próximo passo é popular o AWS Secrets Manager com suas chaves de API sensíveis.



## 2. Configuração das Chaves de API no AWS Secrets Manager

Com a infraestrutura AWS provisionada, o próximo passo é armazenar suas chaves de API sensíveis no AWS Secrets Manager. Este serviço garante que suas credenciais sejam criptografadas e gerenciadas de forma segura, sem a necessidade de incluí-las diretamente no código ou em arquivos de configuração expostos.

### 2.1. Entendendo os Secrets Criados

O script `deploy_infrastructure.sh` já criou os "esqueletos" (nomes) dos secrets que a solução espera encontrar. São eles:

*   `/memecoin-sniping/helius-api-key`
*   `/memecoin-sniping/solana-wallet-private-key`
*   `/memecoin-sniping/twitter-api-secrets` (opcional)
*   `/memecoin-sniping/telegram-api-secret`

Agora, você precisará preencher esses secrets com os valores reais das suas chaves de API que você obteve nos pré-requisitos.

### 2.2. Inserindo os Valores dos Secrets

Utilize o comando `aws secretsmanager put-secret-value` para inserir o conteúdo JSON de cada secret. Certifique-se de substituir os placeholders (`SUA_CHAVE_API_HELIUS`, `SEU_CONSUMER_KEY`, etc.) pelos seus valores reais e de usar a `sua-regiao-aws` correta (a mesma que você usou para o deploy da infraestrutura).

#### 2.2.1. Helius API Key

Esta chave é essencial para o Agente Discoverer monitorar novos tokens na blockchain Solana.

```bash
aws secretsmanager put-secret-value \
    --secret-id /memecoin-sniping/helius-api-key \
    --secret-string \'{"apiKey":"SUA_CHAVE_API_HELIUS"}\' \
    --region sua-regiao-aws
```

#### 2.2.2. Solana Wallet Private Key

**ATENÇÃO: Esta é a chave mais crítica!** Ela permite que o Agente Trader execute transações reais com seus fundos. Manuseie-a com extrema cautela. Certifique-se de que o formato da chave privada (hexadecimal ou base58) é compatível com a biblioteca `solana.py` e que você está usando uma carteira dedicada para esta solução com um saldo mínimo para testes.

```bash
aws secretsmanager put-secret-value \
    --secret-id /memecoin-sniping/solana-wallet-private-key \
    --secret-string \'{"privateKey":"SUA_CHAVE_PRIVADA_SOLANA"}\' \
    --region sua-regiao-aws
```

#### 2.2.3. Twitter API Secrets (Opcional)

Se você deseja que o Agente Analyzer utilize a análise de sentimento do Twitter, insira suas credenciais aqui. Caso contrário, você pode pular esta etapa, mas a funcionalidade de análise de sentimento será limitada.

```bash
aws secretsmanager put-secret-value \
    --secret-id /memecoin-sniping/twitter-api-secrets \
    --secret-string \'{"consumerKey":"SEU_CONSUMER_KEY","consumerSecret":"SEU_CONSUMER_SECRET","accessToken":"SEU_ACCESS_TOKEN","accessTokenSecret":"SEU_ACCESS_TOKEN_SECRET"}\' \
    --region sua-regiao-aws
```

#### 2.2.4. Telegram Bot Token

Para receber notificações em tempo real sobre trades e alertas do sistema, insira o token do seu bot do Telegram.

```bash
aws secretsmanager put-secret-value \
    --secret-id /memecoin-sniping/telegram-api-secret \
    --secret-string \'{"botToken":"SEU_TELEGRAM_BOT_TOKEN"}\' \
    --region sua-regiao-aws
```

### 2.3. Verificação dos Secrets

Após inserir todos os valores, você pode verificar se os secrets foram armazenados corretamente usando o comando `get-secret-value` (apenas para confirmar a existência, evite exibir o valor completo em logs por segurança):

```bash
aws secretsmanager get-secret-value \
    --secret-id /memecoin-sniping/helius-api-key \
    --query SecretString \
    --output text \
    --region sua-regiao-aws
```

Este comando deve retornar o JSON que você inseriu. Repita para os outros secrets se desejar confirmar.

### 2.4. Boas Práticas de Segurança com Secrets

*   **Rotação de Credenciais**: O AWS Secrets Manager suporta a rotação automática de credenciais. Para chaves mais sensíveis, como a da carteira Solana, configure a rotação para aumentar a segurança.
*   **Princípio do Menor Privilégio**: As roles IAM criadas pelo CloudFormation para as funções Lambda já seguem o princípio do menor privilégio, permitindo que cada Lambda acesse apenas os secrets que necessita.
*   **Monitoramento**: Utilize o AWS CloudTrail e o CloudWatch para monitorar o acesso aos seus secrets e configurar alertas para atividades incomuns.

Com suas chaves de API configuradas de forma segura, a solução terá acesso às informações necessárias para operar. O próximo passo é empacotar e implantar o código dos agentes nas funções Lambda correspondentes. 

---

*Autor: Manus AI*
*Data: 7 de Julho de 2025*



## 3. Deploy das Funções AWS Lambda (Agentes)

Com a infraestrutura AWS base configurada e suas chaves de API armazenadas de forma segura, o próximo passo é empacotar o código de cada agente e implantá-lo como funções AWS Lambda. O script `scripts/package_lambda.sh` automatiza esse processo.

### 3.1. Entendendo o Processo de Empacotamento e Deploy

As funções AWS Lambda exigem que o código e suas dependências sejam empacotados em um arquivo `.zip` para serem implantados. O script `package_lambda.sh` realiza as seguintes ações para cada agente:

1.  **Instalação de Dependências**: Navega até o diretório de cada agente (`src/discoverer`, `src/analyzer`, etc.) e instala as dependências Python listadas no `requirements.txt` do agente em um diretório local. Isso garante que todas as bibliotecas necessárias estejam incluídas no pacote de deploy.
2.  **Criação do Pacote `.zip`**: Compacta o código do agente e suas dependências em um arquivo `.zip`.
3.  **Upload para S3**: Envia o arquivo `.zip` gerado para o bucket S3 de código Lambda que foi criado na etapa de deploy da infraestrutura.
4.  **Atualização da Função Lambda**: Atualiza a função AWS Lambda correspondente, apontando-a para o novo pacote `.zip` no S3. Isso garante que a função Lambda sempre execute a versão mais recente do seu código.

### 3.2. Executando o Script de Empacotamento e Deploy

No terminal, a partir do diretório raiz do projeto, execute o script `scripts/package_lambda.sh`. Você pode especificar qual agente deseja empacotar e implantar, ou usar `all` para processar todos os agentes de uma vez.

#### 3.2.1. Deploy de Todos os Agentes

Para empacotar e implantar todos os quatro agentes (Discoverer, Analyzer, Trader, Optimizer), execute:

```bash
./scripts/package_lambda.sh all
```

#### 3.2.2. Deploy de um Agente Específico

Se você fez alterações em apenas um agente e deseja implantar apenas ele, pode especificar o nome do agente:

```bash
./scripts/package_lambda.sh discoverer
# ou
./scripts/package_lambda.sh analyzer
# ou
./scripts/package_lambda.sh trader
# ou
./scripts/package_lambda.sh optimizer
```

#### Exemplo de Saída do Script (para um agente)

```bash
ubuntu@sandbox:~/memecoin-sniping-solution$ ./scripts/package_lambda.sh discoverer
Empacotando e implantando o agente: discoverer
Instalando dependências para discoverer...
Collecting boto3==1.26.137
  Downloading boto3-1.26.137-py3-none-any.whl (139 kB)
...
Successfully installed boto3-1.26.137 botocore-1.29.137 ...
Criando pacote zip para discoverer...
  adding: discoverer.py (deflated 65%)
  adding: requirements.txt (deflated 35%)
  adding: boto3/ (stored 0%)
...
Upload do pacote zip para S3: s3://memecoin-sniping-code-bucket-dev/discoverer.zip
upload: ./discoverer.zip to s3://memecoin-sniping-code-bucket-dev/discoverer.zip
Atualizando função Lambda: MemecoinSnipingDiscoverer
{
    "FunctionName": "MemecoinSnipingDiscoverer",
    "FunctionArn": "arn:aws:lambda:us-east-1:123456789012:function:MemecoinSnipingDiscoverer",
    "Runtime": "python3.9",
    "Role": "arn:aws:iam::123456789012:role/MemecoinSnipingDiscovererRole",
    ...
}
Deploy do agente discoverer concluído com sucesso!
```

#### Tempo de Execução

O processo de empacotamento e deploy pode levar alguns minutos por agente, especialmente na primeira vez, pois todas as dependências precisam ser baixadas e incluídas no pacote `.zip`. Para `all`, o processo será sequencial para cada agente.

### 3.3. Verificação do Deploy das Funções Lambda

Após a execução do script, você pode verificar o status das suas funções Lambda no console da AWS:

1.  Acesse o [console da AWS Lambda](https://console.aws.amazon.com/lambda/)
2.  Certifique-se de que está na região correta (a mesma que você usou para o deploy).
3.  Você deverá ver as seguintes funções Lambda listadas:
    *   `MemecoinSnipingDiscoverer`
    *   `MemecoinSnipingAnalyzer`
    *   `MemecoinSnipingTrader`
    *   `MemecoinSnipingOptimizer`
4.  Clique em cada função para verificar seus detalhes, como o código-fonte (que deve estar apontando para o S3), as variáveis de ambiente e as permissões.

Você também pode testar uma função Lambda manualmente a partir do console do Lambda, configurando um evento de teste simples (por exemplo, um JSON vazio `{}` para testar a invocação básica). Isso ajuda a confirmar que a função está respondendo e que não há erros de tempo de execução básicos.

Com os agentes implantados, a lógica central da sua solução de sniping de memecoins está agora ativa na AWS. O próximo passo é implantar o dashboard web para que você possa monitorar e interagir com a solução.

---

*Autor: Manus AI*
*Data: 7 de Julho de 2025*



## 4. Deploy do Dashboard Web

O dashboard web é a interface principal para monitorar a performance da sua solução de sniping de memecoins e interagir com algumas de suas funcionalidades. Ele é implementado como uma aplicação Flask e pode ser implantado de diversas maneiras na AWS. Para este guia, vamos considerar uma abordagem comum usando AWS Elastic Beanstalk ou um contêiner Docker no ECS/Fargate para simplicidade, ou até mesmo um deploy manual para testes iniciais.

### 4.1. Opções de Deploy para o Dashboard

#### 4.1.1. Deploy Local (para Testes e Desenvolvimento)

Para testar o dashboard rapidamente em sua máquina local, siga estes passos:

1.  **Navegue até o diretório do dashboard**: 
    ```bash
    cd dashboard
    ```
2.  **Crie e ative um ambiente virtual**: 
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```
3.  **Instale as dependências**: 
    ```bash
    pip install -r requirements.txt
    ```
4.  **Execute a aplicação Flask**: 
    ```bash
    python src/main.py
    ```
    O dashboard estará acessível em `http://localhost:5000` no seu navegador.

#### 4.1.2. Deploy na AWS (Recomendado para Produção)

Para um ambiente de produção, o deploy do dashboard na AWS garante alta disponibilidade, escalabilidade e segurança. As opções mais comuns incluem:

*   **AWS Elastic Beanstalk**: Uma maneira fácil de implantar e escalar aplicações web. Ele abstrai a infraestrutura subjacente (servidores EC2, balanceadores de carga, etc.).
*   **AWS ECS (Elastic Container Service) com Fargate**: Permite executar o dashboard como um contêiner Docker sem precisar gerenciar servidores. Oferece grande flexibilidade e escalabilidade.
*   **AWS Lambda com API Gateway**: Para dashboards mais simples ou APIs REST, pode-se usar o Flask como uma função Lambda, acessível via API Gateway. Isso é ideal para arquiteturas serverless completas.

Para este guia, vamos focar em um deploy genérico que pode ser adaptado para Elastic Beanstalk ou ECS/Fargate, pois ambos geralmente envolvem o empacotamento da aplicação.

### 4.2. Preparando o Dashboard para Deploy

Independentemente da opção de deploy na AWS, você precisará garantir que o dashboard esteja pronto para ser empacotado e implantado.

1.  **Verifique as Dependências**: Certifique-se de que o arquivo `dashboard/requirements.txt` está atualizado com todas as dependências Python necessárias para o Flask e suas bibliotecas (boto3, flask-cors, etc.). Você pode gerar este arquivo executando:
    ```bash
    cd dashboard
    source venv/bin/activate # Se você usou um ambiente virtual local
    pip freeze > requirements.txt
    ```
2.  **Configuração de Produção**: Para produção, o `debug=True` em `src/main.py` deve ser removido ou definido como `False`. Além disso, o `SECRET_KEY` deve ser uma string aleatória e complexa, preferencialmente carregada de uma variável de ambiente ou do Secrets Manager.
    ```python
    # Em src/main.py
    app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY", "uma_chave_secreta_padrao_para_desenvolvimento")
    app.run(host=\'0.0.0.0\', port=5000, debug=False) # Mudar para False em produção
    ```

### 4.3. Exemplo de Deploy com Elastic Beanstalk (Abordagem Simplificada)

Esta é uma das maneiras mais rápidas de colocar uma aplicação Flask no ar na AWS.

1.  **Instale o EB CLI**: 
    ```bash
    pip install awsebcli
    ```
2.  **Inicialize o Elastic Beanstalk no diretório do dashboard**: 
    ```bash
    cd dashboard
    eb init -p python-3.9 my-memecoin-dashboard --region sua-regiao-aws
    ```
    Siga as instruções. Escolha a região e crie uma nova aplicação.
3.  **Crie um ambiente Elastic Beanstalk**: 
    ```bash
    eb create memecoin-dashboard-env
    ```
    Isso pode levar vários minutos, pois o Elastic Beanstalk provisionará todos os recursos necessários (EC2, Load Balancer, etc.).
4.  **Deploy da aplicação**: 
    ```bash
    eb deploy
    ```
    O EB CLI empacotará seu código e o implantará no ambiente. Após o deploy, o terminal exibirá a URL pública do seu dashboard.

### 4.4. Configuração de Variáveis de Ambiente para o Dashboard

O dashboard precisará acessar as mesmas variáveis de ambiente que os agentes Lambda para se conectar ao DynamoDB, S3 e Secrets Manager. Se você estiver usando Elastic Beanstalk, pode configurá-las no console do EB em `Configuração > Propriedades de Software > Variáveis de Ambiente`.

Exemplos de variáveis de ambiente que o dashboard pode precisar:

*   `TRADER_TABLE_NAME`: Nome da tabela DynamoDB do Trader.
*   `OPTIMIZER_TABLE_NAME`: Nome da tabela DynamoDB do Optimizer.
*   `CONFIG_BUCKET`: Nome do bucket S3 de configuração.
*   `TELEGRAM_BOT_TOKEN_SECRET_NAME`: Nome do secret do Telegram no Secrets Manager.

### 4.5. Verificação do Deploy do Dashboard

Após o deploy, acesse a URL pública do dashboard no seu navegador. Verifique se a interface carrega corretamente e se os dados de trading (mesmo que vazios inicialmente, se ainda não houver trades) são exibidos. Se houver problemas, verifique os logs do ambiente Elastic Beanstalk (via `eb logs` ou no console do CloudWatch).

Com o dashboard no ar, você terá uma visão centralizada da sua solução, permitindo monitorar a performance e interagir com os dados de trading. O próximo e último passo é realizar uma verificação final de todo o sistema e entender como a solução começa a operar.

---

*Autor: Manus AI*
*Data: 7 de Julho de 2025*



## 5. Verificação do Deploy e Configuração Inicial

Após o deploy de todos os componentes (infraestrutura, agentes Lambda e dashboard), é crucial realizar uma verificação final para garantir que tudo está funcionando conforme o esperado. Esta seção também aborda a configuração inicial da solução para começar a operar.

### 5.1. Verificação da Infraestrutura

1.  **AWS CloudFormation Console**: Acesse o console do CloudFormation na sua região. Verifique se todas as stacks relacionadas à sua solução (`memecoin-sniping-infra-dev`, `memecoin-sniping-sqs-dev`, etc.) estão no status `CREATE_COMPLETE` ou `UPDATE_COMPLETE`. Se houver alguma falha, investigue os logs da stack para identificar o problema.
2.  **AWS Lambda Console**: Verifique se as quatro funções Lambda (`MemecoinSnipingDiscoverer`, `MemecoinSnipingAnalyzer`, `MemecoinSnipingTrader`, `MemecoinSnipingOptimizer`) estão presentes e com o status `Active`.
3.  **AWS SQS Console**: Confirme a existência das filas SQS (`MemecoinSnipingDiscovererQueue`, `MemecoinSnipingAnalyzerQueue`).
4.  **AWS DynamoDB Console**: Verifique se as tabelas DynamoDB (`MemecoinSnipingTraderTable`, `MemecoinSnipingOptimizerTable`) foram criadas.
5.  **AWS S3 Console**: Confirme a existência dos buckets S3 (um para código Lambda e outro para configurações, como `memecoin-sniping-code-bucket-dev` e `memecoin-sniping-config-bucket-dev`).
6.  **AWS Secrets Manager Console**: Verifique se os secrets (`/memecoin-sniping/helius-api-key`, etc.) estão presentes e se os valores foram inseridos corretamente (você pode visualizar os detalhes do secret, mas tenha cuidado para não expor os valores).

### 5.2. Verificação do Funcionamento dos Agentes

Para confirmar que os agentes estão se comunicando e processando informações, você pode realizar alguns testes:

1.  **Teste do Agente Discoverer**: 
    *   O Agente Discoverer é acionado por webhooks da Helius API. Para testá-lo, você precisará configurar um webhook na Helius para apontar para o endpoint da sua função Lambda Discoverer (geralmente um API Gateway que invoca o Lambda). 
    *   Alternativamente, você pode invocar o Lambda Discoverer manualmente no console do AWS Lambda com um evento de teste que simule um webhook da Helius. Observe os logs do CloudWatch do Discoverer para ver se ele processou o evento e enviou uma mensagem para a fila SQS do Analyzer.
2.  **Teste do Agente Analyzer**: 
    *   O Analyzer é acionado por mensagens na fila SQS. Você pode enviar uma mensagem de teste para a `MemecoinSnipingAnalyzerQueue` via console do SQS, contendo dados de um token (simulando a saída do Discoverer). 
    *   Monitore os logs do CloudWatch do Analyzer para ver se ele processou a mensagem, realizou a análise e enviou uma mensagem para a fila SQS do Trader (ou diretamente para o Trader, dependendo da sua configuração).
3.  **Teste do Agente Trader**: 
    *   O Trader é acionado por mensagens do Analyzer. Se o Analyzer enviar uma recomendação de trade, o Trader tentará executá-la. 
    *   **Importante**: Por padrão, o Trader está em modo `paper trading` (`is_dry_run: true`). Verifique os logs do Trader para confirmar que ele está simulando as operações e registrando-as na tabela DynamoDB `MemecoinSnipingTraderTable`.
4.  **Teste do Agente Optimizer**: 
    *   O Optimizer é acionado por uma regra do EventBridge. Você pode aguardar o próximo agendamento ou invocar o Lambda Optimizer manualmente no console. 
    *   Verifique os logs do CloudWatch do Optimizer para ver se ele está coletando dados do DynamoDB, executando a otimização e, potencialmente, atualizando o arquivo de configuração no S3.

### 5.3. Configuração Inicial da Solução

Para que a solução comece a operar de forma autônoma, você precisará configurar a Helius API para enviar webhooks para o Agente Discoverer e, opcionalmente, configurar o bot do Telegram para receber notificações.

#### 5.3.1. Configurar Webhook na Helius API

1.  **Obtenha o Endpoint do Discoverer**: Se você usou um API Gateway para expor o Lambda Discoverer, obtenha a URL do endpoint. Caso contrário, o Lambda pode ser invocado diretamente por outros serviços AWS ou por um evento de teste.
2.  **Crie um Webhook na Helius**: No painel da Helius, crie um novo webhook. Configure-o para monitorar os eventos de blockchain que você deseja (por exemplo, `SWAP` para detecção de novos pools de liquidez) e aponte a URL do webhook para o endpoint do seu Lambda Discoverer.

#### 5.3.2. Configurar o Bot do Telegram

1.  **Inicie o Bot**: No Telegram, procure pelo seu bot (usando o nome que você deu ao `@BotFather`) e inicie uma conversa com ele. Isso é necessário para que o bot possa enviar mensagens para você.
2.  **Obtenha seu Chat ID**: Você pode usar um bot como `@userinfobot` no Telegram para obter seu `chat_id`. Este ID é necessário para que o sistema saiba para onde enviar as notificações.
3.  **Configure o Chat ID no Sistema**: O dashboard ou um arquivo de configuração no S3 pode precisar do seu `chat_id` para enviar mensagens. Verifique a documentação do dashboard para saber onde configurar isso.

### 5.4. Próximos Passos: Ativação do Live Trading e Otimização

Após confirmar que todos os componentes estão funcionando corretamente em modo de simulação, você pode prosseguir com a ativação do live trading (conforme detalhado na Seção 3 do `REAL_WORLD_GUIDE.md`) e permitir que o Agente Optimizer comece a refinar seus parâmetros de trading (conforme detalhado na Seção 5 do `REAL_WORLD_GUIDE.md`).

Lembre-se de que o monitoramento contínuo é fundamental. Utilize o dashboard, os logs do CloudWatch e os alertas do Telegram para acompanhar a performance e a saúde da sua solução em tempo real.

---

*Autor: Manus AI*
*Data: 7 de Julho de 2025*



REV 002


