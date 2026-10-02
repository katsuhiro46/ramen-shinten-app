# ramen-shinten-app

ラーメンDBの新店情報を表示・Push通知する Flask アプリ（Vercel 配信）。
運用の詳細（自動実行・秘密設定・復旧手順）は [OPERATIONS.md](OPERATIONS.md)、通知設定は [NOTIFICATIONS_SETUP.md](NOTIFICATIONS_SETUP.md) を参照。

## 構成
- `app.py` — Flask 本体（Vercel の `@vercel/python` で動作）
- `modules/news_scraper.py` — ラーメンDBのスクレイピング
- `modules/push_notifications.py` — Web Push 通知
- `scripts/update_snapshot.py` — スナップショット更新
- `scripts/local_ramen_update.sh` — Mac の LaunchAgent が毎日 3:35 に実行
- `data/news_snapshot.json` — 新店スナップショット（自動コミットされる）

## 重要なルール
- 秘密キー（`~/.config/ramen-shinten-app/env`、Bitwarden 管理）は絶対にコミット・出力しない。
- ラーメンDBは GitHub Actions / Vercel から 403 になるため、取得は Mac のローカル実行で行う。
- LaunchAgent の実行フォルダは `/Users/katsuhiro/ramen-shinten-app` のまま（`Documents/Codex/...` 配下は不可）。
- `data/news_snapshot.json` の "Update ramen news snapshot" コミットは自動更新によるもの。
- 本番 push・デプロイ・LaunchAgent や pmset の変更は、事前にユーザーへ確認する。

## 確認コマンド
```bash
launchctl print gui/$(id -u)/com.katsuhiro.ramen-shinten-update
tail -n 120 ~/Library/Logs/ramen-shinten-app/local_update.err.log
```
