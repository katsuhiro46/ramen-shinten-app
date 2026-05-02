# 新店通知の設定

このアプリは PWA + Web Push + Upstash Redis で新店通知を送ります。

## 必要な環境変数

Vercel と GitHub Actions の両方に同じ値を設定します。

- `APP_BASE_URL`: 本番URL
- `UPSTASH_REDIS_REST_URL`: Upstash Redis REST URL
- `UPSTASH_REDIS_REST_TOKEN`: Upstash Redis REST Token
- `VAPID_PUBLIC_KEY`: Web Push の公開鍵
- `VAPID_PRIVATE_KEY`: Web Push の秘密鍵
- `VAPID_SUBJECT`: 連絡先。例: `mailto:your-email@example.com`

## VAPIDキーの作成例

ローカルで以下を実行すると公開鍵と秘密鍵を作れます。

```bash
npx web-push generate-vapid-keys --json
```

出力された `publicKey` を `VAPID_PUBLIC_KEY`、`privateKey` を `VAPID_PRIVATE_KEY` に設定します。

## 通知の流れ

1. スマホでアプリを開く
2. iPhoneの場合はホーム画面に追加してから開く
3. 「新店通知を受け取る」を押す
4. 通知を許可する
5. GitHub Actions が1日1回スナップショットを更新する
6. 前回より新しい店舗が増えていたら通知を送る

## 注意

Vercel本番からラーメンDBへの直接取得は403になるため、画面表示はスナップショットフォールバックを使います。
通知の差分検出は GitHub Actions の更新時に行います。
