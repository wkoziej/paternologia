#!/bin/bash
# ABOUTME: Skrypt do backupu wszystkich urządzeń MIDI
# ABOUTME: Użycie: ./backup_all.sh [--dry-run]

set -e

BACKUP_ROOT=~/backup/midi_$(date +%Y%m%d_%H%M%S)
DRY_RUN=${1:-""}

log() { echo "[$(date +%H:%M:%S)] $1"; }
run() {
    if [ "$DRY_RUN" = "--dry-run" ]; then
        echo "[DRY-RUN] $@"
    else
        "$@"
    fi
}

mkdir -p "$BACKUP_ROOT"
log "Backup directory: $BACKUP_ROOT"

# ═══════════════════════════════════════════════════════════════════════
# 1. NEKTAR PACER
# ═══════════════════════════════════════════════════════════════════════
log "=== Nektar Pacer ==="
PACER_PORT=$(amidi -l 2>/dev/null | grep -i pacer | head -1 | awk '{print $2}' || true)

if [ -n "$PACER_PORT" ]; then
    log "Pacer found at $PACER_PORT"
    run amidi -p "$PACER_PORT" \
        -S "F0 00 01 77 7F 02 7F F7" \
        -r "$BACKUP_ROOT/pacer.syx" -t 10
    log "Pacer backup: OK"
else
    log "Pacer: NOT CONNECTED"
fi

# ═══════════════════════════════════════════════════════════════════════
# 2. BOSS RC-600
# ═══════════════════════════════════════════════════════════════════════
log "=== BOSS RC-600 ==="
RC600_MOUNT=$(ls -d /media/$USER/RC-600* 2>/dev/null | head -1 || true)

if [ -d "$RC600_MOUNT/ROLAND" ]; then
    log "RC-600 mounted at $RC600_MOUNT"
    run cp -r "$RC600_MOUNT/ROLAND" "$BACKUP_ROOT/rc600_ROLAND"
    log "RC-600 backup: OK ($(du -sh "$BACKUP_ROOT/rc600_ROLAND" 2>/dev/null | cut -f1))"
else
    log "RC-600: NOT MOUNTED (przełącz na tryb STORAGE)"
fi

# ═══════════════════════════════════════════════════════════════════════
# 3. ELEKTRON MODEL:SAMPLES
# ═══════════════════════════════════════════════════════════════════════
log "=== Elektron Model:Samples ==="

if command -v elektroid-cli &> /dev/null; then
    MS_DEVICE=$(elektroid-cli ld 2>/dev/null | grep -i "model" | head -1 || true)

    if [ -n "$MS_DEVICE" ]; then
        log "Model:Samples found: $MS_DEVICE"
        mkdir -p "$BACKUP_ROOT/model_samples"/{data,samples}

        run elektroid-cli elektron:data:rdl "$BACKUP_ROOT/model_samples/data/"
        log "Model:Samples data backup: OK"

        run elektroid-cli elektron:sample:dl -r "$BACKUP_ROOT/model_samples/samples/" 0:/
        log "Model:Samples samples backup: OK"
    else
        log "Model:Samples: NOT CONNECTED"
    fi
else
    log "Model:Samples: elektroid-cli NOT INSTALLED"
    log "  Install: flatpak install flathub io.github.dagargo.Elektroid"
fi

# ═══════════════════════════════════════════════════════════════════════
# 4. ARTURIA MICROFREAK
# ═══════════════════════════════════════════════════════════════════════
log "=== Arturia MicroFreak ==="
MF_PORT=$(amidi -l 2>/dev/null | grep -i "microfreak\|arturia" | head -1 | awk '{print $2}' || true)

if [ -n "$MF_PORT" ]; then
    log "MicroFreak found at $MF_PORT"
    log "  MicroFreak backup wymaga MIDI Control Center (Windows/Mac)"
    log "  Alternatywa: https://studiocode.dev/doc/microfreak-reader/ (tylko podgląd)"
else
    log "MicroFreak: NOT CONNECTED"
fi

# ═══════════════════════════════════════════════════════════════════════
# PODSUMOWANIE
# ═══════════════════════════════════════════════════════════════════════
echo ""
log "═══════════════════════════════════════════"
log "BACKUP COMPLETE"
log "═══════════════════════════════════════════"
log "Location: $BACKUP_ROOT"
ls -la "$BACKUP_ROOT" 2>/dev/null || true
du -sh "$BACKUP_ROOT" 2>/dev/null || true
