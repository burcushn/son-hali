#!/usr/bin/env bash
# Kullanim: bash geri-yukle-veritabani.sh yedekler/mongo-yedek-20260601-0100.archive
set -e
ARCHIVE="$1"
DB=${DB_NAME:-ihracat_db}
CONTAINER=${MONGO_CONTAINER:-ihracat-mongo}

if [ -z "$ARCHIVE" ] || [ ! -f "$ARCHIVE" ]; then
  echo "Yedek dosyasi bulunamadi. Kullanim: bash geri-yukle-veritabani.sh <yedek.archive>"
  exit 1
fi

read -p "DIKKAT: $DB veritabanindaki ayni koleksiyonlar silinip yedekten yuklenecek. Devam? (e/h) " ok
[ "$ok" = "e" ] || exit 0

if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER}$"; then
  docker cp "$ARCHIVE" "$CONTAINER":/tmp/geri.archive
  docker exec "$CONTAINER" mongorestore --archive=/tmp/geri.archive --drop
  docker exec "$CONTAINER" rm -f /tmp/geri.archive
else
  mongorestore --uri="${MONGO_URL:-mongodb://localhost:27017}" --archive="$ARCHIVE" --drop
fi

echo "Geri yukleme tamamlandi."
