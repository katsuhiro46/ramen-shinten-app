# ramen-shinten-app 運用メモ

## アプリ概要

`ramen-shinten-app` は、ラーメンデータベースのニューオープン情報を確認・通知するWebアプリです。

- GitHub: `katsuhiro46/ramen-shinten-app`
- 本番URL: `https://ramen-shinten-app.vercel.app/`
- ローカル作業フォルダ: `/Users/katsuhiro/ramen-shinten-app`
- デスクトップの `ramen-shinten-app` は、このフォルダへのショートカットです。

## 通知

- 通知タイトル: `ラ`
- 通知本文: `ラーメン新店が追加されました` または `ラーメン新店がN件追加されました`
- 新店がある時だけ通知します。
- 通知を押すとラーメン新店速報ページを開きます。
- 追加店はページ上部にまとめて表示し、県別一覧でも `NEW` を付けます。
- 最新の追加店は端末にかかわらず、次の追加分が来るまで `NEW` 表示を続けます。
- 最新表示の下に、過去30日間の追加店を新しい順で確認できる開閉式一覧を表示します。
- 通知から開いた場合は、その通知に対応する追加店を表示します。
- 追加履歴はスナップショットに30日間保持します。
- Push購読先が期限切れで削除された場合は、次にアプリを開いた時に自動で再登録します。

## 現在の自動実行

### ラーメン更新

Macで実行します。

- Mac自動起床: 毎日 3:33
- ラーメン更新: 毎日 3:35
- 実行設定: `~/Library/LaunchAgents/com.katsuhiro.ramen-shinten-update.plist`
- 実行スクリプト: `/Users/katsuhiro/ramen-shinten-app/scripts/local_ramen_update.sh`
- ログ:
  - `~/Library/Logs/ramen-shinten-app/local_update.out.log`
  - `~/Library/Logs/ramen-shinten-app/local_update.err.log`

ラーメンDBは GitHub Actions / Vercel からだと 403 で拒否されるため、Macから取得します。

## 秘密設定

秘密キーはGitHubに入れません。

Mac内の設定ファイル:

```text
~/.config/ramen-shinten-app/env
```

Bitwardenには `ramen-shinten-app secrets` として以下を保存しています。

```text
APP_BASE_URL
UPSTASH_REDIS_REST_URL
UPSTASH_REDIS_REST_TOKEN
VAPID_PUBLIC_KEY
VAPID_PRIVATE_KEY
VAPID_SUBJECT
```

特に秘密扱い:

```text
UPSTASH_REDIS_REST_TOKEN
VAPID_PRIVATE_KEY
```

## 重要な注意点

- Macは電源OFFにしない。スリープ運用ならOK。
- 自動実行中はスクリプト内の `caffeinate` で一時的にスリープを防ぎます。
- 自動実行フォルダは `/Users/katsuhiro/ramen-shinten-app` を使います。
- `Documents/Codex/...` 配下でLaunchAgentを動かすと `Operation not permitted` になることがありました。
- スマホ通知が不安定な時は、ホーム画面のアプリを開いて通知登録を停止→再開すると直る場合があります。

## よく使う確認コマンド

Mac自動起床の確認:

```bash
pmset -g sched
```

ラーメン更新設定の確認:

```bash
launchctl print gui/$(id -u)/com.katsuhiro.ramen-shinten-update
```

ラーメン更新ログ:

```bash
tail -n 120 ~/Library/Logs/ramen-shinten-app/local_update.out.log
tail -n 120 ~/Library/Logs/ramen-shinten-app/local_update.err.log
```

## 復旧手順の概要

新しいMacに移す時は以下の順番です。

1. GitHubから `katsuhiro46/ramen-shinten-app` を取得する。
2. `/Users/katsuhiro/ramen-shinten-app` に配置する。
3. Bitwardenの `ramen-shinten-app secrets` から6個の環境変数を取り出す。
4. `~/.config/ramen-shinten-app/env` を作って貼る。
5. `scripts/local_ramen_update.sh` を一度実行して確認する。
6. LaunchAgentを登録し直す。
7. `pmset` でMac自動起床を設定する。
