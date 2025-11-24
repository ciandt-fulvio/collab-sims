#!/bin/bash
# CollabSims Server Manager with tmux
# Manages API and Web servers in separate tmux windows

SESSION_NAME="collab-sims"
API_WINDOW="api"
WEB_WINDOW="web"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}[CollabSims]${NC} $1"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# Check if tmux session exists
session_exists() {
    tmux has-session -t "$SESSION_NAME" 2>/dev/null
    return $?
}

# Check if a specific window exists
window_exists() {
    tmux list-windows -t "$SESSION_NAME" -F "#{window_name}" 2>/dev/null | grep -q "^$1$"
    return $?
}

# Start servers
start_servers() {
    if session_exists; then
        print_warning "Session '$SESSION_NAME' already exists"
        print_status "Use 'restart' to restart servers or 'stop' then 'start'"
        return 1
    fi

    print_status "Starting CollabSims servers..."

    # Create tmux session with API window
    tmux new-session -d -s "$SESSION_NAME" -n "$API_WINDOW"

    # Start API server in first window
    tmux send-keys -t "$SESSION_NAME:$API_WINDOW" "cd $PWD && ./run_api.sh" C-m
    print_success "API server starting in tmux window '$API_WINDOW'"

    # Create web window
    tmux new-window -t "$SESSION_NAME" -n "$WEB_WINDOW"

    # Start web server in second window
    tmux send-keys -t "$SESSION_NAME:$WEB_WINDOW" "cd $PWD && ./run_web.sh" C-m
    print_success "Web server starting in tmux window '$WEB_WINDOW'"

    # Select API window by default
    tmux select-window -t "$SESSION_NAME:$API_WINDOW"

    print_success "Servers started in tmux session '$SESSION_NAME'"
    echo ""
    echo "Access servers at:"
    echo "  • API:     http://localhost:3007"
    echo "  • Web:     http://localhost:3005"
    echo "  • API Docs: http://localhost:3007/docs"
    echo ""
    echo "Management commands:"
    echo "  ./manage_servers.sh logs [api|web]  - View logs"
    echo "  ./manage_servers.sh restart [api|web|all] - Restart servers"
    echo "  ./manage_servers.sh stop            - Stop all servers"
    echo "  ./manage_servers.sh attach          - Attach to tmux session"
}

# Stop servers
stop_servers() {
    if ! session_exists; then
        print_error "No tmux session '$SESSION_NAME' found"
        return 1
    fi

    print_status "Stopping CollabSims servers..."

    # Kill the tmux session (will terminate all processes)
    tmux kill-session -t "$SESSION_NAME"

    print_success "Servers stopped"
}

# Restart a specific server or all
restart_server() {
    local target="${1:-all}"

    if ! session_exists; then
        print_error "No tmux session found. Use 'start' first"
        return 1
    fi

    case $target in
        api)
            print_status "Restarting API server..."
            # Send Ctrl+C to stop current process
            tmux send-keys -t "$SESSION_NAME:$API_WINDOW" C-c
            sleep 2
            # Restart
            tmux send-keys -t "$SESSION_NAME:$API_WINDOW" "./run_api.sh" C-m
            print_success "API server restarted"
            ;;
        web)
            print_status "Restarting Web server..."
            tmux send-keys -t "$SESSION_NAME:$WEB_WINDOW" C-c
            sleep 2
            tmux send-keys -t "$SESSION_NAME:$WEB_WINDOW" "./run_web.sh" C-m
            print_success "Web server restarted"
            ;;
        all)
            print_status "Restarting all servers..."
            restart_server api
            restart_server web
            ;;
        *)
            print_error "Invalid target: $target. Use 'api', 'web', or 'all'"
            return 1
            ;;
    esac
}

# View logs (attach to specific window)
view_logs() {
    local target="${1:-api}"

    if ! session_exists; then
        print_error "No tmux session found. Use 'start' first"
        return 1
    fi

    case $target in
        api)
            print_status "Attaching to API logs (Ctrl+B then D to detach)..."
            sleep 1
            tmux select-window -t "$SESSION_NAME:$API_WINDOW"
            tmux attach-session -t "$SESSION_NAME"
            ;;
        web)
            print_status "Attaching to Web logs (Ctrl+B then D to detach)..."
            sleep 1
            tmux select-window -t "$SESSION_NAME:$WEB_WINDOW"
            tmux attach-session -t "$SESSION_NAME"
            ;;
        *)
            print_error "Invalid target: $target. Use 'api' or 'web'"
            return 1
            ;;
    esac
}

# Attach to tmux session
attach_session() {
    if ! session_exists; then
        print_error "No tmux session found. Use 'start' first"
        return 1
    fi

    print_status "Attaching to tmux session (Ctrl+B then D to detach)..."
    sleep 1
    tmux attach-session -t "$SESSION_NAME"
}

# Show status
show_status() {
    if session_exists; then
        print_success "Session '$SESSION_NAME' is running"
        echo ""
        echo "Windows:"
        tmux list-windows -t "$SESSION_NAME" -F "  • #{window_name} (#{window_panes} pane(s))"
        echo ""
        echo "Access servers at:"
        echo "  • API:     http://localhost:3007"
        echo "  • Web:     http://localhost:3005"
        echo "  • API Docs: http://localhost:3007/docs"
    else
        print_warning "Session '$SESSION_NAME' is not running"
        echo "Use './manage_servers.sh start' to start servers"
    fi
}

# Show usage
show_usage() {
    cat << EOF
CollabSims Server Manager

Usage: ./manage_servers.sh <command> [options]

Commands:
  start                    Start API and Web servers in tmux
  stop                     Stop all servers
  restart [api|web|all]    Restart specific server or all (default: all)
  logs [api|web]           View server logs (default: api)
  attach                   Attach to tmux session
  status                   Show server status
  help                     Show this help message

Examples:
  ./manage_servers.sh start          # Start all servers
  ./manage_servers.sh logs api       # View API logs
  ./manage_servers.sh restart api    # Restart only API server
  ./manage_servers.sh stop           # Stop all servers

Tmux shortcuts (when attached):
  Ctrl+B then D              Detach from session (servers keep running)
  Ctrl+B then [              Scroll mode (Q to exit)
  Ctrl+B then 0/1            Switch between windows (0=api, 1=web)
  Ctrl+B then ,              Rename current window

EOF
}

# Main command dispatcher
case "${1:-help}" in
    start)
        start_servers
        ;;
    stop)
        stop_servers
        ;;
    restart)
        restart_server "${2:-all}"
        ;;
    logs)
        view_logs "${2:-api}"
        ;;
    attach)
        attach_session
        ;;
    status)
        show_status
        ;;
    help|--help|-h)
        show_usage
        ;;
    *)
        print_error "Unknown command: $1"
        echo ""
        show_usage
        exit 1
        ;;
esac
