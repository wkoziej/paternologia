#!/bin/bash
# ABOUTME: Skrypt do przywracania backupu konkretnego urządzenia
# ABOUTME: Użycie: ./restore_device.sh <device> <backup_dir>

set -e

DEVICE=$1
BACKUP_DIR=$2

usage() {
    echo "Użycie: $0 <device> <backup_dir>"
    echo "  device: pacer | rc600 | model_samples"
    echo "  backup_dir: ścieżka do katalogu z backupem"
    echo ""
    echo "Przykład: $0 pacer ~/backup/midi_20241225_120000"
    exit 1
}

[ -z "$DEVICE" ] || [ -z "$BACKUP_DIR" ] && usage

log() { echo "[$(date +%H:%M:%S)] $1"; }

case $DEVICE in
    pacer)
        log "Restoring Pacer from $BACKUP_DIR/pacer.syx"

        if [ ! -f "$BACKUP_DIR/pacer.syx" ]; then
            log "ERROR: File not found: $BACKUP_DIR/pacer.syx"
            exit 1
        fi

        PACER_PORT=$(amidi -l 2>/dev/null | grep -i pacer | head -1 | awk '{print $2}')
        [ -z "$PACER_PORT" ] && { log "ERROR: Pacer not connected"; exit 1; }

        amidi -p "$PACER_PORT" -s "$BACKUP_DIR/pacer.syx"
        log "Pacer restore: OK"
        ;;

    rc600)
        log "Restoring RC-600 from $BACKUP_DIR/rc600_ROLAND"

        if [ ! -d "$BACKUP_DIR/rc600_ROLAND" ]; then
            log "ERROR: Directory not found: $BACKUP_DIR/rc600_ROLAND"
            exit 1
        fi

        RC600_MOUNT=$(ls -d /media/$USER/RC-600* 2>/dev/null | head -1)
        [ -z "$RC600_MOUNT" ] && { log "ERROR: RC-600 not mounted"; exit 1; }

        echo "  UWAGA: To NADPISZE wszystkie dane na RC-600!"
        read -p "Kontynuować? (yes/no): " confirm
        [ "$confirm" != "yes" ] && { log "Anulowano"; exit 0; }

        rm -rf "$RC600_MOUNT/ROLAND"
        cp -r "$BACKUP_DIR/rc600_ROLAND" "$RC600_MOUNT/ROLAND"
        sync
        log "RC-600 restore: OK"
        ;;

    model_samples)
        log "Restoring Model:Samples from $BACKUP_DIR/model_samples"

        if [ ! -d "$BACKUP_DIR/model_samples" ]; then
            log "ERROR: Directory not found: $BACKUP_DIR/model_samples"
            exit 1
        fi

        if ! command -v elektroid-cli &> /dev/null; then
            log "ERROR: elektroid-cli not installed"
            exit 1
        fi

        echo "  UWAGA: To NADPISZE dane na Model:Samples!"
        read -p "Kontynuować? (yes/no): " confirm
        [ "$confirm" != "yes" ] && { log "Anulowano"; exit 0; }

        if [ -d "$BACKUP_DIR/model_samples/data" ]; then
            elektroid-cli elektron:data:ul "$BACKUP_DIR/model_samples/data/"
            log "Data restore: OK"
        fi

        if [ -d "$BACKUP_DIR/model_samples/samples" ]; then
            elektroid-cli elektron:sample:ul -r "$BACKUP_DIR/model_samples/samples/" 0:/
            log "Samples restore: OK"
        fi
        ;;

    *)
        log "ERROR: Nieznane urządzenie: $DEVICE"
        usage
        ;;
esac
