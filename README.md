
# Grants Harvester（自治体・医療/介護/DX向け）

APIが無いサイトでも **RSS / CKAN / サイトマップ / HTML / PDF** を組み合わせて
補助金・助成金・公募情報を自動収集するための最小フレームワークです。

> ⚠️ 実運用では各サイトの利用規約・robots.txtを遵守し、レート制限や並列度を適切に設定してください。

## 使い方（ローカル）

1. Python 3.10+ を用意し、必要パッケージをインストール：
   ```bash
   pip install requests pyyaml pdfminer.six
   # （必要に応じて）pip install beautifulsoup4 readability-lxml
   ```

2. `config/sources.yaml` に収集対象を追記します（後述）。

3. 実行：
   ```bash
   python run.py --sources config/sources.yaml --keywords config/keywords.yaml --out out
   ```

4. 出力：`out/grants_*.jsonl`（1行1レコード）と `out/grants_*.csv`。

## 拡張方法

- **収集先を増やす**：`config/sources.yaml` の `sources:` 配列に辞書を追加
  - `type: rss|ckan|sitemap|html|pdf`
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

- `util/fetch.py`：ETag / Last-Modified による差分取得。`GRANTS_CACHE_DIR` でキャッシュ先変更可。
- `include_patterns / exclude_patterns`：正規表現でフィルタ（日本語OK）。
- `issuer_level`：`prefecture|municipality|national|agency` など自由に運用可能。

