#!/bin/bash
# Script to start the Vibe-Draw application

# Colors for pretty output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting Vibe-Draw...${NC}"

# Check if Redis is running
redis_running=$(redis-cli ping 2>/dev/null)
if [ "$redis_running" != "PONG" ]; then
    echo -e "${YELLOW}Redis is not running. Attempting to start Redis...${NC}"
    
    # Try different methods to start Redis based on the system
    if command -v redis-server &> /dev/null; then
        redis-server --daemonize yes
    elif command -v brew &> /dev/null; then
        brew services start redis
    else
        echo -e "${RED}Could not start Redis. Please start it manually.${NC}"
        echo "On macOS: brew services start redis"
        echo "On Ubuntu: sudo service redis-server start"
        echo "On Windows: Start the Redis server from the installation directory"
        exit 1
    fi
    
    sleep 2
    redis_running=$(redis-cli ping 2>/dev/null)
    if [ "$redis_running" != "PONG" ]; then
        echo -e "${RED}Failed to start Redis. Please start it manually and try again.${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}Redis started successfully.${NC}"
fi

# Create a directory for log files if it doesn't exist
mkdir -p logs

# Start the FastAPI server in the background
echo -e "${GREEN}Starting FastAPI server...${NC}"
cd backend
source venv/bin/activate || source venv/Scripts/activate
python run.py > ../logs/api.log 2>&1 &
API_PID=$!
cd ..

# Start the Celery worker in the background
echo -e "${GREEN}Starting Celery worker...${NC}"
cd backend
source venv/bin/activate || source venv/Scripts/activate
celery -A worker worker --loglevel=info > ../logs/celery.log 2>&1 &
CELERY_PID=$!
cd ..

# Start the Next.js frontend
echo -e "${GREEN}Starting Next.js frontend...${NC}"
cd frontend
npm run dev > ../logs/frontend.log 2>&1 &
FRONTEND_PID=$!
cd ..

echo -e "${GREEN}All services started successfully!${NC}"
echo -e "${YELLOW}API Server PID: ${API_PID}${NC}"
echo -e "${YELLOW}Celery Worker PID: ${CELERY_PID}${NC}"
echo -e "${YELLOW}Frontend PID: ${FRONTEND_PID}${NC}"
echo -e "${GREEN}Vibe-Draw is now available at: http://localhost:3000${NC}"
echo -e "${YELLOW}Check the logs directory for detailed logs.${NC}"
echo -e "${RED}Press Ctrl+C to stop all services${NC}"

# Function to kill processes on exit
cleanup() {
    echo -e "${YELLOW}Shutting down Vibe-Draw...${NC}"
    kill $API_PID 2>/dev/null
    kill $CELERY_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    echo -e "${GREEN}All services stopped.${NC}"
    exit 0
}

# Set up the trap for cleanup on script termination
trap cleanup SIGINT SIGTERM

# Keep the script running until manually terminated
while true; do
    sleep 1
done
