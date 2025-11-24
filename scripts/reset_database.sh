#!/bin/bash
# Reset database script - deletes existing database and recreates schema

echo "🗑️  Resetting database..."

# Remove existing database
if [ -f "./data/api_sessions.db" ]; then
    rm -f ./data/api_sessions.db
    echo "   Deleted existing database"
fi

# Create data directory if it doesn't exist
mkdir -p ./data

# Create new database with schema
sqlite3 ./data/api_sessions.db < collab_sims/persistence/schema.sql

echo "✅ Database reset complete."
echo "   New database created at: ./data/api_sessions.db"
