#!/usr/bin/env bash
# Initialize planning files for a new session.
#
# Usage:
#   ./init-session.sh                              # legacy: root-level task_plan.md, findings.md, progress.md
#   ./init-session.sh [--template TYPE]            # legacy with template choice
#   ./init-session.sh "Backend Refactor"           # slug mode: .planning/<date>-backend-refactor/
#   ./init-session.sh --plan-dir                   # slug mode with auto-generated untitled-<short> name
#   ./init-session.sh --plan-dir "Quick Spike"     # slug mode, explicit slug
#
# Legacy mode (zero positional args, no --plan-dir) preserves v1.x behavior so
# upgrades stay non-breaking. Slug mode addresses parallel multi-task isolation
# (issue #148) by writing each plan under .planning/<date>-<slug>/ and pinning
# .planning/.active_plan so resolve-plan-dir.sh can find it.

set -e

TEMPLATE="default"
PROJECT_NAME=""
USE_PLAN_DIR=0

while [[ $# -gt 0 ]]; do
    case "$1" in
        --template|-t)
            TEMPLATE="$2"
            shift 2
            ;;
        --plan-dir)
            USE_PLAN_DIR=1
            shift
            ;;
        *)
            if [ -z "$PROJECT_NAME" ]; then
                PROJECT_NAME="$1"
            else
                PROJECT_NAME="$PROJECT_NAME $1"
            fi
            shift
            ;;
    esac
done

DATE=$(date +%Y-%m-%d)

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILL_ROOT="$(dirname "$SCRIPT_DIR")"
TEMPLATE_DIR="$SKILL_ROOT/templates"

if [ "$TEMPLATE" != "default" ] && [ "$TEMPLATE" != "analytics" ]; then
    echo "Unknown template: $TEMPLATE (available: default, analytics). Using default."
    TEMPLATE="default"
fi

# Slug mode triggers when a project name was given OR --plan-dir was passed.
SLUG_MODE=0
if [ -n "$PROJECT_NAME" ] || [ "$USE_PLAN_DIR" -eq 1 ]; then
    SLUG_MODE=1
fi

slugify() {
    # Lowercase, non-alphanumerics → '-', collapse repeats, trim leading/trailing '-'
    printf '%s' "$1" \
        | tr '[:upper:]' '[:lower:]' \
        | sed -e 's/[^a-z0-9]/-/g' -e 's/-\{2,\}/-/g' -e 's/^-//' -e 's/-$//' \
        | cut -c1-40
}

short_uuid() {
    # Probe each candidate: command -v alone is not enough on Windows because
    # App Execution Aliases report presence but exit non-zero when run.
    _py="${PYTHON_BIN:-}"
    if [ -z "$_py" ]; then
        for _c in python3 python py; do
            if command -v "$_c" >/dev/null 2>&1 && "$_c" -c "import uuid" >/dev/null 2>&1; then
                _py="$_c"
                break
            fi
        done
    fi
    if [ -n "$_py" ]; then
        "$_py" -c "import uuid; print(uuid.uuid4().hex[:8])"
        return
    fi
    if command -v uuidgen >/dev/null 2>&1; then
        uuidgen | tr '[:upper:]' '[:lower:]' | tr -d '-' | cut -c1-8
        return
    fi
    # Last-ditch: seconds timestamp as 8 hex chars
    printf '%08x' "$(date +%s)" | cut -c1-8
}

safe_session_id() {
    local raw="$1"
    local session_id
    session_id="$(printf '%s' "$raw" \
        | sed -nE 's/.*([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}).*/\1/p' \
        | tail -n 1 \
        | tr '[:upper:]' '[:lower:]')"
    if [ -n "$session_id" ]; then
        printf '%s\n' "$session_id"
        return 0
    fi
    if [ -z "$raw" ]; then
        return 0
    fi
    case "$raw" in
        *[!A-Za-z0-9_.-]*)
            return 0
            ;;
    esac
    if [ "${#raw}" -ge 8 ] && [ "${#raw}" -le 160 ]; then
        printf '%s\n' "$raw"
    fi
}

session_id_from_env() {
    local key raw session_id
    for key in PWF_SESSION_ID CODEX_THREAD_ID CODEX_CONVERSATION_ID CODEX_SESSION_ID; do
        eval "raw=\${$key:-}"
        session_id="$(safe_session_id "$raw")"
        if [ -n "$session_id" ]; then
            printf '%s\n' "$session_id"
            return 0
        fi
    done
}

bind_session_plan_if_available() {
    local plan_root="$1"
    local plan_id="$2"
    local session_id session_plan_path
    session_id="$(session_id_from_env)"
    if [ -z "$session_id" ]; then
        echo "[planning-with-files] No stable session id in environment; PostToolUse will try to bind this session."
        return 0
    fi
    mkdir -p "${plan_root}/sessions"
    session_plan_path="${plan_root}/sessions/${session_id}.active_plan"
    printf "%s\n" "$plan_id" > "$session_plan_path"
    printf "attached\n" > "${plan_root}/sessions/${session_id}.attached"
    echo "[planning-with-files] Session plan bound: $session_plan_path"
}

write_default_task_plan() {
    cat > "$1" << 'EOF'
# Task Plan: [Brief Description]

## Goal
[One sentence describing the end state]

## Current Phase
Phase 1

## Phases

### Phase 1: Requirements & Discovery
- [ ] Understand user intent
- [ ] Identify constraints
- [ ] Document in findings.md
- **Status:** in_progress

### Phase 2: Planning & Structure
- [ ] Define approach
- [ ] Create project structure
- **Status:** pending

### Phase 3: Implementation
- [ ] Execute the plan
- [ ] Write to files before executing
- **Status:** pending

### Phase 4: Testing & Verification
- [ ] Verify requirements met
- [ ] Document test results
- **Status:** pending

### Phase 5: Delivery
- [ ] Review outputs
- [ ] Deliver to user
- **Status:** pending

## Decisions Made
| Decision | Rationale |
|----------|-----------|

## Errors Encountered
| Error | Resolution |
|-------|------------|
EOF
}

write_default_findings() {
    cat > "$1" << 'EOF'
# Findings & Decisions

## Requirements
-

## Research Findings
-

## Technical Decisions
| Decision | Rationale |
|----------|-----------|

## Issues Encountered
| Issue | Resolution |
|-------|------------|

## Resources
-
EOF
}

write_default_progress() {
    local date_value="$1"
    local target="$2"
    cat > "$target" << EOF
# Progress Log

## Session: $date_value

### Current Status
- **Phase:** 1 - Requirements & Discovery
- **Started:** $date_value

### Actions Taken
-

### Test Results
| Test | Expected | Actual | Status |
|------|----------|--------|--------|

### Errors
| Error | Resolution |
|-------|------------|
EOF
}

write_analytics_progress() {
    local date_value="$1"
    local target="$2"
    cat > "$target" << EOF
# Progress Log

## Session: $date_value

### Current Status
- **Phase:** 1 - Data Discovery
- **Started:** $date_value

### Actions Taken
-

### Query Log
| Query | Result Summary | Interpretation |
|-------|---------------|----------------|

### Errors
| Error | Resolution |
|-------|------------|
EOF
}

create_files_in() {
    local target_dir="$1"
    local plan_path="$target_dir/task_plan.md"
    local findings_path="$target_dir/findings.md"
    local progress_path="$target_dir/progress.md"

    if [ ! -f "$plan_path" ]; then
        if [ "$TEMPLATE" = "analytics" ] && [ -f "$TEMPLATE_DIR/analytics_task_plan.md" ]; then
            cp "$TEMPLATE_DIR/analytics_task_plan.md" "$plan_path"
        else
            write_default_task_plan "$plan_path"
        fi
        echo "Created $plan_path"
    else
        echo "$plan_path already exists, skipping"
    fi

    if [ ! -f "$findings_path" ]; then
        if [ "$TEMPLATE" = "analytics" ] && [ -f "$TEMPLATE_DIR/analytics_findings.md" ]; then
            cp "$TEMPLATE_DIR/analytics_findings.md" "$findings_path"
        else
            write_default_findings "$findings_path"
        fi
        echo "Created $findings_path"
    else
        echo "$findings_path already exists, skipping"
    fi

    if [ ! -f "$progress_path" ]; then
        if [ "$TEMPLATE" = "analytics" ]; then
            write_analytics_progress "$DATE" "$progress_path"
        else
            write_default_progress "$DATE" "$progress_path"
        fi
        echo "Created $progress_path"
    else
        echo "$progress_path already exists, skipping"
    fi
}

if [ "$SLUG_MODE" -eq 1 ]; then
    SLUG="$(slugify "$PROJECT_NAME")"
    if [ -z "$SLUG" ]; then
        SLUG="untitled-$(short_uuid)"
    fi
    BASE_ID="${DATE}-${SLUG}"
    PLAN_ID="$BASE_ID"
    PLAN_ROOT="${PWD}/.planning"
    counter=2
    while [ -d "${PLAN_ROOT}/${PLAN_ID}" ]; do
        PLAN_ID="${BASE_ID}-${counter}"
        counter=$((counter + 1))
    done
    PLAN_DIR="${PLAN_ROOT}/${PLAN_ID}"
    mkdir -p "$PLAN_DIR"

    echo "Initializing planning files for: ${PROJECT_NAME:-untitled} (template: $TEMPLATE)"
    echo "PLAN_ID=$PLAN_ID"
    create_files_in "$PLAN_DIR"
    printf "%s\n" "$PLAN_ID" > "${PLAN_ROOT}/.active_plan"
    bind_session_plan_if_available "$PLAN_ROOT" "$PLAN_ID"
    echo ""
    echo "Active plan recorded: ${PLAN_ROOT}/.active_plan"
    echo "Pin this terminal to the plan for parallel sessions:"
    echo "  export PLAN_ID=$PLAN_ID"
else
    PROJECT_NAME="${PROJECT_NAME:-project}"
    echo "Initializing planning files for: $PROJECT_NAME (template: $TEMPLATE)"
    create_files_in "$(pwd)"
    echo ""
    echo "Planning files initialized!"
    echo "Files: task_plan.md, findings.md, progress.md"
fi
