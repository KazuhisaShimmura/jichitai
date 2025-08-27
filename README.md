
# Grants Harvester（自治体・医療/介護/DX向け）

APIが無いサイトでも **RSS / サイトマップ / HTML / PDF** を組み合わせて
補助金・助成金・公募情報を自動収集するための最小フレームワークです。

> ⚠️ 実運用では各サイトの利用規約・robots.txtを遵守し、レート制限や並列度を適切に設定してください。

## 使い方（ローカル）

1. Python 3.10+ を用意し、`requirements.txt` を使って必要パッケージをインストールします。
   ```bash
   pip install -r requirements.txt
   ```

2. `config/sources.yaml` に収集対象を追記します（後述）。

3. 実行：
   ```bash
   python run.py --sources config/sources.yaml --keywords config/keywords.yaml --out out
   ```

4. 出力：`out/grants_*.jsonl`（1行1レコード）と `out/grants_*.csv`。

## 自動更新（GitHub Actions）

このリポジトリは、GitHub Actionsを利用して毎日自動で情報を収集・更新するように設定されています。

- **スケジュール**: 毎日午前7時（日本時間）に実行されます。
- **処理内容**: `run.py` を実行し、新しい情報が見つかった場合は `out/` ディレクトリとキャッシュファイルを自動でコミット＆プッシュします。
- **設定ファイル**: `.github/workflows/update_grants.yml`

## 拡張方法

- **収集先を増やす**：`config/sources.yaml` の `sources:` 配列に辞書を追加
  - `type: rss|sitemap|html|pdf`
  - 例：
    ```yaml
    - type: rss
      name: "〇〇市 新着RSS"
      url: "https://www.city.example.jp/rss.xml"
      issuer_name: "〇〇市"
      issuer_level: "municipality"
      region_code: "13-001"   # 任意のコード（JIS 0402などを推奨）
      include_patterns: ["補助金|助成|募集|公募"]
      exclude_patterns: ["結果|終了"]
    ```

- **医療・介護の重みづけ**：`config/keywords.yaml` の `categories` を編集。
  本テンプレは **medical / care を高ウェイト** に設定済み。

- **パーサ精度の向上**：
  - HTML抽出は `harvesters/html.py` の `_extract_text` を BeautifulSoup/readability に差し替え可。
  - PDF抽出は `harvesters/pdf.py` で `pdfminer.six` を使用。より高精度が必要なら `pdfplumber` も検討。

- **データ整形**：スキーマは `grants_harvester/schema.py`。必要ならフィールド追加し、
  `pipeline.py` のCSV出力列も調整してください。

## 設計メモ

- **差分取得**: `util/fetch.py` は、サーバ負荷を軽減するため ETag / Last-Modified ヘッダを利用した差分取得に対応しています。キャッシュは `.cache/` ディレクトリに保存されます。
- **User-Agent**: クローラの身元を明示するため、連絡先を含むUser-Agentを設定することを推奨します。本リポジトリでは、GitHub Actions実行時に環境変数経由で安全に設定する仕組みを採用しています。
- `include_patterns / exclude_patterns`：正規表現でフィルタ（日本語OK）。
- `issuer_level`：`prefecture|municipality|national|agency` など自由に運用可能。
- **収集方針**: 著作権や元サイトへの配慮から、本クローラは「発見と導線」に徹します。
  - **RSS**: 新規情報の「検知」にのみ利用し、タイトルとURLのみを保存します。本文や募集期間などの詳細は保存しません。
  - **HTML/PDF**: ページ内から関連キーワードに合致するリンクを抽出します。詳細情報はリンク先の元サイトで確認することを前提としています。
