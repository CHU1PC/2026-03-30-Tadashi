# SAM(Serverless Application Model)

**AWS SAM（Serverless Application Model）** を学ぶためのハンズオンプロジェクト。

S3に保存したディープラーニングモデル（ONNX）を使って、画像を分類するサーバーレスアプリケーションです。

## AWS SAMとは？

**SAM（Serverless Application Model）** は、AWSのサーバーレスアプリケーションを**簡単に定義・ビルド・デプロイ・テスト**するためのフレームワークです。

### そもそもサーバーレスとは？

通常のWebアプリケーションは、**サーバーを自分で用意・管理**する必要があります：

```text
従来のアプリケーション:
  サーバーを購入/レンタル → OSをインストール → 24時間起動しておく
  → アクセスが増えたらサーバーを追加 → 使わない時間も課金される
```

**サーバーレス** は、サーバーの管理をAWSに任せるアーキテクチャです：

```text
サーバーレス:
  コードだけ書く → AWSにアップロード → リクエストが来た時だけ実行
  → 使った分だけ課金 → サーバーの管理は一切不要
```

AWS Lambda がサーバーレスの代表的なサービスです。関数（コード）をアップロードすると、リクエストが来るたびにAWSが自動でサーバーを起動し、実行後に停止します。サーバーの存在を意識する必要がないので「サーバーレス」と呼ばれます。

#### サーバーレスのメリット

- **コスト削減** — リクエストが来た時だけ課金。アクセスがゼロなら料金もゼロ
- **サーバー管理不要** — OS更新、セキュリティパッチ、障害対応をAWSに任せられる
- **自動スケーリング** — アクセスが急増しても自動で処理能力が増える。手動でサーバーを追加する必要がない
- **開発に集中できる** — インフラの心配をせず、ビジネスロジック（コード）に集中できる

#### サーバーレスのデメリット

- **コールドスタート** — しばらく使われていないと、次のリクエストで起動に時間がかかる（数秒〜数十秒）。このプロジェクトではモデルのダウンロードも加わるため、初回は特に遅い
- **実行時間の制限** — Lambda関数は最大15分まで。長時間の処理には向かない
- **ローカル開発が難しい** — 本番環境はAWS上にあるため、ローカルでの再現が難しい（→ **SAMはこの問題を解決する**）
- **デバッグしにくい** — エラーが起きてもサーバーにSSHしてログを見ることができない。CloudWatch Logsを使う必要がある
- **ベンダーロックイン** — AWSのサービスに依存するため、他のクラウドへの移行が難しい

### SAMが解決する問題

AWSでLambda関数を使ったアプリケーションを作る時、通常はこれだけの作業が必要です：

1. AWSコンソールでLambda関数を作成
2. IAMロールを作成して権限を設定
3. API Gatewayを作成してLambdaと紐付け
4. S3バケットを作成
5. コードをZIPにしてアップロード
6. 環境変数を手動で設定
7. 全部の設定が正しいか確認...

**1つの機能を追加するたびに、この作業を繰り返す必要があります。**

さらに問題なのは：

- 設定がAWSコンソール上にしか存在しない（コードで管理できない）
- チームメンバーが同じ環境を再現できない
- 本番環境とテスト環境で設定が違っていても気づけない
- ローカルでテストする方法がない

### SAMがあると何が変わるか

SAMを使うと、上記の全てが `template.yaml` という **1つのファイル** に集約されます：

```yaml
# これだけで Lambda + API Gateway + IAMロール が自動で作られる
ClassifyFunction:
  Type: AWS::Serverless::Function
  Properties:
    PackageType: Image
    Policies:
      - S3ReadPolicy:
          BucketName: !Ref ModelBucket
    Events:
      Classify:
        Type: Api
        Properties:
          Path: /classify
          Method: post
```

上の十数行で、SAMなしなら50行以上のCloudFormation定義（Lambda + IAMロール + API Gateway + 権限設定）が自動生成されます。

### なぜLambdaを使う時にSAMが特に便利なのか

Lambdaは「サーバーを持たずにコードを実行する」サービスですが、単独では使いにくいです：

| Lambdaだけの場合 | SAM + Lambdaの場合 |
| --- | --- |
| コードの変更のたびに手動でZIPを作成・アップロード | `sam build` で自動パッケージング |
| API Gatewayとの連携を手動で設定 | `Events: Type: Api` と書くだけで自動連携 |
| IAMロールを手動で作成・管理 | `Policies: S3ReadPolicy` で自動生成 |
| ローカルテスト不可（デプロイしないと動作確認できない） | `sam local` でDockerを使ってローカル実行 |
| 環境変数をコンソールで手動設定 | `template.yaml` の `Environment` で定義 |
| 複数の関数がある場合、設定がバラバラになる | `Globals` で全関数の共通設定をまとめられる |
| 設定のバージョン管理ができない | `template.yaml` をGitで管理できる |

### SAM最大の強み：ローカルで本番環境を再現できる

SAMが他のIaCツールと最も異なるのは、**ローカル環境で本番とほぼ同じ動作を再現できる**ことです。

#### 従来のLambda開発の問題

```text
従来の開発サイクル:
  コード修正 -> ZIPに固める -> AWSにアップロード -> テスト -> エラー発見
  -> コード修正 -> ZIPに固める -> AWSにアップロード -> テスト -> ...

  1回のテストに数分かかる。AWSへの通信が必要。課金も発生する。
```

#### SAMを使った開発サイクル

```text
SAMの開発サイクル:
  コード修正 -> sam build -> sam local でテスト -> すぐ結果が分かる
  -> コード修正 -> sam build -> sam local でテスト -> ...

  数秒でテストできる。AWSへの通信不要。課金なし。
```

`sam local` はDockerを使って、**あなたのPC上にLambdaの実行環境をそのまま再現**します。AWSアカウントがなくても、インターネット接続がなくても、Lambda関数の動作をテストできます。

#### このプロジェクトでの再現

このプロジェクトでは、さらに **LocalStack** を組み合わせることで、S3も含めた完全な再現を実現しています：

```text
本番環境 (AWS):
  API Gateway -> Lambda -> S3 (モデル読み込み) -> 分類結果を返す

ローカル環境 (あなたのPC):
  SAM local   -> Lambda (Docker) -> LocalStack S3 (モデル読み込み) -> 分類結果を返す

  ↑ 本番と同じコード、同じ動作、同じ結果。AWSアカウント不要。
```

つまり、**本番にデプロイする前に、ローカルで全ての動作を確認できます。** バグを見つけるためにデプロイする必要がなく、開発速度が大幅に向上します。

## LocalStackとは？

**LocalStack** は、AWSのサービスを**自分のPC上でエミュレート（擬似的に再現）**するオープンソースツールです。Dockerコンテナとして動作します。

### なぜLocalStackが必要なのか

SAMの `sam local` はLambda関数をローカルで実行できますが、**Lambda以外のAWSサービス（S3、DynamoDBなど）はエミュレートしてくれません。**

```text
sam local だけの場合:
  Lambda関数 → S3からモデルを読み込む → 本物のAWS S3に接続 → AWSアカウントが必要

sam local + LocalStack:
  Lambda関数 → S3からモデルを読み込む → LocalStack S3に接続 → AWSアカウント不要
```

つまり、LocalStackは `sam local` が対応していない部分を補完するツールです。

### LocalStackの仕組み

```text
LocalStackなし:
  aws s3 cp file.txt s3://bucket/file.txt
  → https://s3.amazonaws.com に接続（本物のAWS）

LocalStackあり:
  aws --endpoint-url=http://localhost:4566 s3 cp file.txt s3://bucket/file.txt
  → http://localhost:4566 に接続（あなたのPC上の擬似AWS）
```

`--endpoint-url` を追加するだけで、同じコマンドがLocalStackに向きます。Pythonコード（boto3）でも同様に `endpoint_url` を指定するだけです：

```python
# 本物のAWS
s3 = boto3.client("s3")

# LocalStack
s3 = boto3.client("s3", endpoint_url="http://localhost:4566")
```

### このプロジェクトでの役割分担

| ツール | 担当 | 理由 |
| --- | --- | --- |
| **SAM local** | Lambda関数の実行 | Lambda専用のローカル実行環境。`template.yaml` を読んでDockerで実行 |
| **LocalStack** | S3のエミュレート | SAM localはS3をエミュレートしないため、LocalStackで補完 |

### なぜLocalStackでLambdaを動かさないのか

LocalStackもLambda関数を実行する機能がありますが、このプロジェクトでは**SAM localを使ってLambdaを実行**しています。その理由：

- **LocalStackのLambdaエミュレートはPro版（有料）が必要** — 無料版では制限がある
- **SAM localはLambda専用に設計されている** — `template.yaml` をそのまま読んでDockerで実行でき、セットアップが簡単
- **SAM localはAPI Gatewayも自動作成** — `Events: Type: Api` の定義からルーティングを自動で設定してくれる
- **ログが見やすい** — SAM localはLambdaの実行ログをターミナルにそのまま表示してくれる

つまり、**それぞれのツールが得意なことを担当**しています：SAM localがLambdaの実行を、LocalStackがS3のエミュレートを担当します。

### LocalStackの注意点

- **データは永続化されない（デフォルト）** — `docker compose down` するとS3のデータは消える。再起動時はバケット作成とモデルアップロードをやり直す必要がある
- **無料版は一部のサービスのみ** — S3、DynamoDB、SQSなどは無料。LambdaのエミュレートはPro版（有料）が必要
- **本番のAWSと100%同じではない** — 細かい挙動の違いがある場合があるので、最終的には本番AWSでの動作確認が推奨

## CloudFormationとは？

SAMを理解するには、まず **CloudFormation** を理解する必要があります。なぜなら、**SAMは単独では動かない** — 裏側でCloudFormationを使ってリソースを作成しているからです。

```text
SAMとCloudFormationの関係:

  あなた → SAM → CloudFormation → AWS
          (書きやすくする)  (実際にリソースを作る)

SAM = 「CloudFormationを簡単に書くためのツール」
CloudFormation = 「AWSリソースを実際に作成・管理するサービス」
```

つまり、SAMはあくまで**便利な入口**であり、実際にS3バケットやLambda関数を作るのはCloudFormationです。`sam deploy` を実行すると、SAMが `template.yaml` をCloudFormation形式に変換し、CloudFormationがAWSリソースを作成します。

### 問題：AWSリソースの手動管理はつらい

AWSでアプリケーションを構築すると、多くのリソースを作成する必要があります：

- Lambda関数を3つ作成
- それぞれにIAMロールを設定
- API Gatewayを作成して各Lambdaにルーティング
- S3バケットを作成
- DynamoDBテーブルを作成
- ...

これを全て **AWSコンソール（Webの管理画面）で手動で設定** すると：

- 設定を忘れる・間違える
- 同じ環境を別のアカウントに再現できない
- 誰がいつ何を変更したか分からない
- 開発環境と本番環境で設定がズレる

### 解決策：Infrastructure as Code（IaC）

CloudFormationは、AWSリソースを **コード（YAMLファイル）で定義** するサービスです。

```yaml
# 例：S3バケットをCloudFormationで定義
Resources:
  MyBucket:
    Type: AWS::S3::Bucket
    Properties:
      BucketName: my-app-bucket
```

このYAMLファイルをAWSに渡すと、CloudFormationが自動でS3バケットを作成してくれます。

### CloudFormationの基本概念

```text
テンプレート（template.yaml）
  = 「何を作りたいか」を定義したファイル

      ↓ CloudFormationに渡す

スタック（Stack）
  = テンプレートから作られたAWSリソースの集まり
  = スタックを削除すれば、関連リソースが全て消える
```

**スタック** という概念が重要です。1つのテンプレートから作られたリソースは1つのスタックにまとまるので、不要になったら `sam delete`（= スタック削除）で全部きれいに消せます。

### CloudFormationだけだとLambdaは面倒

CloudFormationは汎用的ですが、Lambda関数を定義するには多くの記述が必要です：

```yaml
# CloudFormationでLambda関数を作る場合（約40行）
Resources:
  MyFunction:
    Type: AWS::Lambda::Function
    Properties:
      FunctionName: my-function
      Runtime: python3.13
      Handler: app.lambda_handler
      Code:
        S3Bucket: my-deploy-bucket
        S3Key: my-function.zip
      Role: !GetAtt MyFunctionRole.Arn

  MyFunctionRole:
    Type: AWS::IAM::Role
    Properties:
      AssumeRolePolicyDocument:
        Version: '2012-10-17'
        Statement:
          - Effect: Allow
            Principal:
              Service: lambda.amazonaws.com
            Action: sts:AssumeRole
      Policies:
        - PolicyName: S3ReadAccess
          PolicyDocument:
            Version: '2012-10-17'
            Statement:
              - Effect: Allow
                Action:
                  - s3:GetObject
                Resource: !Sub 'arn:aws:s3:::my-bucket/*'

  MyApi:
    Type: AWS::ApiGateway::RestApi
    # ... さらに20行以上の設定が必要
```

**SAMなら同じことが10行で書けます：**

```yaml
# SAMでLambda関数を作る場合（約10行）
Resources:
  MyFunction:
    Type: AWS::Serverless::Function
    Properties:
      CodeUri: src/
      Handler: app.lambda_handler
      Runtime: python3.13
      Policies:
        - S3ReadPolicy:
            BucketName: my-bucket
      Events:
        MyApi:
          Type: Api
          Properties:
            Path: /my-endpoint
            Method: post
```

これがSAMの存在意義です。CloudFormationの力はそのままに、**サーバーレスに特化した省略記法** を提供します。

## SAMの仕組み

### SAMとCloudFormationの関係

SAMは **CloudFormation** の拡張です。CloudFormationはAWSのインフラをコードで定義・管理するサービスで、SAMはその上に「サーバーレス向けの便利な省略記法」を追加したものです。

```text
あなたが書くもの:
  template.yaml (SAM構文)
    AWS::Serverless::Function  <- SAM独自の省略記法
    AWS::Serverless::SimpleTable

     ↓ sam deploy 時に自動変換

CloudFormationが受け取るもの:
  template.yaml (CloudFormation構文に変換済み)
    AWS::Lambda::Function      <- 通常のCloudFormationリソース
    AWS::IAM::Role             <- 自動生成されたIAMロール
    AWS::ApiGateway::RestApi   <- 自動生成されたAPI Gateway
    AWS::DynamoDB::Table
```

つまり、SAMで `AWS::Serverless::Function` と書くだけで、裏では Lambda + IAMロール + API Gateway が自動で作られます。手動で3つのリソースを定義する必要がありません。

## SAMコマンド詳解（ローカル開発で使うもの）

### `sam build`

```bash
sam build
```

**何をするか：** ソースコードと依存パッケージをパッケージングする。

Lambda関数のパッケージ方法は2種類あります：

**ZIPパッケージ（`PackageType: Zip`、デフォルト）:**

- `CodeUri` で指定したディレクトリのコードを `.aws-sam/build/` にコピー
- `requirements.txt` や `pyproject.toml` から依存パッケージをインストール
- 最大250MBまで

```yaml
# ZIPパッケージの場合
MyFunction:
  Type: AWS::Serverless::Function
  Properties:
    CodeUri: src/           # ソースコードの場所
    Handler: app.handler    # 実行する関数
    Runtime: python3.13     # ランタイム指定が必要
```

**Dockerコンテナ（`PackageType: Image`、このプロジェクトで使用）:**

- `Metadata.DockerContext` で指定したディレクトリの Dockerfile からDockerイメージをビルド
- ML系ライブラリなど大きな依存パッケージがある場合に使用
- 最大10GBまで

```yaml
# Dockerコンテナの場合（このプロジェクト）
ClassifyFunction:
  Type: AWS::Serverless::Function
  Properties:
    PackageType: Image      # Dockerを使う宣言
    # CodeUri, Handler, Runtime は不要（Dockerfileで定義するため）
  Metadata:
    DockerContext: ./lambda  # Dockerfileがあるディレクトリ
    Dockerfile: Dockerfile
```

```text
sam build 実行前:
  lambda/
    app.py
    Dockerfile
    pyproject.toml

sam build 実行後:
  .aws-sam/build/
    ClassifyFunction/        <- ビルド済みのLambda関数
    template.yaml            <- 変換済みテンプレート
```

**いつ再実行が必要か：**

- `app.py`（Lambda関数のコード）を変更した時
- `pyproject.toml`（依存パッケージ）を変更した時
- `template.yaml` を変更した時

### `sam local start-api`

```bash
sam local start-api --env-vars env.local.json
```

**何をするか：** ローカルにAPI Gatewayをエミュレートし、リクエストが来たらDockerでLambdaを実行する。

```text
リクエストの流れ:
  curl POST localhost:3000/classify
    -> SAM local が受信
    -> template.yaml のEventsを見て ClassifyFunction を特定
    -> Dockerコンテナを起動（classifyfunction:latest イメージ）
    -> コンテナ内で app.lambda_handler() を実行
    -> レスポンスを返す
    -> コンテナを停止（デフォルト動作）
```

**オプション：**

| オプション | 説明 |
| --- | --- |
| `--env-vars file.json` | 環境変数を上書き（LocalStackへの接続設定など） |
| `--warm-containers EAGER` | コンテナを起動したまま保持（コールドスタートを回避） |
| `--port 3001` | ポートを変更（デフォルトは3000） |
| `--docker-network` | Dockerネットワークを指定 |

### `sam local invoke`

```bash
sam local invoke ClassifyFunction -e events/classify_event.json
```

**何をするか：** 1つのLambda関数を1回だけ実行する。APIを経由せずに直接テストできる。

`-e` でイベントJSONを渡す — これがLambdaの `event` 引数になる。

## このプロジェクトの動作

```text
画像をアップロード
  -> FastAPIが受け取る（localhost:8000）
  -> SAM local経由でLambdaに送信（localhost:3000）
  -> LambdaがS3からONNXモデルの重みをダウンロード
  -> ONNX Runtimeで推論実行
  -> 結果を返す："good"（92%）or "bad"（8%）
```

モデルは **ConvNeXt Small**（良品/不良品の2クラス分類）です。

## 学べること

- **`template.yaml`** の書き方（SAMの中核）
- **Lambda関数**、**S3バケット**、**API Gateway** をコードで定義する方法
- Lambdaを **Dockerコンテナ** としてデプロイする方法（ML向け）
- **`sam build`**、**`sam local`**、**`sam deploy`** の使い方
- Lambda内で **S3からファイルを読み込む** 方法
- **LocalStack** を使った完全オフラインのローカル開発

## プロジェクト構成

```text
template.yaml              <- SAMテンプレート：全AWSリソースを定義
samconfig.toml             <- デプロイ設定（リージョン、スタック名）
docker-compose.yml         <- LocalStack（擬似S3）+ FastAPIのコンテナ
env.local.json             <- ローカルテスト用の環境変数

lambda/                    <- Lambda関数（Dockerで実行）
  app.py                   <- メインコード：S3からモデルをDL、画像を分類
  Dockerfile               <- コンテナイメージの定義
  pyproject.toml            <- Pythonの依存パッケージ（onnxruntime, pillow, numpy）

app/                       <- FastAPIアプリ（ローカルテスト用）
  main.py                  <- 画像を受け取ってLambdaに転送
  Dockerfile               <- コンテナイメージの定義

models/                    <- ユーティリティスクリプト
  convert_to_onnx.py       <- PyTorchの.pthモデルをONNX形式に変換

s3/                        <- S3ユーティリティスクリプト
  upload_model.py          <- ONNXモデルをS3にアップロード

onnx/                      <- モデルファイル
  weight.onnx              <- 変換済みONNXモデル（Git LFSで管理）

dataset/                   <- テスト用サンプル画像
  images/good/             <- 良品画像
  images/bad/              <- 不良品画像
```

## 前提条件

以下のツールをインストールしてください：

```bash
# AWS CLI - S3の操作に必要（LocalStackでもAWS CLIを使う）
brew install awscli

# SAM CLI - SAMプロジェクトのビルド・実行に必要
brew install aws-sam-cli

# Docker Desktop - 全てDockerコンテナで動作する
# ダウンロード: https://www.docker.com/products/docker-desktop/

# uv - 高速なPythonパッケージマネージャー
brew install uv
```

ダミーのAWS認証情報を設定（LocalStack用、どんな値でもOK）：

```bash
aws configure
# AWS Access Key ID: test
# AWS Secret Access Key: test
# Default region name: ap-northeast-1
# Default output format: json
```

## Amazon S3とは？

このプロジェクトでは S3 にモデルの重みファイルを保存し、Lambda から読み込みます。S3 の基本を理解しておくとハンズオンがスムーズに進みます。

### S3 の基本

**Amazon S3（Simple Storage Service）** は、AWS のオブジェクトストレージサービスです。簡単に言えば、**ファイルをインターネット上に保存・取得できる巨大なファイルサーバー** です。

```text
ローカルのファイルシステム:
  /Users/you/documents/report.pdf

S3:
  s3://my-bucket/documents/report.pdf
       ~~~~~~~~   ~~~~~~~~~~~~~~~~~~~~
       バケット名    キー（ファイルパス）
```

### バケットとオブジェクト

S3 には2つの基本概念があります：

| 概念 | 説明 | 例 |
| --- | --- | --- |
| **バケット（Bucket）** | ファイルの入れ物。グローバルで一意の名前が必要 | `sam-image-classifier-models` |
| **オブジェクト（Object）** | バケット内のファイル。「キー」で指定する | `models/weight.onnx` |

```text
バケット: sam-image-classifier-models
  ├── models/
  │   └── weight.onnx          <- これが「オブジェクト」、キーは "models/weight.onnx"
  └── models/
      └── old_weight.onnx      <- 複数のモデルを保存することも可能
```

> **注意：** S3 に「フォルダ」は存在しません。`models/weight.onnx` はフォルダ構造のように見えますが、実際は `models/weight.onnx` という名前のキー（文字列）です。

### このプロジェクトでの S3 の使い方

```text
1. モデルの重みファイル（weight.onnx）をS3にアップロード
2. Lambda関数が起動時にS3からモデルをダウンロード
3. Lambda内の /tmp/ にキャッシュして推論に使用

  アップロード:
    aws s3 cp onnx/weight.onnx s3://bucket/models/weight.onnx
                                    ~~~~~~ ~~~~~~~~~~~~~~~~
                                    バケット  キー（MODEL_KEY）

  Lambda内でのダウンロード（lambda/app.py）:
    s3.download_file(MODEL_BUCKET, MODEL_KEY, "/tmp/model.onnx")
                     ~~~~~~~~~~~~  ~~~~~~~~~
                     バケット名     キー
```

### S3 の基本コマンド（AWS CLI）

```bash
# バケットを作成
aws s3 mb s3://my-bucket

# ファイルをアップロード
aws s3 cp local_file.txt s3://my-bucket/path/file.txt

# ファイルをダウンロード
aws s3 cp s3://my-bucket/path/file.txt local_file.txt

# バケット内のファイル一覧
aws s3 ls s3://my-bucket/

# ファイルを削除
aws s3 rm s3://my-bucket/path/file.txt

# LocalStackを使う場合は --endpoint-url を追加
aws --endpoint-url=http://localhost:4566 s3 ls s3://my-bucket/
```

## はじめ方

### Step 1: LocalStackとFastAPIを起動

> **関連ファイル:** `docker-compose.yml`（コンテナの定義）、`app/Dockerfile`（FastAPIのビルド定義）

```bash
docker compose up -d
```

`docker-compose.yml` に定義された2つのDockerコンテナが起動します：

- **LocalStack**（`localhost:4566`）— `docker-compose.yml` の `localstack` サービス。本物のAWSの代わりにローカルで動く擬似AWS。S3をエミュレート。
- **FastAPI**（`localhost:8000`）— `docker-compose.yml` の `app` サービス。`app/main.py` のコードを実行し、画像をLambdaに転送する。

### Step 2: LocalStack上にS3バケットを作成

> **関連ファイル:** `template.yaml` の `ModelBucket` リソース（本番では `sam deploy` 時に CloudFormation が自動でS3バケットを作成するが、ローカルでは CloudFormation が動かないため手動で作る必要がある）

```bash
aws --endpoint-url=http://localhost:4566 s3 mb s3://sam-image-classifier-models --region ap-northeast-1
```

擬似S3にバケットを作成します。バケット名 `sam-image-classifier-models` は `env.local.json` の `MODEL_BUCKET` と一致させる必要があります。

`--endpoint-url` で、AWS CLIの接続先をLocalStackに向けています。

### Step 3: ONNXモデルを擬似S3にアップロード

> **関連ファイル:** `template.yaml` の `Parameters.ModelKey`（S3上のモデルパスを定義）、`env.local.json` の `MODEL_KEY`

```bash
aws --endpoint-url=http://localhost:4566 s3 cp onnx/weight.onnx \
  s3://sam-image-classifier-models/models/weight.onnx --region ap-northeast-1
```

S3上のパス `models/weight.onnx` は `env.local.json` の `MODEL_KEY` で指定した値と一致させます。Lambda関数（`lambda/app.py`）はこのパスからモデルをダウンロードします。

### Step 4: Lambda関数をビルド

> **関連ファイル:** `template.yaml`（どの関数をビルドするか）、`lambda/Dockerfile`（Dockerイメージの定義）、`lambda/pyproject.toml`（Lambda用の依存パッケージ）

```bash
sam build
```

`template.yaml` の `ClassifyFunction` → `Metadata.DockerContext: ./lambda` → `lambda/Dockerfile` の順に参照し、Dockerイメージをビルドします。イメージには Python、ONNX Runtime、`app.py` が含まれます。

### Step 5: SAM local APIを起動

> **関連ファイル:** `template.yaml`（APIのパス定義 `Path: /classify`）、`env.local.json`（環境変数の上書き）

```bash
sam local start-api --env-vars env.local.json
```

`template.yaml` の `Events.Classify.Properties.Path: /classify` に基づいて、ローカルのAPI Gatewayが `localhost:3000` で起動します。

`--env-vars env.local.json` がないと、Lambda関数は `template.yaml` の `LOCALSTACK_ENDPOINT: ''`（空文字）を使うため、LocalStackではなく**実際のAWS S3に接続しようとして失敗**します。`env.local.json` で `LOCALSTACK_ENDPOINT` を `http://host.docker.internal:4566` に上書きすることで、LocalStackに接続されます。

### Step 6: テストしてみよう

> **関連ファイル:** `app/main.py`（FastAPIがリクエストを受け取り、SAM localに転送）→ `lambda/app.py`（Lambda関数が画像を分類）

ブラウザで `http://localhost:8000/docs` を開く — FastAPIのSwagger UIから画像をアップロードできます。

またはcurlで：

```bash
curl -X POST http://localhost:8000/classify \
  -F "file=@dataset/images/good/00001.png"
```

リクエストの流れ：

```text
curl → app/main.py (FastAPI, :8000)
  → base64エンコードしてSAM localに転送
  → template.yaml の Events で ClassifyFunction を特定
  → lambda/app.py (Lambda, Docker内)
    → env.local.json の LOCALSTACK_ENDPOINT を使ってLocalStack S3に接続
    → MODEL_BUCKET + MODEL_KEY のパスからモデルをダウンロード
    → 画像を前処理 → ONNX Runtime で推論
    → 結果を返す
```

期待されるレスポンス：

```json
{
  "predictions": [
    {"label": "good", "confidence": 0.95},
    {"label": "bad", "confidence": 0.05}
  ]
}
```

### Step 7: 終了

```bash
docker compose down -v --rmi all
```

SAM localは別ターミナルで `Ctrl+C` で停止してください。

## 重要なファイルの解説

### `template.yaml`

SAMの中核ファイル。以下を定義します：

- **Parameters** — 設定可能な値（例：使用するONNXモデルのパス）
- **Globals** — 全Lambda関数の共通設定
- **Resources** — 作成するAWSリソース（S3バケット、Lambda関数、API Gateway）
- **Outputs** — デプロイ後に表示される値（APIのURL、バケット名）

### `lambda/app.py`

Lambda関数のコード。重要なポイント：

- **グローバルスコープ** はコールドスタート時に1回だけ実行 — ここでS3からモデルをダウンロード
- **`lambda_handler()`** はリクエストごとに実行 — 画像を受け取り、分類して、結果を返す
- **`/tmp`** はLambdaで唯一書き込み可能なディレクトリ — モデルをここにキャッシュ

### `env.local.json`

ローカル実行時に環境変数を上書きするファイル。`LOCALSTACK_ENDPOINT` を `http://host.docker.internal:4566` に設定し、Lambda（Docker内）からLocalStack（同じくDocker内）に接続できるようにします。

## 本番AWSへのデプロイ（任意）

今回のハンズオンではLocalStackを使ったローカル開発のみを行いますが、参考として実際のAWSへのデプロイ手順も記載します。

### `sam deploy` コマンドについて

```bash
sam deploy --guided    # 初回（対話式）
sam deploy             # 2回目以降（samconfig.toml の設定を使用）
```

**何をするか：** ビルド済みのアプリケーションをAWSにデプロイする。

`--guided` を付けると、スタック名やリージョンなどを対話式で設定でき、回答は `samconfig.toml` に保存されます。

### `sam delete` コマンドについて

```bash
sam delete
```

**何をするか：** デプロイした全リソース（Lambda、S3、API Gatewayなど）を削除する。

CloudFormationスタックごと削除するので、関連リソースが全て消えます。ただし、中身があるS3バケットは先に空にする必要があります。

### Step 1: AWS認証情報を設定

```bash
aws configure
# 本物のAWSアクセスキーとシークレットキーを入力
# Default region: ap-northeast-1
```

### Step 2: デプロイ

```bash
sam build && sam deploy --guided
```

`--guided` を付けると、以下の質問が順番に表示されます：

```text
Setting default arguments for 'sam deploy'
=========================================

Stack Name [sam-app]: sam-image-classifier
  → CloudFormationスタックの名前。任意の名前でOK。

AWS Region [ap-northeast-1]: ap-northeast-1
  → リソースを作成するリージョン。東京リージョンなら ap-northeast-1。

Parameter ModelKey [models/weight.onnx]:
  → template.yaml の Parameters で定義した値。Enterでデフォルト値を使用。

Confirm changes before deploy [y/N]: y
  → デプロイ前に変更内容を確認するか。y が安全。

Allow SAM CLI IAM role creation [Y/n]: y
  → Lambda用のIAMロールを自動作成するか。y にしないとデプロイが失敗する。

Disable rollback [y/N]: n
  → デプロイ失敗時に自動ロールバックするか。n（ロールバックあり）が安全。

ClassifyFunction has no authentication. Is this okay? [y/N]: y
  → API Gatewayに認証がないことの確認。学習用なので y でOK。

Save arguments to configuration file [Y/n]: y
  → 回答を samconfig.toml に保存するか。y にすると次回から sam deploy だけでOK。

SAM configuration file [samconfig.toml]: （Enterでデフォルト）
SAM configuration environment [default]: （Enterでデフォルト）
```

初回デプロイ後は `samconfig.toml` が生成されるので、2回目以降は質問なしで実行できます：

```bash
sam deploy    # samconfig.toml の設定を使用
```

### Step 3: モデルを本番S3にアップロード

```bash
uv run python s3/upload_model.py
```

### AWSリソースの削除

```bash
aws s3 rm s3://$(aws cloudformation describe-stacks \
  --stack-name sam-image-classifier \
  --query 'Stacks[0].Outputs[?OutputKey==`ModelBucketName`].OutputValue' \
  --output text) --recursive

sam delete
```

## 用語集

| 用語 | 意味 |
| --- | --- |
| **SAM** | Serverless Application Model — サーバーレスアプリのフレームワーク |
| **Lambda** | サーバー管理不要でコードを実行するAWSサービス |
| **S3** | AWSのオブジェクトストレージ（バケットにファイルを保存） |
| **API Gateway** | HTTPリクエストをLambdaにルーティングするAWSサービス |
| **template.yaml** | 全AWSリソースを定義するSAMの設定ファイル |
| **コールドスタート** | Lambdaの初回起動時（初期化が必要） |
| **ウォームスタート** | 既存のコンテナを再利用する2回目以降の起動 |
| **LocalStack** | AWSサービスをローカルでエミュレートするOSSツール |
| **ONNX Runtime** | 高速なML推論エンジン（PyTorchの代替） |
| **PackageType: Image** | LambdaをZIPの代わりにDockerコンテナとしてデプロイ |
