from datetime import datetime, timezone, timedelta, date

def latest_monday(date_of=datetime.now(timezone.utc).date()) -> date:
    """Returns the beginning of the week of given date parameter. If parameter is not avaliable,
    then defaults to current date. The date is used to map a weekly advice and its corresponding week.

    Returns:
        monday_of_week (datetime.date): The week's Monday 00:00 UTC.
    """
    # Determine the day of `date_of` and subtract the number of days to Monday.
    days_to_subtract = date_of.weekday()
    return date_of - timedelta(days_to_subtract)
