# Python 3.11 をベースに使用（AWS Lambdaとも互換あり）
FROM python:3.11-slim

# 作業ディレクトリ作成
WORKDIR /app

# 必要ファイルをコピー
COPY requirements.txt .
COPY main.py .

# 依存パッケージのインストール
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install python-dotenv

# 環境変数を使って起動できるようにする（.env 読み込みは main.py 側で対応）
CMD ["python", "main.py"]