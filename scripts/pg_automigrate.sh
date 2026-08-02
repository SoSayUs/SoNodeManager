#!/bin/bash
set -e


# If postgres is auto updated on mac, migrate data to new version. 
# Not tested.


# Find all installed pg data dirs and their versions
OLD_VERSION=$(cat /opt/homebrew/var/postgresql@*/PG_VERSION 2>/dev/null | sort -n | head -1)
NEW_VERSION=$(cat /opt/homebrew/var/postgresql@*/PG_VERSION 2>/dev/null | sort -n | tail -1)

if [ "$OLD_VERSION" == "$NEW_VERSION" ]; then
    echo "Only one PostgreSQL version found, no migration needed."
    exit 0
fi

OLD_DIR="/opt/homebrew/var/postgresql@${OLD_VERSION}"
NEW_DIR="/opt/homebrew/var/postgresql@${NEW_VERSION}"
OLD_BIN="/opt/homebrew/opt/postgresql@${OLD_VERSION}/bin"
NEW_BIN="/opt/homebrew/opt/postgresql@${NEW_VERSION}/bin"
BACKUP="$HOME/pg_migration_${OLD_VERSION}_to_${NEW_VERSION}_$(date +%Y%m%d_%H%M%S).sql"

echo "Detected upgrade from pg${OLD_VERSION} to pg${NEW_VERSION}"

# Remove stale PID if present
[ -f "$OLD_DIR/postmaster.pid" ] && rm "$OLD_DIR/postmaster.pid"
[ -f "$NEW_DIR/postmaster.pid" ] && rm "$NEW_DIR/postmaster.pid"

# Stop new version, start old to dump
brew services stop "postgresql@${NEW_VERSION}" || true
"$OLD_BIN/pg_ctl" -D "$OLD_DIR" -l /tmp/pg_old.log start
sleep 3

echo "Dumping pg${OLD_VERSION} data to $BACKUP..."
"$OLD_BIN/pg_dumpall" -p 5432 > "$BACKUP"

"$OLD_BIN/pg_ctl" -D "$OLD_DIR" stop
sleep 2

# Start new version and restore
brew services start "postgresql@${NEW_VERSION}"
sleep 3

echo "Restoring into pg${NEW_VERSION}..."
psql -p 5432 postgres -f "$BACKUP"

# Cleanup old version
echo "Removing old pg${OLD_VERSION} cluster..."
brew services stop "postgresql@${OLD_VERSION}" || true
brew uninstall "postgresql@${OLD_VERSION}" || true
rm -rf "$OLD_DIR"
echo "Old pg${OLD_VERSION} cluster removed."

echo "Migration complete. Backup kept at $BACKUP"
echo "Verify with: psql -p 5432 postgres -c '\l'"