#!/bin/bash

# --- Configuration ---
# Directory to watch and sync
WATCH_DIR="/home/ryan/projects" 

# Git branch to push to
GIT_BRANCH="main" 

# Format for automatic commit messages
COMMIT_MSG="Auto-sync: Files changed on $(date +'%Y-%m-%d %H:%M:%S')"
# --- End Configuration ---

# --- Script Logic ---

# Check if the watch directory exists
if [ ! -d "$WATCH_DIR" ]; then
  # Log error to standard error
  echo "$(date): Error: Watch directory '$WATCH_DIR' not found." >&2
  exit 1 # Exit the script if directory doesn't exist
fi

# Navigate into the repository directory. Exit if fails.
cd "$WATCH_DIR" || { echo "$(date): Error: Could not cd into '$WATCH_DIR'." >&2; exit 1; }

echo "$(date): Monitoring directory '$WATCH_DIR' for changes, syncing to branch '$GIT_BRANCH'..."

# Loop forever to keep monitoring
while true; do
  # Wait for any file modification, creation, deletion, or move event recursively
  # The '-q' option can be added after '-e' for quieter operation (less verbose inotifywait output)
  # Example: inotifywait -q -r -e modify,create,delete,move "$WATCH_DIR"
  inotifywait -r -e modify,create,delete,move "$WATCH_DIR"

  echo "$(date): Change detected in '$WATCH_DIR'. Staging changes..."
  
  # Stage all changes (new files, modifications, deletions) respecting .gitignore
  git add .

  # Check if there are actually any changes staged
  # Prevents empty commits if files were changed then changed back quickly
  if git diff --staged --quiet; then
    echo "$(date): No actual changes staged to commit."
  else
    # Commit the staged changes
    echo "$(date): Committing staged changes..."
    git commit -m "$COMMIT_MSG"

    # Attempt to push the commit(s) to the remote repository
    echo "$(date): Pushing changes to GitHub (origin/$GIT_BRANCH)..."
    if git push origin "$GIT_BRANCH"; then
      # Push was successful
      echo "$(date): Push successful."
    else
      # Push failed! Log error to standard error.
      # This usually requires manual intervention (git pull, resolve conflicts, git push)
      # in the WATCH_DIR before the script can push successfully again.
      echo "$(date): Error: git push failed. Remote likely has changes not present locally." >&2
      echo "$(date): Manual intervention (git pull/push) likely needed in '$WATCH_DIR'." >&2
    fi
  fi
  
  # Brief pause to prevent excessive commits if many files change simultaneously
  sleep 2 
done

# Script execution technically never reaches here in normal operation due to infinite loop
exit 0
