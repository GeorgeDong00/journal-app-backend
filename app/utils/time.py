import datetime


def return_previous_sunday(date : datetime.date) -> datetime.date:
    """Returns the datetime of latest previous (last week) Sunday before given
    date. The datetime is set to midnight UTC and is used to retrieve the latest
    week that has already passed.

    Args:
        date: UTC date to calculate the previous Sunday.

    Returns:
        datetime.date: Last week Sunday before the given date.
    """
    previous_sunday_date = date - datetime.timedelta(days=date.weekday() + 1)

    # Combine previous Sunday date with midnight time and UTC timezone.
    return datetime.datetime.combine(
        previous_sunday_date,
        datetime.time.min,
        tzinfo=datetime.timezone.utc
    )
