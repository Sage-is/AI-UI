#!/bin/bash

# Source environment variables
if [ -f /app/.env ]; then
  echo "Sourcing /app/.env..."
  . /app/.env
else
  echo "No /app/.env found. Using environment and env.sh variables."
fi

# function to setup rclone config
setup_rclone() {
  # Create rclone config directory
  config_dir="${HOME}/.config/rclone"
  mkdir -p "$config_dir" || {
    echo "Failed to create config directory"
    return 1
  }

  # Find all unique remotes by scanning environment variables that start with RCLONE_CONFIG_
  remotes=$(env | grep -E '^RCLONE_CONFIG_[^_]+_TYPE=' | sed 's/RCLONE_CONFIG_\([^_]*\)_TYPE=.*/\1/' | sort -u)

  if [ -z "$remotes" ]; then
    echo "No remotes found"
    return 0
  fi

  echo "Found remotes: $remotes"
  echo "Generating rclone configuration for all remotes..."

  # Generate rclone config file
  for REMOTE in $remotes; do
    echo "Generating configuration for $REMOTE..."
    {
      echo "[$REMOTE]"
      echo "type = $(eval echo \$RCLONE_CONFIG_${REMOTE}_TYPE)"
      env | grep "^RCLONE_CONFIG_${REMOTE}_" | sed "s/^RCLONE_CONFIG_${REMOTE}_//" |
        sed 's/=/ = /' | awk -F' = ' '{print tolower($1)" = "$2}' | grep -v '^type = '
    } >>"$config_dir/rclone.conf" || {
      echo "Failed to write config for $REMOTE"
      return 1
    }
  done

  echo "Rclone configuration generated."
  echo ""
  echo "*********"
  cat "$config_dir/rclone.conf"
  echo "*********"
}

# Function to perform backup
backup() {
  echo "$(date): Starting backup of /app/backend/data/ to $RCLONE_REMOTE:/$BACKUP_PATH ..."
  echo "rclone copy /app/backend/data/ $RCLONE_REMOTE:/$BACKUP_PATH"
  rclone -vv copy /app/backend/data/ "$RCLONE_REMOTE:/$BACKUP_PATH"
  echo "$(date): Backup of /app/backend/data/ to $RCLONE_REMOTE:/$BACKUP_PATH completed."
}

# Function to perform restore
restore_backup() {
  echo "$(date): Checking for backup at $RCLONE_REMOTE..."
  if rclone -vv lsf "$RCLONE_REMOTE:$BACKUP_PATH" >/dev/null 2>&1; then
    # Echo the date & time at which the backup was found
    echo "$(date): Backup found at $RCLONE_REMOTE ."
    rclone -vv copy "$RCLONE_REMOTE:$BACKUP_PATH" /app/backend/data/

    echo "$(date): Backup restored successfully."
  else
    echo "$(date): No backup found at $RCLONE_REMOTE. Using existing files."
  fi
}

# Function to schedule backups
schedule_backups() {
  local MINUTE HOUR DAY
  IFS=' ' read -r MINUTE HOUR DAY <<<"$BACKUP_CRON"

  echo "Scheduling backups with cron expression: $BACKUP_CRON"

  while true; do
    CURRENT_MINUTE=$(date +%-M)
    CURRENT_HOUR=$(date +%-H)
    CURRENT_DAY=$(date +%-d)

    MATCHED=true

    # Check minute
    if [ "$MINUTE" != "*" ]; then
      if [ "$MINUTE" != "$CURRENT_MINUTE" ]; then
        MATCHED=false
      fi
    fi

    # Check hour
    if [ "$HOUR" != "*" ]; then
      if [ "$HOUR" != "$CURRENT_HOUR" ]; then
        MATCHED=false
      fi
    fi

    # Check day
    if [ "$DAY" != "*" ]; then
      if [ "$DAY" != "$CURRENT_DAY" ]; then
        MATCHED=false
      fi
    fi

    if [ "$MATCHED" = true ]; then
      echo "Time matches the backup schedule, running backup..."
      backup
      # Sleep for 60 seconds to avoid running backup multiple times in the same minute
      sleep 60
    else
      # Sleep until the start of the next minute
      sleep $((60 - $(date +%S)))
    fi
  done
}

# Function to restore a backup if AUTO_RESTORE is set to true
restore_if_needed() {
  if [ "$AUTO_RESTORE" = "true" ]; then
    echo "AUTO_RESTORE is set to true. Restoring backup..."
    restore_backup
  fi
}
# Function to enable auto backup if AUTO_BACKUP is set to true
enable_auto_backup_if_needed() {
  if [ "$AUTO_BACKUP" = "true" ]; then
    echo "AUTO_BACKUP is set to true. Scheduling backups..."
    # Function to schedule backups or run a custom backup hook
    schedule_or_hook() {
      if [ -z "$BACKUP_HOOK" ]; then
        BACKUP_CRON="${BACKUP_CRON:-0 5 *}" # Default to '0 5 *' (5:00 AM every day)
        schedule_backups &
      else
        # Run custom backup hook if provided
        eval "$BACKUP_HOOK"
      fi
    }
  else
    echo "AUTO_BACKUP is set to false. Not scheduling backups."
  fi
}

# Common function to start the application with a given command
start_common() {
  local start_command=$1
  APP_PID=""
  BACKUP_PID=""

  # Set up trap to catch termination signals
  trap cleanup SIGTERM SIGINT

  # Cleanup function to handle graceful shutdown
  cleanup() {
    echo "Received termination signal. Shutting down gracefully..."
    
    # Kill the backup scheduler if it's running
    if [ -n "$BACKUP_PID" ]; then
      echo "Stopping backup scheduler (PID: $BACKUP_PID)..."
      kill -TERM "$BACKUP_PID" 2>/dev/null || true
    fi
    
    # Kill the main application if it's running
    if [ -n "$APP_PID" ]; then
      echo "Stopping application (PID: $APP_PID)..."
      kill -TERM "$APP_PID" 2>/dev/null || true
    fi
    
    echo "Cleanup complete. Exiting."
    exit 0
  }

  # Restore backup if needed
  restore_if_needed

  # Start the application using the provided command
  $start_command &
  APP_PID=$!
  echo "Started application with PID: $APP_PID"

  # Schedule backups if needed
  if [ "$AUTO_BACKUP" = "true" ]; then
    echo "AUTO_BACKUP is set to true. Scheduling backups..."
    if [ -z "$BACKUP_HOOK" ]; then
      BACKUP_CRON="${BACKUP_CRON:-0 5 *}" # Default to '0 5 *' (5:00 AM every day)
      schedule_backups &
      BACKUP_PID=$!
      echo "Started backup scheduler with PID: $BACKUP_PID"
    else
      # Run custom backup hook if provided
      eval "$BACKUP_HOOK" &
      BACKUP_PID=$!
      echo "Started backup hook with PID: $BACKUP_PID"
    fi
  else
    echo "AUTO_BACKUP is set to false. Not scheduling backups."
  fi

  # Wait for any process to exit
  wait
}

# Function to start the application in production mode
start_app() {
  echo "Starting application in production mode..."
  start_common "./start.sh"
}

# Function to start the application in development mode
start_dev() {
  echo "Starting application in development mode..."
  start_common "./dev.sh"
}

# Main execution logic
case "$1" in
backup)
  backup
  ;;
restore)
  restore_backup
  ;;
setup_rclone)
  setup_rclone
  ;;
server)
  setup_rclone
  # enable auto backup
  export AUTO_BACKUP=true
  start_app
  ;;
dev)
  setup_rclone
  # disable auto backup
  export AUTO_BACKUP=false
  start_dev
  ;;
*)
  # Dynamically generate usage options by parsing the case statement
  options=$(awk '/case "\$1" in/,/\*)/' "$0" | grep -E '^\s+[^\|\)]+' | sed 's/)//;s/)//;s/^\s*//')
  echo "Usage: $0 {$(echo $options | tr '\n' '|')}"
  exit 1
  ;;
esac

# Exit with status of process that exited first
wait -n
exit $?
