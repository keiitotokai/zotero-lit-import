# zotero-lit-import — 配布・導入手順

文献リスト（DOI等）を CrossRef で照合し、Zotero ライブラリの
指定コレクションに journalArticle として一括投入する Claude Science スキルです。
投入先コレクションは実行のたびにユーザーへ確認します。

## 同梱ファイル
- `SKILL.md`  — スキル定義・ワークフロー
- `kernel.py` — 自動読込ヘルパー関数群

## 導入手順（各ユーザーが自分の環境で実施）

### 1. 自分の Zotero API キーを用意
1. https://www.zotero.org/settings/keys を開く
2. "Create new private key" → "Allow library access" と
   "Allow write access" を有効化して保存
3. 表示された API キー文字列をコピー（この画面でしか表示されません）

### 2. Claude Science にクレデンシャル登録
- 左サイドバー Customize → Credentials → Add Credential
- 名前を **ZOTERO**、値に上記 API キーを設定（generic シークレット）

### 3. スキルを自分のスキルセットに登録
Claude Science の repl ツールで、同梱の2ファイルの中身を渡して登録します:

```python
ksrc = open("kernel.py").read()
msrc = open("SKILL.md").read()
host.skills.edit("zotero-lit-import", "SKILL.md", msrc)
host.skills.edit("zotero-lit-import", "kernel.py", ksrc)
host.skills.publish("zotero-lit-import")
```

### 4. ネットワーク許可
初回実行時 `api.zotero.org`（および CrossRef 照合用に `api.crossref.org`）へのアクセス許可が求められます。承認してください。

## 使い方
`skill("zotero-lit-import")` を読み込み、投入したい文献の DOI リストを
渡してください。コレクションを尋ねられるので選択（新規作成も可）すると投入されます。

## セキュリティ上の注意（重要）
- このスキルは各自の `ZOTERO` クレデンシャルから API キーを読みます。
  キー自体はスキルに含まれません。
- **自分の API キーを他人に配らないでください。** 配ると相手が
  あなたの Zotero ライブラリに書き込めてしまいます。各自が自分の
  キーを登録して使ってください。
- 投入されるアイテムに PDF 本文は添付されません。

## 個人情報について
配布ファイル（SKILL.md / kernel.py）には、特定個人の氏名・
メールアドレス・API キー・ユーザーID・コレクションID等は
一切含まれていません（すべて実行時の動的参照）。
