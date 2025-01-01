from datetime import datetime, timezone, timedelta, date


def latest_monday() -> date:
    """Returns the beginning of the current week - Monday at midnight UTC. The date is used to map
    a weekly advice and its corresponding week.

    Returns:
        monday_of_week (datetime.date): Current week's Monday 00:00 UTC.
    """
    # Get the current date and subtract the number of days to Monday.
    current_date = datetime.now(timezone.utc).date()
    days_to_subtract = current_date.weekday()
    return current_date - timedelta(days_to_subtract)
