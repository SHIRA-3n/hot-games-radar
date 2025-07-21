# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Hot Games Radar is a gaming market intelligence platform that analyzes the Japanese gaming market to identify promising opportunities for streamers. The system processes data from multiple sources (Twitch, Steam, Google Trends, Twitter) to score games based on streaming potential and competitive landscape.

## Architecture

### Signal-Based Processing System
The core architecture uses a modular signal processing approach where each signal module (`radar/signals/`) independently analyzes different aspects of games:
- Each signal returns a normalized score (0-1) for games
- Signals run concurrently using `asyncio.gather()` for performance
- Final scores are weighted averages based on `config.yaml` settings
- Individual signal failures don't crash the entire analysis

### Key Components
- **`run.py`** - Entry point that imports and executes `radar.core.main()`
- **`radar/core.py`** - Main orchestration logic, handles Twitch data fetching, signal coordination, and Discord notifications
- **`radar/utils.py`** - Steam API integration and utility functions
- **`radar/signals/`** - Individual signal modules, each focusing on one data source or analysis type

## Development Commands

```bash
# Run the analysis
python3 run.py

# Validate syntax
python3 -m py_compile run.py

# Install dependencies
pip3 install -r requirements.txt
```

## Configuration

### Required Environment Variables
```bash
TWITCH_CLIENT_ID=your_twitch_client_id
TWITCH_CLIENT_SECRET=your_twitch_client_secret
DISCORD_WEBHOOK_URL_3D=webhook_for_3_day_notifications
DISCORD_WEBHOOK_URL_7D=webhook_for_7_day_notifications  
DISCORD_WEBHOOK_URL_30D=webhook_for_30_day_notifications
```

### config.yaml Structure
- **Analysis settings**: `target_count`, `score_threshold`, `notification_intervals`
- **Channel profile**: Your streaming stats for competitive analysis comparison
- **Schedule**: Your streaming schedule for optimal game timing analysis
- **Weights**: Importance weights for each signal type (sum should equal 1.0)

## Signal Modules Reference

Each signal module in `radar/signals/` follows the pattern:
```python
async def calculate_signal(session, app_ids, channel_profile, schedule_info, current_time):
    # Returns dict mapping app_id -> score (0-1)
```

Key signals:
- **competition.py**: Analyzes Japanese streamer competition density
- **google_trends.py**: Google search trends analysis
- **steam_ccu.py**: Steam concurrent user tracking
- **twitch_drops.py**: Detects Twitch Drops campaigns
- **jp_ratio.py**: Japanese audience penetration analysis
- **slot_fit.py**: Streaming schedule optimization scoring
- **market_health.py**: Overall market health assessment

## API Integration Notes

- **Rate Limiting**: The system handles API rate limits through async session management
- **Fuzzy Matching**: Game names are matched between services using `rapidfuzz`
- **Error Handling**: Individual signal failures are caught and logged without stopping analysis
- **Data Chunking**: Discord messages are split into chunks to avoid size limits

## Adding New Signals

1. Create new file in `radar/signals/your_signal.py`
2. Implement `calculate_signal()` async function returning app_id -> score dict
3. Add import and call in `radar/core.py`
4. Add corresponding weight in `config.yaml`

## Performance Considerations

- Analysis runs for up to 1000 games concurrently
- Steam API calls are batched to minimize requests
- Results are cached during single execution to avoid duplicate API calls
- Discord notifications are sent asynchronously to avoid blocking