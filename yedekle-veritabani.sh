#!/usr/bin/env bash
# MongoDB yedegi alir -> yedekler/mongo-yedek-<tarih>.archive
set -e
DB=${DB_NAME:-ihracat_db}
CONTAINER=${MONGO_CONTAINER:-ihracat-mongo}
DIR="$(cd "$(dirname "$0")" && pwd)/yedekler"
mkdir -p "$DIR"
STAMP=$(date +%Y%m%d-%H%M)
OUT="$DIR/mongo-yedek-$STAMP.archive"

if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER}$"; then
  echo "Docker konteyneri kullaniliyor: $CONTAINER"
  docker exec "$CONTAINER" mongodump --db="$DB" --archive=/tmp/yedek.archive
  docker cp "$CONTAINER":/tmp/yedek.archive "$OUT"
  docker exec "$CONTAINER" rm -f /tmp/yedek.archive
else
  echo "Yerel mongodump kullaniliyor"
  mongodump --uri="${MONGO_URL:-mongodb://localhost:27017}" --db="$DB" --archive="$OUT"
fi

echo "Yedek olusturuldu: $OUT"
ls -lh "$OUT"
# 30 gunden eski yedekleri sil
find "$DIR" -name 'mongo-yedek-*.archive' -mtime +30 -delete 2>/dev/null || true
